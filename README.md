<<<<<<< HEAD
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

## Documentation

| Document | Path |
| --- | --- |
| PRD v2.0 | `../govai/prd.pdf` |
| TRD v2.0 | [`docs/TRD-GOVFLOW-001.md`](docs/TRD-GOVFLOW-001.md) |
| 90-Day Roadmap | [`ROADMAP.md`](ROADMAP.md) |

## Test

```powershell
.\venv\Scripts\pytest tests\ -v
.\venv\Scripts\python -m tests.test_eval --api-url http://localhost:8000
```

### 🧪 Testing Strategy

**Framework:** `pytest`
**Mocking:** `unittest.mock` for API dependency injection.
**CI/CD:** Automated testing pipeline on every push.

## Project Structure

```text
app/
├── main.py              # FastAPI entrypoint
├── api/v1/process.py    # POST /api/v1/process, GET /api/v1/process/{trace_id}
├── api/v1/history.py    # GET /api/v1/history
├── db/models.py         # SQLModel: documents, decisions, audit_logs
├── schemas/process.py   # Pydantic v2 request/response
├── services/            # pipeline, llm
├── security/presidio.py # PII sanitization
├── resilience/          # pybreaker, tenacity
└── tasks/               # Celery workers
alembic/                 # DB migrations (Phase 4)
tests/
├── test_process.py
├── test_phase4_db.py
└── test_eval.py         # Golden Test Set evaluator
eval/
└── golden_test_set.jsonl
```
=======
#CivicOs
>AI-powered workflow automation engine for government and public sector document triage, classification, and routing.

**Overview** 
>CiviOs is a production-grade ai pipeline designed to transform unstructured citizens submissions - such as complaints, >reports, and forms - into structured , actionable data. By utilizing Fastapi, Pydantic validation, and llm powered >reasoning, CiviOs enables government agencies to reduce manual triage overhead and ensure consistent , auditable decision -> making

**Core features**
- **INTELLIGENT TRIANGLE :** Automates categorization (complaint, request, report) and priority scoring (low to critical).
- **STRUCTURED OUTPUT   :** Uses instructor  and pydantic to ensure the llm returns valid , non-hallucinated JSON.
- **AUDIT-READY         :** Every decision is logged with confidence scores , reasoning traces, and processing metrices.
- **PERFORMANCE FOCUSED :** Built for sub-3s latency with a cost -efficient architecture.

**ARCHITECTURE** 
1. **INGESTION   :** Raw text input via REST API
2. **AI-ENGINE    :** LLM-based analysis with strict schema enforcemnt .
3. **PERSISTENCE :** PostgreSQL audit logging for all decisions.
4. **MONITORING  :** Streamlit dashboard for real-time triage oversight.

**tech stack**
- **BACKEND        :** Python 3.11,FastAPI,Pydantic
- **AI             :** OpenAPI, instructor
- **DATABASE       :** PostgreSQL
- **INFRASTRUCTURE :** Docker, Render/Railway


>>>>>>> 4bf825acc599aae423884cfc4ea3a134144365db
