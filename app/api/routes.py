from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.rag.agent import get_agent


router = APIRouter(prefix="/api/ai", tags=["Agronomic AI"])


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3)


class ChatResponse(BaseModel):
    question: str
    answer: str
    sources: list[dict]


@router.get("/health")
def health():
    return {"status": "ok", "service": "fertintelligence-fert-ai"}


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    agent = get_agent()
    return agent.answer(request.question)
