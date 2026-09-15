"""
RAG (Retrieval-Augmented Generation) system for Sakura Stack.
Uses LangChain for orchestration: Chroma vector store + Ollama LLM.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document

import logging

# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ---- Config from .env ----
LLM_MODEL = os.getenv("LLM_MODEL", "mistral")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "jlpt_chunks")
TOP_K = int(os.getenv("RAG_TOP_K", 5))


# ---- Build the RAG chain once ----
def build_rag_chain():
    """Build and return a LangChain RAG chain."""
    logger.info(f"Building RAG chain (LLM={LLM_MODEL}, embed={EMBED_MODEL})")

    # Embeddings + vector store
    embeddings = OllamaEmbeddings(
        model=EMBED_MODEL,
        base_url=OLLAMA_BASE_URL
    )

    vector_store = Chroma(
        collection_name=CHROMA_COLLECTION,
        embedding_function=embeddings,
        host=CHROMA_HOST,
        port=CHROMA_PORT
    )

    retriever = vector_store.as_retriever(
        search_kwargs={"k": TOP_K}
    )

    # LLM
    llm = ChatOllama(
        model=LLM_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.1
    )

    # Prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a helpful JLPT N2 study assistant. Answer the student's "
         "question using ONLY the context provided below.\n\n"
         "Guidelines:\n"
         "- Answer clearly in English, with Japanese terms where relevant\n"
         "- If example sentences are in the context, use them\n"
         "- If the context doesn't contain the answer, say: "
         "\"I don't have that information in my study materials\"\n"
         "- Cite context numbers like [1], [2] when you use them\n"
         "- Be concise but thorough\n\n"
         "Context:\n{context}"),
        ("human", "{question}")
    ])

    # Format retrieved docs into a single context string with [n] labels
    def format_docs(docs):
        return "\n\n".join(
            f"[{i}] ({d.metadata.get('section_type', 'general')} from "
            f"{d.metadata.get('source_file', 'unknown')})\n{d.page_content}"
            for i, d in enumerate(docs, 1)
        )

    # LCEL chain
    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain, retriever


# Cache chain so we don't rebuild on every query
_chain_cache = None


def get_chain():
    global _chain_cache
    if _chain_cache is None:
        _chain_cache = build_rag_chain()
    return _chain_cache


# ---- Public API ----
def query_rag(question: str, top_k: int = TOP_K) -> dict:
    """
    Query the RAG system.

    Returns:
        dict with keys: answer, sources, context
    """
    logger.info(f"Query: {question}")

    chain, retriever = get_chain()

    # Retrieve sources separately so we can return metadata
    docs: list[Document] = retriever.invoke(question)
    metadatas = [d.metadata for d in docs]
    context = "\n\n".join(
        f"[{i}] {d.page_content}" for i, d in enumerate(docs, 1)
    )

    if not docs:
        return {
            "answer": "I couldn't find any relevant information in the study materials.",
            "sources": [],
            "context": ""
        }

    # Generate answer
    logger.info(f"Generating answer with {LLM_MODEL}...")
    answer = chain.invoke(question)

    return {
        "answer": answer,
        "sources": metadatas,
        "context": context
    }


# ---- CLI ----
def interactive_mode():
    print("\n" + "=" * 60)
    print("Sakura Stack — JLPT Study Assistant (LangChain)")
    print("=" * 60)
    print("Ask questions about JLPT N2 vocabulary and grammar.")
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
                    print(f"  [{i}] {src.get('section_type', '?')} — "
                          f"{src.get('source_file', '?')}")
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
            print(f"  [{i}] {src.get('section_type', '?')} — "
                  f"{src.get('source_file', '?')}")
    else:
        interactive_mode()