## GovFlow AI

[![CI](https://github.com/sitara2007/CivicOs/actions/workflows/ci.yml/badge.svg)](https://github.com/sitara2007/CivicOs/actions/workflows/ci.yml)

Production-grade government document classification and routing engine.

## Quick Start

```powershell
cd civicos
.\venv\Scripts\pip install -e ".[dev]"
copy .env.example .env
docker compose up -d postgres   # optional: persistence
.\venv\Scripts\alembic upgrade head
.\venv\Scripts\uvicorn app.main:app --reload --port 8000
```

Set `DATABASE_ENABLED=true` in `.env` to persist documents, decisions, and audit logs.

## Architecture

- **API Gateway** — request ID and trace ID injection, request validation, error handling.
- **Pipeline Engine** — central orchestration for security, retrieval, LLM routing, evaluation, and audit.
- **Security / PII Guard** — redact sensitive content before model calls.
- **Retrieval** — Qdrant-based RAG context lookup with chunk reranking.
- **Observability** — OpenTelemetry tracing, structured logging, latency and token metrics.
- **Evaluation** — answer groundedness and hallucination scoring.
- **Audit Log** — persisted trace records for each request and response.

## Request lifecycle

1. Client submits `POST /api/v1/process`
2. Gateway assigns `trace_id` and starts tracing span
3. Pipeline sanitizes PII with the security guard
4. Retriever fetches Qdrant context and reranks chunks
5. LLM router selects the provider and generates an answer
6. Evaluation scores are computed and attached to the response
7. Audit record is persisted with latency, tokens, and scores
8. Response is returned with `trace_id`

## Testing

```powershell
.\venv\Scripts\pytest tests\ -v
.\venv\Scripts\python -m tests.test_eval --api-url http://localhost:8000
```

### 🧪 Testing Strategy

- **Framework:** `pytest`
- **Mocking:** `unittest.mock` for API dependency injection
- **CI/CD:** automated tests on every push

## Project structure

```text
app/
├── main.py
├── api/v1/
│   ├── process.py
│   ├── history.py
│   └── endpoints/
├── core/
│   ├── config.py
│   ├── logging.py
│   ├── metrics.py
│   └── tracing.py
├── gateway/
│   └── middleware.py
├── pipeline/
│   ├── context.py
│   └── engine.py
├── services/
│   ├── audit/
│   │   └── logger.py
│   ├── evaluation/
│   │   ├── evaluator.py
│   │   ├── groundedness.py
│   │   └── hallucination.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── fallback.py
│   │   ├── model_router.py
│   │   └── router.py
│   ├── rag/
│   │   ├── retriever.py
│   │   └── reranker.py
│   ├── security/
│   │   └── pii_guard.py
│   └── audit/
│       └── logger.py
├── db/
│   ├── models.py
│   ├── repositories/
│   └── session.py
├── schemas/
└── tests/
```

## Documentation

| Document | Path |
| --- | --- |
| PRD v2.0 | `../govai/prd.pdf` |
| TRD v2.0 | [`docs/TRD-GOVFLOW-001.md`](docs/TRD-GOVFLOW-001.md) |
| 90-Day Roadmap | [`ROADMAP.md`](ROADMAP.md) |

## Tech stack

- **Backend:** Python 3.11, FastAPI, Pydantic
- **AI:** OpenAI / mock classifier
- **Database:** PostgreSQL
- **Observability:** OpenTelemetry, structured JSON logging
- **Infrastructure:** Docker, Docker Compose

## **Architecture Diagram**
```mermaid
graph TD
    %% Subgraphs with deployment specs
    subgraph API_Gateway["API_Gateway (K8s Service: NodePort)"]
        API[FastAPI Gateway]
        OtelAPI[("fa:fa-bullseye Otel:API TraceID/Metrics")]
        OtelAPI --> API
    end

    subgraph Core_Pipeline["Core_Pipeline (K8s Deployment: Microservices Cluster)"]
        Pipe[Pipeline Service]
        RAG[Qdrant RAG Context]
        LLM[Decision Engine]
        OtelRAG[("fa:fa-bullseye Otel:RAG TraceID/Metrics")]
        OtelLLM[("fa:fa-bullseye Otel:LLM TraceID/Metrics")]
        OtelRAG --> RAG
        OtelLLM --> LLM
        Pipe --> RAG --> LLM
    end

    subgraph Persistence_Layer["Persistence_Layer (Cloud Storage: PostgreSQL + Distributed FS)"]
        DB[(PostgreSQL)]
        Audit[Hash-Chain Auditor]
        OtelDB[("fa:fa-bullseye Otel:DB TraceID/Metrics")]
        OtelAudit[("fa:fa-bullseye Otel:Audit TraceID/Metrics")]
        OtelDB --> DB
        OtelAudit --> Audit
    end

    subgraph Async_Worker["Async_Worker (K8s CronJob/Worker Node Pool)"]
        Celery[Celery/Background Task]
        DLQ[Dead Letter Queue]
        OtelCelery[("fa:fa-bullseye Otel:Worker TraceID/Metrics")]
        OtelDLQ[("fa:fa-bullseye Otel:DLQ TraceID/Metrics")]
        OtelCelery --> Celery
        OtelDLQ --> DLQ
    end

    %% Core connections
    API --> Pipe
    LLM --> Audit
    Audit --> DB
    DB --> Celery
    Celery -- Failed msg --> DLQ
