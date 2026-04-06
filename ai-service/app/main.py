from fastapi import FastAPI
from app.routes.query import router

app = FastAPI(
    title="AI Service — RAG Pipeline",
    description="Retrieval-Augmented Generation with LangChain + FAISS + OpenAI",
    version="1.0.0"
)

app.include_router(router, prefix="/api/v1", tags=["RAG"])

@app.get("/health")
async def health():
    return {"status": "ok", "service": "ai-service"}
