from typing import Any

from app.recommendation.engine import calculate_acidity_salinity_recommendation, calculate_fertilization_recommendation, solve_fertilizer_doses
from app.recommendation.schemas import (
    RecommendationRequest,
    RecommendationResponse,
    RecommendationType,
)


def _pick_name(data: dict[str, Any] | None) -> str | None:
    if not data:
        return None

    return (
        data.get("name")
        or data.get("nome")
        or data.get("description")
        or data.get("descricao")
        or data.get("title")
        or data.get("titulo")
    )


def _has_data(data: dict[str, Any] | None) -> bool:
    return bool(data and len(data.keys()) > 0)


def _summarize_entity(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {
            "provided": False,
            "name": None,
            "keys": [],
        }

    return {
        "provided": True,
        "name": _pick_name(data),
        "keys": sorted(list(data.keys())),
    }


def _build_data_used(request: RecommendationRequest) -> dict[str, Any]:
    return {
        "property": _summarize_entity(request.property),
        "plot": _summarize_entity(request.plot),
        "physical_analysis": _summarize_entity(request.physical_analysis),
        "fertility_analysis": _summarize_entity(request.fertility_analysis),
        "saturation_extract_analysis": _summarize_entity(request.saturation_extract_analysis),
        "annual_crop_folder": _summarize_entity(request.annual_crop_folder),
        "crop": _summarize_entity(request.crop),
        "crop_fertilization_table": _summarize_entity(request.crop_fertilization_table),
        "soil_fertility_interpretation_table": _summarize_entity(
            request.soil_fertility_interpretation_table
        ),
        "leaf_analysis_interpretation_table": _summarize_entity(
            request.leaf_analysis_interpretation_table
        ),
        "fertilizer_group": request.fertilizer_group,
        "fertilizer_source": _summarize_entity(request.fertilizer_source),
    }


def _build_technical_alerts(request: RecommendationRequest) -> list[str]:
    alerts: list[str] = []

    if not _has_data(request.property):
        alerts.append("Propriedade não foi informada ou veio vazia.")

    if not _has_data(request.plot):
        alerts.append("Talhão não foi informado ou veio vazio.")

    if not _has_data(request.fertility_analysis):
        alerts.append("Análise de fertilidade do solo não foi informada ou veio vazia.")

    if request.recommendation_type == RecommendationType.ACIDITY_SALINITY:
        if not _has_data(request.saturation_extract_analysis):
            alerts.append(
                "Análise de extrato de saturação não foi informada; a correção de salinidade ficará pendente."
            )

    if request.recommendation_type == RecommendationType.FERTILIZATION:
        if not _has_data(request.crop):
            alerts.append("Cultura não foi informada; a recomendação de adubação ficará incompleta.")

        if not _has_data(request.crop_fertilization_table):
            alerts.append(
                "Tabela de adubação de culturas não foi informada; não é possível definir doses NPK finais."
            )

        if not _has_data(request.soil_fertility_interpretation_table):
            alerts.append(
                "Tabela de interpretação da fertilidade do solo não foi informada; a classificação dos nutrientes ficará pendente."
            )

    return alerts


def _build_interpretation(request: RecommendationRequest) -> dict[str, Any]:
    fertility_provided = _has_data(request.fertility_analysis)
    physical_provided = _has_data(request.physical_analysis)
    saturation_provided = _has_data(request.saturation_extract_analysis)

    return {
        "summary": "Interpretação agronômica preliminar gerada a partir das entidades recebidas do FertIntelligence.",
        "property_name": _pick_name(request.property),
        "plot_name": _pick_name(request.plot),
        "crop_name": _pick_name(request.crop),
        "analysis_status": {
            "physical_analysis_available": physical_provided,
            "fertility_analysis_available": fertility_provided,
            "saturation_extract_analysis_available": saturation_provided,
        },
        "planning_note": (
            "Esta etapa ainda não executa os cálculos finais. Ela estrutura o relatório "
            "para receber, nas próximas etapas, interpretação química, calagem, gessagem, "
            "correção de salinidade, recomendação NPK e conversão para fertilizantes comerciais."
        ),
    }


def _build_diagnosis(request: RecommendationRequest) -> list[str]:
    diagnosis = [
        "Dados recebidos e organizados para geração de recomendação agronômica estruturada.",
        "O relatório foi separado em interpretação, diagnóstico, correção, adubação, sugestões de fertilizantes e alertas técnicos.",
    ]

    if request.recommendation_type == RecommendationType.ACIDITY_SALINITY:
        diagnosis.append(
            "Fluxo selecionado: correção de acidez e salinidade. A próxima engine deverá avaliar pH, Al, H+Al, V%, Ca, Mg, Na e parâmetros do extrato de saturação."
        )

    if request.recommendation_type == RecommendationType.FERTILIZATION:
        diagnosis.append(
            "Fluxo selecionado: adubação. A próxima engine deverá interpretar os teores de nutrientes, cruzar a cultura com a tabela de adubação e gerar doses de N, P2O5 e K2O."
        )

    return diagnosis


def _build_correction_recommendation(request: RecommendationRequest) -> dict[str, Any]:
    if request.recommendation_type != RecommendationType.ACIDITY_SALINITY:
        return {
            "enabled": False,
            "status": "NOT_REQUESTED",
            "liming": {"status": "NOT_REQUESTED"},
            "gypsum": {"status": "NOT_REQUESTED"},
            "salinity_correction": {"status": "NOT_REQUESTED"},
        }

    return calculate_acidity_salinity_recommendation(
        fertility_analysis=request.fertility_analysis,
        saturation_extract_analysis=request.saturation_extract_analysis,
    )


def _build_fertilization_recommendation(request: RecommendationRequest) -> dict[str, Any]:
    if request.recommendation_type != RecommendationType.FERTILIZATION:
        return {
            "enabled": False,
            "status": "NOT_REQUESTED",
            "nutrient_recommendation": {"status": "NOT_REQUESTED"},
            "table_crossing": {
                "crop_table_available": _has_data(request.crop_fertilization_table),
                "soil_interpretation_table_available": _has_data(
                    request.soil_fertility_interpretation_table
                ),
                "leaf_interpretation_table_available": _has_data(
                    request.leaf_analysis_interpretation_table
                ),
            },
        }

    return calculate_fertilization_recommendation(
        fertility_analysis=request.fertility_analysis,
        crop=request.crop,
        crop_fertilization_table=request.crop_fertilization_table,
        soil_fertility_interpretation_table=request.soil_fertility_interpretation_table,
    )


def _build_fertilizer_suggestions(request: RecommendationRequest) -> list[dict[str, Any]]:
    if request.recommendation_type != RecommendationType.FERTILIZATION:
        return []

    fertilization = _build_fertilization_recommendation(request)
    nutrient_recommendation = fertilization.get("nutrient_recommendation", {})

    suggestions = solve_fertilizer_doses(
        nutrient_recommendation=nutrient_recommendation,
        fertilizer_source=request.fertilizer_source,
    )

    if suggestions:
        return suggestions

    return [
        {
            "status": "INSUFFICIENT_DATA",
            "fertilizer_group": request.fertilizer_group,
            "message": "Não foi possível sugerir fertilizantes porque não vieram doses NPK calculadas ou lista de fertilizantes comerciais.",
        }
    ]


def generate_recommendation(request: RecommendationRequest) -> RecommendationResponse:
    return RecommendationResponse(
        recommendation_type=request.recommendation_type,
        fertilizer_group=request.fertilizer_group,
        status="AGRONOMIC_RECOMMENDATION_PLANNED",
        data_used=_build_data_used(request),
        interpretation=_build_interpretation(request),
        diagnosis=_build_diagnosis(request),
        correction_recommendation=_build_correction_recommendation(request),
        fertilization_recommendation=_build_fertilization_recommendation(request),
        fertilizer_suggestions=_build_fertilizer_suggestions(request),
        technical_alerts=_build_technical_alerts(request),
        next_steps=[
            "Implementar engine de calagem, gessagem e correção de salinidade.",
            "Implementar engine de interpretação da fertilidade e recomendação NPK.",
            "Implementar solver de fertilizantes comerciais por grupo selecionado.",
            "Integrar o backend Spring Boot para enviar entidades reais consolidadas ao Fert-AI.",
        ],
    )
