import logging

from openai import OpenAI

from app.core import config
from app.rag.retriever import retrieve_sources


logger = logging.getLogger(__name__)


client = OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
)


FORBIDDEN_OUTPUT_MARKERS = [
    "[",
    "]",
    "[valor",
    "[fórmula",
    "[formula",
    "[alerta",
    "[nome",
    "[nome do responsável",
    "[responsavel",
    "[responsável",
    "crea",
    "prnt",
    "parcelamento",
    "cronograma",
    "profundidade",
    "incorporação",
    "incorporacao",
    "forma de aplicação",
    "forma de aplicacao",
    "responsável técnico",
    "responsavel tecnico",
]


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


def _contains_forbidden_hallucination_marker(improved_report: str, technical_report: str) -> bool:
    improved_lower = improved_report.lower()
    original_lower = technical_report.lower()

    for marker in FORBIDDEN_OUTPUT_MARKERS:
        marker_lower = marker.lower()

        if marker_lower in improved_lower and marker_lower not in original_lower:
            return True

    return False


def _safe_improved_report(improved_report: str, technical_report: str) -> str:
    cleaned = improved_report.strip()

    if not cleaned:
        return technical_report

    if _contains_forbidden_hallucination_marker(cleaned, technical_report):
        return technical_report

    return cleaned


def improve_recommendation_narrative(technical_report: str) -> dict:
    try:
        sources = retrieve_sources(technical_report, top_k=5)
    except FileNotFoundError:
        logger.warning("RAG index not found; continuing without sources")
        sources = []

    context = _build_context(sources)

    prompt = f"""
Você é o FertIntelligence AI.

Você receberá um laudo técnico já calculado pelo sistema FertIntelligence.

Sua função é EXCLUSIVAMENTE revisar a redação do texto recebido.

Você NÃO é calculadora agronômica nesta tarefa.
Você NÃO deve complementar o laudo.
Você NÃO deve enriquecer tecnicamente o laudo.
Você NÃO deve criar recomendações.
Você NÃO deve usar conhecimento externo para adicionar conteúdo.

TAREFA PERMITIDA:
- Corrigir gramática.
- Melhorar clareza.
- Melhorar organização textual.
- Melhorar fluidez.
- Padronizar linguagem técnica.
- Reorganizar frases mantendo exatamente o mesmo sentido.

REGRAS OBRIGATÓRIAS:
- NÃO crie informações novas.
- NÃO utilize placeholders.
- NÃO use colchetes para campos pendentes.
- NÃO escreva marcadores como [Valor], [Fórmula], [Alerta], [Nome do Responsável] ou similares.
- NÃO altere doses.
- NÃO altere cálculos.
- NÃO altere unidades.
- NÃO altere diagnósticos.
- NÃO altere critérios.
- NÃO invente dados de análise.
- NÃO invente recomendações.
- NÃO invente alertas técnicos.
- NÃO invente seções.
- NÃO invente subtítulos que indiquem dados ausentes.
- NÃO transforme afirmações genéricas em afirmações específicas.
- NÃO explique causas agronômicas que não estejam explicitamente no laudo original.
- NÃO acrescente manejo operacional.
- NÃO acrescente instruções de execução.
- NÃO acrescente observações preventivas.
- NÃO acrescente responsáveis, assinaturas, nomes, cargos ou CREA.

PROIBIÇÕES ESPECÍFICAS:
Caso NÃO existam literalmente no LAUDO ORIGINAL, não mencione:
- PRNT.
- Parcelamento.
- Cronograma.
- Profundidade.
- Profundidade de incorporação.
- Forma de aplicação.
- Responsável técnico.
- CREA.
- Gessagem.
- Manejo.
- Reanálise.
- Monitoramento.

REGRA DE AUSÊNCIA:
Se um dado não existir no LAUDO ORIGINAL, mantenha a ausência.
Não diga que está ausente.
Não crie campo para preencher depois.
Não use placeholders.

FONTES DE APOIO:
As fontes abaixo podem ser usadas apenas como contexto linguístico geral.
É proibido usar as fontes para adicionar qualquer informação técnica, prática, operacional ou agronômica ao laudo.

{context}

SAÍDA:
Responda somente com o laudo revisado.
Não explique o que foi feito.
Não inclua comentários.
Não inclua markdown fora do próprio laudo.
Não inclua placeholders.

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
                        "Você é um revisor técnico conservador. "
                        "Sua única tarefa é melhorar a redação sem adicionar, remover ou inferir conteúdo. "
                        "Se houver risco de inferência, preserve o texto original."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0,
        )
    except Exception:
        logger.warning("DeepSeek narrative generation failed; returning original technical report")
        return _empty_response(technical_report)

    improved_report = response.choices[0].message.content or technical_report
    improved_report = _safe_improved_report(improved_report, technical_report)

    return {
        "improved_report": improved_report,
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
