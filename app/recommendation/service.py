from app.recommendation.schemas import (
    RecommendationRequest,
    RecommendationResponse,
    RecommendationType,
)


def generate_recommendation_stub(request: RecommendationRequest) -> RecommendationResponse:
    warnings = []

    if request.recommendation_type == RecommendationType.ACIDITY_SALINITY:
        if not request.fertility_analysis:
            warnings.append("Análise de fertilidade não foi informada.")
        if not request.saturation_extract_analysis:
            warnings.append("Análise de extrato de saturação não foi informada.")
    else:
        if not request.crop:
            warnings.append("Cultura não foi informada.")
        if not request.crop_fertilization_table:
            warnings.append("Tabela de adubação de culturas não foi informada.")
        if not request.soil_fertility_interpretation_table:
            warnings.append("Tabela de interpretação da fertilidade do solo não foi informada.")

    return RecommendationResponse(
        recommendation_type=request.recommendation_type,
        fertilizer_group=request.fertilizer_group,
        status="CONTRACT_VALIDATED",
        interpretation={
            "message": "Contrato recebido e validado pelo FertIntelligence AI.",
            "property_name": request.property.get("name") or request.property.get("nome"),
            "plot_name": request.plot.get("name") or request.plot.get("nome"),
            "crop_name": (request.crop or {}).get("name") or (request.crop or {}).get("nome"),
        },
        diagnosis=[
            "Endpoint estrutural criado para receber dados consolidados do backend Spring.",
            "A recomendação agronômica real será implementada na próxima etapa.",
        ],
        correction_recommendation=None,
        fertilization_recommendation=None,
        fertilizer_suggestions=[],
        warnings=warnings,
        next_steps=[
            "Implementar interpretação da análise de fertilidade.",
            "Implementar cálculo de calagem, gessagem e correção de salinidade.",
            "Implementar recomendação NPK por cultura.",
            "Implementar solver de doses de adubos conforme grupo selecionado.",
        ],
    )
