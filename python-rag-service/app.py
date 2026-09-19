from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="python-rag-service")


class RAGRequest(BaseModel):
    tenant_id: str
    query: str
    limit: int = 5


class RAGResult(BaseModel):
    tenant_id: str
    query: str
    results: list[str]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/search", response_model=RAGResult)
async def search(req: RAGRequest) -> RAGResult:
    return RAGResult(
        tenant_id=req.tenant_id,
        query=req.query,
        results=[f"tenant={req.tenant_id} :: match-{i}" for i in range(req.limit)],
    )
