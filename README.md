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


