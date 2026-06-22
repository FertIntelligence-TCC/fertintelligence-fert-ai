import logging

from openai import OpenAI

from app.core import config
from app.rag.retriever import retrieve_sources


logger = logging.getLogger(__name__)


client = OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
)


def _build_context(sources: list[dict]) -> str:
    blocks: list[str] = []

    for i, source in enumerate(sources, start=1):
        blocks.append(
            f"""[FONTE {i}]
Arquivo: {source.get("source")}
Página: {source.get("page")}

{source.get("preview")}
"""
        )

    return "\n".join(blocks)


def _empty_response(technical_report: str) -> dict:
    return {
        "improved_report": technical_report,
        "sources_used": 0,
        "citations": [],
    }


def improve_recommendation_narrative(technical_report: str) -> dict:
    try:
        sources = retrieve_sources(technical_report, top_k=5)
    except FileNotFoundError:
        logger.warning("RAG index not found; continuing without sources")
        sources = []

    context = _build_context(sources)

    prompt = f"""
Você é o FertIntelligence AI, um assistente agronômico especialista em fertilidade do solo, calagem, gessagem, salinidade, adubação e geração de laudos técnicos.

Você receberá um laudo técnico já calculado pelo sistema FertIntelligence.

Sua tarefa é apenas revisar e organizar a redação técnica do laudo, preservando integralmente o conteúdo factual original.

REGRAS OBRIGATÓRIAS:
- Não altere doses.
- Não altere cálculos.
- Não altere unidades.
- Não invente recomendações.
- Não invente diagnósticos.
- Não invente dados de análise.
- Não transforme afirmações genéricas em afirmações específicas.
- Não explique causas agronômicas que não estejam explicitamente no laudo original.
- Não invente prazos de aplicação.
- Não invente profundidade de incorporação.
- Não invente forma de aplicação.
- Não invente parcelamento de adubação.
- Não invente necessidade de reanálise.
- Não acrescente manejo operacional que não esteja no laudo original.
- Nos alertas técnicos, apenas reescreva os alertas existentes sem adicionar novas condições, exemplos ou procedimentos.
- Não remova alertas técnicos.
- Não contradiga o laudo original.
- Use as fontes apenas para melhorar a linguagem e a fundamentação geral, sem criar novas recomendações práticas.
- Não use as fontes para acrescentar etapas de execução, prazos, formas de aplicação, monitoramento ou cuidados não presentes no laudo original.
- Se alguma informação estiver ausente no laudo original, diga que ela não foi informada somente quando isso for necessário para evitar inferência indevida.
- Responda somente com o laudo final melhorado.
- O texto final deve conter apenas informações já presentes no laudo original, com melhoria de clareza, organização e linguagem.
- Escreva em português brasileiro técnico, claro e objetivo.

FONTES DE APOIO:
{context}

LAUDO ORIGINAL:
{technical_report}
"""

    try:
        response = client.chat.completions.create(
            model=config.DEEPSEEK_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um engenheiro agrônomo rigoroso. "
                        "Você melhora a redação de laudos sem modificar cálculos, doses ou recomendações."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.15,
        )
    except Exception:
        logger.warning("DeepSeek narrative generation failed; returning original technical report")
        return _empty_response(technical_report)

    improved_report = response.choices[0].message.content or technical_report

    return {
        "improved_report": improved_report.strip(),
        "sources_used": len(sources),
        "citations": [
            {
                "id": i,
                "source": source.get("source"),
                "page": source.get("page"),
                "score": source.get("score"),
            }
            for i, source in enumerate(sources, start=1)
        ],
    }
