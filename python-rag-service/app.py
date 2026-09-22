import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from retrieval import HybridRetriever

app = FastAPI(title="python-rag-service")


class RAGRequest(BaseModel):
    tenant_id: str
    query: str
    limit: int = Field(default=5, ge=1, le=20)


class ContextResult(BaseModel):
    text: str
    score: float
    source: str


class RAGResult(BaseModel):
    tenant_id: str
    query: str
    results: list[ContextResult]
    answer: str | None = None


retriever = HybridRetriever()


async def generate_answer(query: str, contexts: list[ContextResult]) -> str:
    if not contexts:
        return "No relevant context was found for this query."

    provider = os.getenv("LLM_PROVIDER", "mock").lower()
    if provider == "mock":
        best = contexts[0].text
        snippet = best.strip().replace("\n", " ")
        return f"Based on the retrieved context, the likely answer is: {snippet[:500]}"

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500, detail="OPENAI_API_KEY is not configured"
            )

        from openai import AsyncOpenAI

        prompt = "\n\n".join(
            f"Context {i + 1}: {ctx.text}" for i, ctx in enumerate(contexts[:5])
        )
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
            messages=[
                {"role": "system", "content": "Answer only from the supplied context."},
                {"role": "user", "content": f"Query: {query}\n\n{prompt}"},
            ],
        )
        return response.choices[0].message.content or "No answer was generated."

    return "LLM provider is not configured for answer generation."


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/search", response_model=RAGResult)
async def search(req: RAGRequest) -> RAGResult:
    try:
        contexts = retriever.search(
            req.query, req.tenant_id, candidate_limit=50, top_k=req.limit
        )
    except Exception:
        contexts = []

    normalized = [
        ContextResult(
            text=item["text"],
            score=float(item.get("score", 0.0)),
            source=item.get("source", "hybrid"),
        )
        for item in contexts
    ]

    answer = await generate_answer(req.query, normalized)
    return RAGResult(
        tenant_id=req.tenant_id,
        query=req.query,
        results=normalized,
        answer=answer,
    )
