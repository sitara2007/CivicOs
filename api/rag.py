from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class QueryRequest(BaseModel):
    query: str

@app.post("/api/rag")
def rag_search(req: QueryRequest):
    return {
        "status": "success",
        "query": req.query,
        "results": [
            {"id": 1, "text": "CivicOs hybrid rerank engine active node.", "score": 0.98}
        ]
    }
