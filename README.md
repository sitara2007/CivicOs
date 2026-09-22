#  CivicOs

[![CI](https://github.8252/sitara2007/CivicOs/actions/workflows/ci.yml/badge.svg)](https://github.8252/sitara2007/CivicOs/actions/workflows/ci.yml)
[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen)](https://civic-os-two.vercel.app)

Production-grade AI-powered workflow automation engine for government and public sector document triage, classification, and routing. Built for high-throughput, security, and tamper-proof compliance.

## 🚀 Live Demo & Endpoints

- **Public Frontend Dashboard:** [civic-os-two.vercel.app](https://civic-os-two.vercel.app)
- **API Documentation & Specs:** Integrated via FastAPI backend engine.

---

## 📊 Core Architecture Highlights

- **PII Guard** — Automatically redacts sensitive citizen data BEFORE any LLM model calls are made.
- **Hash-Chain Audit** — Tamper-proof compliance logs ensuring absolute government accountability.
- **Hallucination Scoring** — Every output is verified for groundedness and reliability.
- **High-Throughput Ingestion** — 12K events/sec powered by Go, Python FastAPI, Qdrant, and ClickHouse pipelines.

---

Set `DATABASE_ENABLED=true` in `.env` to persist documents, decisions, and audit logs.

🏗️ System Architecture
API Gateway — Request ID and trace ID injection, request validation, and robust error handling.

Pipeline Engine — Central orchestration for security, retrieval, LLM routing, evaluation, and audit logs.

Security / PII Guard — Real-time sanitization of sensitive data.

Retrieval (RAG) — Qdrant-based context lookup with advanced chunk reranking.

Observability — OpenTelemetry tracing, structured JSON logging, and latency/token metrics.

Evaluation — Answer groundedness and hallucination scoring modules.

🔄 Request Lifecycle
Client submits POST /api/v1/process

Gateway assigns a unique trace_id and initiates tracing spans.

Pipeline sanitizes PII utilizing the security guard.

Retriever fetches Qdrant context and reranks relevant chunks.

LLM router selects the optimal model provider and generates responses.

Evaluation metrics and hallucination scores are computed.

Audit record with latency, token consumption, and audit trail is persisted.

Response is returned containing the corresponding trace_id.

🛠️ Tech Stack
Backend / Engine: Python 3.11, FastAPI, Pydantic, Go microservices

High-Throughput Ingestion: Go + ClickHouse

Vector Search & Storage: Qdrant, PostgreSQL, Alembic

Observability: OpenTelemetry, structured JSON logging

Infrastructure & Deployment: Docker, Docker Compose, Vercel (https://civic-os-two.vercel.app)
## Project structure

graph TD
    subgraph API_Gateway["API Gateway (K8s Service)"]
        API[FastAPI Gateway]
        OtelAPI[("Otel: TraceID & Metrics")]
        OtelAPI --> API
    end

    subgraph Core_Pipeline["Core Pipeline (Microservices Cluster)"]
        Pipe[Pipeline Engine]
        RAG[Qdrant RAG Context]
        LLM[Decision & Router Engine]
        Pipe --> RAG --> LLM
    end

    subgraph Persistence_Layer["Persistence Layer (PostgreSQL + ClickHouse)"]
        DB[(PostgreSQL)]
        Audit[Hash-Chain Auditor]
        LLM --> Audit --> DB
    end

    API --> Pipe
