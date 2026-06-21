from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as ai_router


app = FastAPI(
    title="FertIntelligence Fert AI",
    description="Microserviço RAG agronômico com DeepSeek para o FertIntelligence.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_router)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "fertintelligence-fert-ai",
        "docs": "/docs",
        "health": "/api/ai/health",
        "chat": "/api/ai/chat",
    }
