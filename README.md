# GovFlow AI

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

- **API Layer** — FastAPI request routing, trace ID injection, CORS, and global error handling.
- **Pipeline Service** — orchestrates normalization, PII sanitization, optional RAG retrieval, LLM classification, and decision persistence.
- **Security / PII Guard** — Microsoft Presidio-based sanitization with a regex fallback when Presidio is unavailable.
- **Retrieval** — Qdrant RAG lookup for optional policy/context enrichment.
- **Observability** — OpenTelemetry tracing and metrics with structured JSON logging.
- **Evaluation** — offline groundedness and hallucination scoring components for model quality review.
- **Persistence / Audit** — PostgreSQL-backed document, decision, redaction, and DLQ metadata storage.

## Request lifecycle

1. Client submits `POST /api/v1/process`
2. FastAPI middleware binds a trace ID and adds it to response headers
3. Pipeline normalizes text and sanitizes PII
4. Optional RAG retrieval gathers policy context from Qdrant
5. LLM service or mock classifier generates a document decision
6. Completed decisions are saved to PostgreSQL, or failures are routed to DLQ
7. Response returns status and `trace_id`; async requests may return `202 Accepted`
8. `GET /api/v1/process/{trace_id}` polls persisted status and decision

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
├── api/
│   ├── router.py
│   └── v1/
│       ├── process.py
│       ├── history.py
│       └── endpoints/
├── core/
│   ├── config.py
│   └── logging.py
├── db/
│   ├── models.py
│   ├── repositories/
│   └── session.py
├── security/
│   └── presidio.py
├── services/
│   ├── ai_infra.py
│   ├── mock_classifier.py
│   ├── observability.py
│   ├── pipeline.py
│   ├── process_service.py
│   ├── rag/
│   ├── llm/
│   ├── audit/
│   ├── evaluation/
│   ├── cache/
│   ├── embeddings/
│   ├── pii/
│   └── vector_db.py
├── tasks/
│   └── process_document.py
├── utils/
├── worker/
│   └── celery_app.py
└── __init__.py
```

## Documentation

| Document | Path |
| --- | --- |
| PRD v2.0 | `../govai/prd.pdf` |
| TRD v2.0 | [`docs/TRD-GOVFLOW-001.md`](docs/TRD-GOVFLOW-001.md) |
| 90-Day Roadmap | [`ROADMAP.md`](ROADMAP.md) |

## Tech stack

- **Backend:** Python 3.12, FastAPI, Pydantic
- **AI:** OpenAI / mock classifier
- **Database:** PostgreSQL
- **Observability:** OpenTelemetry, structured JSON logging
- **Infrastructure:** Docker, Docker Compose
