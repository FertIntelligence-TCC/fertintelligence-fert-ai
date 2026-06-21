import json
from pathlib import Path

import faiss
import numpy as np
from openai import OpenAI

from app.core.config import (
    VECTORSTORE_DIR,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    TOP_K,
)
from app.rag.ingest import embed_text


SYSTEM_PROMPT = """
Você é um assistente técnico agronômico do FertIntelligence.

Responda em português do Brasil, com clareza e rigor técnico.

Use prioritariamente o CONTEXTO recuperado dos documentos.
Se o contexto não for suficiente, diga isso explicitamente.
Não invente recomendações numéricas específicas quando os documentos não sustentarem.
Quando fizer sentido, cite as fontes no fim usando nome do PDF e página.
"""


class FertRagAgent:
    def __init__(self):
        index_path = VECTORSTORE_DIR / "index.faiss"
        documents_path = VECTORSTORE_DIR / "documents.json"

        if not index_path.exists() or not documents_path.exists():
            raise RuntimeError(
                "Índice RAG não encontrado. Rode antes: python -m app.rag.ingest"
            )

        self.index = faiss.read_index(str(index_path))

        with open(documents_path, "r", encoding="utf-8") as f:
            self.documents = json.load(f)

        self.client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )

    def retrieve(self, question: str, top_k: int = TOP_K) -> list[dict]:
        query_vector = embed_text(question).reshape(1, -1).astype("float32")
        scores, ids = self.index.search(query_vector, top_k)

        results = []

        for score, doc_id in zip(scores[0], ids[0]):
            if doc_id < 0:
                continue

            doc = self.documents[int(doc_id)].copy()
            doc["score"] = float(score)
            results.append(doc)

        return results

    def build_context(self, docs: list[dict]) -> str:
        parts = []

        for i, doc in enumerate(docs, start=1):
            parts.append(
                f"[Fonte {i}] {doc['source']} | página {doc['page']} | score {doc['score']:.4f}\n"
                f"{doc['text']}"
            )

        return "\n\n".join(parts)

    def answer(self, question: str) -> dict:
        docs = self.retrieve(question)
        context = self.build_context(docs)

        user_prompt = f"""
PERGUNTA:
{question}

CONTEXTO RECUPERADO:
{context}

TAREFA:
Responda à pergunta usando o contexto acima.
Inclua uma seção final chamada "Fontes consultadas" com os PDFs e páginas usados.
"""

        response = self.client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT.strip()},
                {"role": "user", "content": user_prompt.strip()},
            ],
            temperature=0.2,
        )

        answer_text = response.choices[0].message.content

        return {
            "question": question,
            "answer": answer_text,
            "sources": [
                {
                    "source": doc["source"],
                    "page": doc["page"],
                    "score": doc["score"],
                    "preview": doc["text"][:300],
                }
                for doc in docs
            ],
        }


_agent = None


def get_agent() -> FertRagAgent:
    global _agent

    if _agent is None:
        _agent = FertRagAgent()

    return _agent
