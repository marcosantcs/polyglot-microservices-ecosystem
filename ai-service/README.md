# AI Service — RAG Pipeline

Microservice for Retrieval-Augmented Generation using LangChain + FAISS + OpenAI.

## Stack
- **FastAPI** — async REST API
- **LangChain** — LLM orchestration
- **FAISS** — local vector store (no external DB required)
- **OpenAI** — `gpt-4o-mini` + `text-embedding-3-small`

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/query` | Query the RAG pipeline |

## Example Request

```bash
curl -X POST http://localhost:8001/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What technologies are used in the platform?"}'
```

## Running Locally

```bash
cp .env.example .env   # add your OPENAI_API_KEY
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

## Running with Docker

```bash
docker build -t ai-service .
docker run -p 8001:8001 --env-file .env ai-service
```
