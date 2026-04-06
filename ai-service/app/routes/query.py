from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.rag import get_rag_response

router = APIRouter()

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: list[str]

@router.post("/query", response_model=QueryResponse)
async def query_rag(payload: QueryRequest):
    try:
        result = await get_rag_response(payload.query)
        return QueryResponse(
            query=payload.query,
            answer=result["answer"],
            sources=result["sources"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
