import os
from openai import OpenAI

from app.rag.retriever import retrieve_sources

try:
    from app.core import config
except Exception:
    config = None


def _get_config_value(name: str, default: str | None = None) -> str | None:
    if config is not None:
        settings = getattr(config, "settings", None)

        if settings is not None and hasattr(settings, name):
            return getattr(settings, name)

        if hasattr(config, name):
            return getattr(config, name)

    return os.getenv(name, default)


DEEPSEEK_API_KEY = _get_config_value("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = _get_config_value("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = _get_config_value("DEEPSEEK_MODEL", "deepseek-chat")

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)


def _build_context(sources: list[dict]) -> str:
    blocks = []

    for i, source in enumerate(sources, start=1):
        blocks.append(
            f"""[FONTE {i}]
Arquivo: {source.get("source")}
Página: {source.get("page")}

{source.get("preview")}
"""
        )

    return "\n".join(blocks)


def ask_agent(question: str) -> dict:
    sources = retrieve_sources(question, top_k=5)
    context = _build_context(sources)

    prompt = f"""
Você é o FertIntelligence AI, um assistente técnico especializado em fertilidade do solo, calagem, gessagem, adubação e interpretação de análise de solo.

Responda à pergunta usando SOMENTE as fontes fornecidas abaixo.

Regras obrigatórias:
- Não invente informações.
- Não cite documentos que não estejam nas fontes.
- Ao fazer uma afirmação técnica relevante, cite a fonte no formato [1], [2], [3].
- Se as fontes não forem suficienteses, diga claramente que os documentos recuperados não são suficientes para responder com segurança.
- Responda em português brasileiro.

FONTES:
{context}

PERGUNTA:
{question}
"""

    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {
                "role": "system",
                "content": "Você é um assistente agronômico técnico e rigoroso com as fontes.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.2,
    )

    answer = response.choices[0].message.content

    citations = [
        {
            "id": i,
            "source": source.get("source"),
            "page": source.get("page"),
            "score": source.get("score"),
        }
        for i, source in enumerate(sources, start=1)
    ]

    return {
        "answer": answer,
        "citations": citations,
    }


def get_agent(question: str) -> dict:
    return ask_agent(question)
