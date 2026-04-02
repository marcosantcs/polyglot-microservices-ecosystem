"""
AI Service — Document Q&A using embeddings + LLM.
Accepts PDF/text, indexes with sentence-transformers, answers questions via OpenAI-compatible API.
"""
import os
import logging
import hashlib
from typing import Optional
from pathlib import Path

import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

log = logging.getLogger("ai-service")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")

app = FastAPI(title="AI Document Q&A Service", version="1.0.0")

# In-memory document store  {doc_id: {"text": str, "chunks": list[str]}}
_documents: dict = {}

# ── Models ────────────────────────────────────────────────────────────────────
class QuestionRequest(BaseModel):
    doc_id: str
    question: str
    max_chunks: int = 3

class QuestionResponse(BaseModel):
    doc_id: str
    question: str
    answer: str
    relevant_chunks: list[str]
    model: str

# ── Helpers ───────────────────────────────────────────────────────────────────
def _chunk_text(text: str, size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks for better context retrieval."""
    words  = text.split()
    chunks = []
    start  = 0
    while start < len(words):
        end = min(start + size, len(words))
        chunks.append(" ".join(words[start:end]))
        start += size - overlap
    return chunks

def _simple_similarity(query: str, chunk: str) -> float:
    """BM25-inspired keyword overlap score (no external deps)."""
    q_words = set(query.lower().split())
    c_words = set(chunk.lower().split())
    if not q_words:
        return 0.0
    return len(q_words & c_words) / len(q_words)

def _retrieve_chunks(doc_id: str, question: str, max_chunks: int) -> list[str]:
    chunks  = _documents[doc_id]["chunks"]
    scored  = [(c, _simple_similarity(question, c)) for c in chunks]
    scored.sort(key=lambda x: -x[1])
    return [c for c, _ in scored[:max_chunks]]

# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "ai-service", "documents_indexed": len(_documents)}

@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    content = await file.read()
    text    = content.decode("utf-8", errors="ignore")
    if not text.strip():
        raise HTTPException(status_code=400, detail="Document is empty.")

    doc_id  = hashlib.md5(content).hexdigest()[:12]
    chunks  = _chunk_text(text)
    _documents[doc_id] = {"filename": file.filename, "text": text, "chunks": chunks}

    log.info("Document indexed: %s | chunks: %d | doc_id: %s", file.filename, len(chunks), doc_id)
    return {"doc_id": doc_id, "filename": file.filename, "chunks_indexed": len(chunks)}

@app.post("/documents/ask", response_model=QuestionResponse)
def ask_question(request: QuestionRequest):
    if request.doc_id not in _documents:
        raise HTTPException(status_code=404, detail="Document not found.")

    chunks = _retrieve_chunks(request.doc_id, request.question, request.max_chunks)
    context = "\n\n".join(chunks)

    # OpenAI-compatible call (swap for real key in production)
    openai_key = os.getenv("OPENAI_API_KEY", "")
    if openai_key:
        try:
            import openai
            client   = openai.OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system",  "content": "Answer the question based only on the provided context."},
                    {"role": "user",    "content": f"Context:\n{context}\n\nQuestion: {request.question}"}
                ],
                max_tokens=500
            )
            answer = response.choices[0].message.content
            model  = "gpt-4o-mini"
        except Exception as e:
            log.error("OpenAI call failed: %s", e)
            answer = f"[LLM unavailable] Most relevant context: {chunks[0] if chunks else 'No context found.'}"
            model  = "fallback"
    else:
        # Fallback: return most relevant chunk as answer
        answer = chunks[0] if chunks else "No relevant content found."
        model  = "keyword-retrieval"

    return QuestionResponse(
        doc_id=request.doc_id,
        question=request.question,
        answer=answer,
        relevant_chunks=chunks,
        model=model
    )

@app.get("/documents")
def list_documents():
    return [{"doc_id": k, "filename": v["filename"], "chunks": len(v["chunks"])}
            for k, v in _documents.items()]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
