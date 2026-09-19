"""
RAG (Retrieval-Augmented Generation) system for Sakura Stack.
Uses LangChain for orchestration: Chroma vector store + Ollama LLM.
Includes hybrid retrieval: keyword pre-filter + vector search.
"""

import os
import re
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document

import logging
import psycopg2

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ---- Config ----
LLM_MODEL = os.getenv("LLM_MODEL", "mistral")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "jlpt_chunks")
TOP_K = int(os.getenv("RAG_TOP_K", 5))


# ---- Keyword pre-filter (from Postgres) ----
def keyword_lookup(question: str, limit: int = 5) -> list[Document]:
    """
    Extract Japanese tokens from question and look them up directly
    in PostgreSQL. Returns matching docs ranked before vector results.
    """
    # Extract Japanese words from the question (katakana, hiragana, kanji)
    jp_tokens = re.findall(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+", question)
    if not jp_tokens:
        return []

    docs: list[Document] = []
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", 5434)),
            dbname=os.getenv("DB_NAME", "sakura_stack"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
        )
        cur = conn.cursor()

        for token in jp_tokens:
            # Vocabulary exact/near match
            cur.execute("""
                SELECT japanese_word, reading, meaning, example_sentence
                FROM vocabulary
                WHERE japanese_word = %s OR japanese_word ILIKE %s
                LIMIT %s
            """, (token, f"%{token}%", limit))
            for word, reading, meaning, example in cur.fetchall():
                content = f"{word} ({reading}) — {meaning}"
                if example:
                    content += f"\nExample: {example}"
                docs.append(Document(
                    page_content=content,
                    metadata={
                        "section_type": "vocabulary",
                        "source_file": "keyword_lookup",
                        "match_type": "keyword",
                    }
                ))

            # Grammar match
            cur.execute("""
                SELECT pattern, explanation, example_sentence
                FROM grammar_rules
                WHERE pattern ILIKE %s OR pattern = %s
                LIMIT %s
            """, (f"%{token}%", token, limit))
            for pattern, explanation, example in cur.fetchall():
                content = f"{pattern}: {explanation}"
                if example:
                    content += f"\nExample: {example}"
                docs.append(Document(
                    page_content=content,
                    metadata={
                        "section_type": "grammar",
                        "source_file": "keyword_lookup",
                        "match_type": "keyword",
                    }
                ))

        cur.close()
        conn.close()
    except Exception as e:
        logger.warning(f"Keyword lookup failed (non-fatal): {e}")

    logger.info(f"Keyword lookup found {len(docs)} direct match(es)")
    return docs


# ---- RAG chain ----
def build_rag_chain():
    logger.info(f"Building RAG chain (LLM={LLM_MODEL}, embed={EMBED_MODEL})")

    embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
    vector_store = Chroma(
        collection_name=CHROMA_COLLECTION,
        embedding_function=embeddings,
        host=CHROMA_HOST,
        port=CHROMA_PORT,
    )
    retriever = vector_store.as_retriever(search_kwargs={"k": TOP_K})

    llm = ChatOllama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.1)

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a helpful JLPT N2 study assistant. Answer the student's "
         "question using ONLY the context provided below.\n\n"
         "Rules (follow strictly):\n"
         "1. Only use information present in the context.\n"
         "2. Do NOT invent readings, meanings, or examples.\n"
         "3. If the context lacks the answer, respond exactly: "
         "\"I don't have that information in my study materials.\"\n"
         "4. Cite context numbers like [1], [2].\n"
         "5. Be concise.\n\n"
         "Context:\n{context}"),
        ("human", "{question}")
    ])

    def format_docs(docs):
        return "\n\n".join(
            f"[{i}] ({d.metadata.get('section_type', 'general')})\n{d.page_content}"
            for i, d in enumerate(docs, 1)
        )

    chain = (
        {"context": RunnablePassthrough() | (lambda _: ""), "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain, retriever, vector_store


_chain_cache = None


def get_chain():
    global _chain_cache
    if _chain_cache is None:
        _chain_cache = build_rag_chain()
    return _chain_cache


# ---- Public API ----
def query_rag(question: str, top_k: int = TOP_K) -> dict:
    logger.info(f"Query: {question}")

    chain, retriever, vector_store = get_chain()

    # 1. Keyword pre-filter
    keyword_docs = keyword_lookup(question)

    # 2. Vector search
    try:
        vector_docs = retriever.invoke(question)
    except Exception as e:
        logger.warning(f"Vector retrieval failed: {e}")
        vector_docs = []

    # 3. Merge, dedupe by content
    seen = set()
    merged: list[Document] = []
    for d in keyword_docs + vector_docs:
        key = d.page_content[:100]
        if key in seen:
            continue
        seen.add(key)
        merged.append(d)

    merged = merged[:top_k + 3]  # allow a few extra when keyword matches exist

    if not merged:
        return {
            "answer": "I don't have that information in my study materials.",
            "sources": [],
            "context": "",
        }

    context = "\n\n".join(
        f"[{i}] ({d.metadata.get('section_type', 'general')})\n{d.page_content}"
        for i, d in enumerate(merged, 1)
    )
    metadatas = [d.metadata for d in merged]

    # 4. Build prompt + generate
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_ollama import ChatOllama

    llm = ChatOllama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.1)
    prompt_text = (
        "You are a helpful JLPT N2 study assistant. Answer the student's "
        "question using ONLY the context below.\n\n"
        "Rules (follow strictly):\n"
        "1. Only use information present in the context.\n"
        "2. Do NOT invent readings, meanings, or examples.\n"
        "3. If the context lacks the answer, respond exactly: "
        "\"I don't have that information in my study materials.\"\n"
        "4. Cite context numbers like [1], [2].\n"
        "5. Be concise.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\nAnswer:"
    )
    logger.info(f"Generating with {LLM_MODEL} ({len(merged)} context chunks)...")
    response = llm.invoke(prompt_text)
    answer = response.content if hasattr(response, "content") else str(response)

    return {"answer": answer, "sources": metadatas, "context": context}


# ---- CLI ----
def interactive_mode():
    print("\n" + "=" * 60)
    print("Sakura Stack — JLPT Study Assistant (LangChain + hybrid retrieval)")
    print("=" * 60)
    print("Type 'quit' or 'exit' to stop.\n")

    while True:
        try:
            question = input("You: ").strip()
            if not question:
                continue
            if question.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break
            result = query_rag(question)
            print(f"\n📚 Assistant:\n{result['answer']}\n")
            if result["sources"]:
                print("Sources:")
                for i, src in enumerate(result["sources"], 1):
                    print(f"  [{i}] {src.get('section_type', '?')} — {src.get('source_file', '?')}")
            print()
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        result = query_rag(question)
        print(f"\n📚 Answer:\n{result['answer']}\n")
        print("Sources:")
        for i, src in enumerate(result["sources"], 1):
            print(f"  [{i}] {src.get('section_type', '?')} — {src.get('source_file', '?')}")
    else:
        interactive_mode()