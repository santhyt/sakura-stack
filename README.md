# 🌸 Sakura Stack

> An AI-powered Japanese language learning platform built to demonstrate 
> end-to-end Data Engineering, Platform Engineering, and Applied AI Engineering.

**Live demo:** [coming soon — deploying Week 10]  
**Status:** 🚧 In active development  
**JLPT target:** N3 (July 2025) → N2 → N1

---

## What it does

Sakura Stack ingests JLPT study materials (PDFs), processes them through 
an automated data pipeline, and serves an AI tutor that answers Japanese 
language questions grounded in those materials — not hallucinated.

Ask it: *"Explain the difference between は and が"* and it retrieves the 
relevant passage from your actual study materials before answering.

---

## Architecture

<details>
<summary>Click to expand architecture diagrams</summary>

### Overview
![Architecture Overview](docs/architecture-overview.png)

### Infrastructure Layer
![Infrastructure Architecture](docs/architecture-infrastructure.png)

### Data Flow
![Data Flow Diagram](docs/architecture-dataflow.png)

### AI Layer
![AI Layer Architecture](docs/architecture-ai-layer.png)

### Technology Decisions
![Technology Decisions](docs/architecture-tech-decisions.png)

</details>

**Stack decision:** AWS for infrastructure and data layers (Terraform, 
EC2, S3, RDS). Azure OpenAI for the AI layer — deliberately chosen to 
activate Azure AI Engineer certification in a real project context and 
reflect real enterprise multi-cloud environments.

---

## Tech Stack

| Layer | Purpose | Technologies |
|-------|---------|-------------|
| Platform | Infrastructure as Code + CI/CD | Terraform, Docker, GitHub Actions, AWS |
| Data | Pipeline, storage, transformation | Apache Airflow, PyMuPDF, PostgreSQL, dbt |
| AI | RAG + LLM | LangChain, ChromaDB, Azure OpenAI (GPT-4o-mini) |
| App | User interface | Streamlit, Render.com |

---

## Project Structure
```
sakura-stack/
├── infra/        # Terraform — AWS infrastructure
├── data/         # Airflow DAGs + dbt models + ETL scripts  
├── ai/           # RAG pipeline + prompt templates
├── app/          # Streamlit application
└── docs/         # Architecture diagrams + decisions
```

---

## Why I built this

I'm preparing for JLPT N3 (July 2025) and wanted a study tool that 
actually uses *my* materials, not generic flashcard apps. Building it 
as a full-stack engineering project meant I could simultaneously 
demonstrate data pipeline design, infrastructure automation, and applied 
AI in one coherent system.

The pipeline is designed to scale — passing N3 means adding N2 PDFs 
to the same pipeline with zero code changes.

---

## Running locally

*(instructions coming — Week 2)*

---

## What I learned

*(updated as project progresses)*

---

## Roadmap

### Phase 1 — Platform Foundation (Weeks 1–2)
- [x] Project scaffolding, README and architecture diagrams
- [x] Requirements.txt and project dependencies
- [x] Local environment setup (Docker, Python, AWS CLI)
- [x] PDF extraction script (PyMuPDF)
- [x] AWS account + IAM user configured
- [x] Docker Compose: local PostgreSQL + ChromaDB running
- [ ] Terraform: S3 bucket, EC2, RDS PostgreSQL, VPC provisioned
- [ ] GitHub Actions: CI/CD pipeline with linting and Terraform validate

### Phase 2 — Data Engineering (Weeks 3–5)
- [ ] PDF extraction script (PyMuPDF) — chunks with metadata
- [ ] PostgreSQL schema: raw\_chunks, vocabulary, grammar\_rules, passages
- [ ] Airflow DAG: S3 trigger → extract → clean → load to Postgres
- [ ] dbt models: staging → marts (vocabulary, grammar, passages)

### Phase 3 — AI Layer (Weeks 6–8)
- [ ] Azure account created + Azure OpenAI access request submitted
- [ ] ChromaDB: vector embeddings from processed chunks
- [ ] RAG chain: LangChain + Azure OpenAI (GPT-4o-mini)
- [ ] Prompt templates: vocabulary, grammar, reading comprehension

### Phase 4 — UI and Deployment (Weeks 9–10)
- [ ] Streamlit UI: chat interface, vocabulary cards, pipeline status tab
- [ ] Live deployment to Render.com — public URL for portfolio
- [ ] Loom walkthrough video recorded and embedded
