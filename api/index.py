from fastapi import FastAPI

app = FastAPI()

@app.get("/")
@app.head("/")
def read_root():
    return {"status": "online", "service": "CivicOs Gateway"}
