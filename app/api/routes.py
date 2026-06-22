from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.rag.retriever import retrieve_sources
from app.rag.agent import ask_agent
from app.recommendation.schemas import RecommendationRequest, RecommendationResponse
from app.recommendation.service import generate_recommendation


router = APIRouter(prefix="/api/ai", tags=["Agronomic AI"])


class RetrieveRequest(BaseModel):
    question: str
    top_k: int = 5


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3)


@router.get("/health")
def health():
    return {"status": "ok", "service": "fertintelligence-fert-ai"}


@router.post("/chat")
def chat(request: ChatRequest):
    return ask_agent(request.question)


@router.post("/retrieve")
def retrieve(request: RetrieveRequest):
    return {
        "question": request.question,
        "sources": retrieve_sources(request.question, request.top_k),
    }


@router.post("/recommendation", response_model=RecommendationResponse)
def recommendation(request: RecommendationRequest):
    return generate_recommendation(request)

