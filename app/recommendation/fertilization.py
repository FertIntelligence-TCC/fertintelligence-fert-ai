from typing import Any

from app.recommendation.common import num as _num


def classify_soil_fertility_level(value: float | None, ranges: list[dict[str, Any]] | None) -> dict[str, Any]:
    if value is None:
        return {
            "status": "INSUFFICIENT_DATA",
            "value": None,
            "classification": None,
            "matched_range": None,
        }

    if not ranges:
        return {
            "status": "NO_TABLE_RANGES",
            "value": value,
            "classification": None,
            "matched_range": None,
        }

    for item in ranges:
        min_value = item.get("min") or item.get("minimum") or item.get("valor_minimo")
        max_value = item.get("max") or item.get("maximum") or item.get("valor_maximo")
        label = item.get("label") or item.get("classification") or item.get("classe") or item.get("interpretation")

        try:
            min_float = float(str(min_value).replace(",", ".")) if min_value is not None else None
            max_float = float(str(max_value).replace(",", ".")) if max_value is not None else None
        except ValueError:
            continue

        min_ok = min_float is None or value >= min_float
        max_ok = max_float is None or value <= max_float

        if min_ok and max_ok:
            return {
                "status": "CLASSIFIED",
                "value": value,
                "classification": label,
                "matched_range": item,
            }

    return {
        "status": "OUT_OF_RANGE",
        "value": value,
        "classification": None,
        "matched_range": None,
    }


def _find_ranges(table: dict[str, Any] | None, nutrient: str) -> list[dict[str, Any]]:
    if not table:
        return []

    candidates = [
        nutrient,
        nutrient.lower(),
        nutrient.upper(),
        f"{nutrient}_ranges",
        f"{nutrient.lower()}_ranges",
        f"ranges_{nutrient.lower()}",
    ]

    for key in candidates:
        value = table.get(key)
        if isinstance(value, list):
            return value

    for key in ("ranges", "content_ranges", "faixas", "intervalos"):
        value = table.get(key)
        if not isinstance(value, list):
            continue

        matched = []
        for item in value:
            item_nutrient = str(
                item.get("nutrient")
                or item.get("nutriente")
                or item.get("element")
                or item.get("elemento")
                or ""
            ).lower()

            if item_nutrient in {nutrient.lower(), nutrient.lower().replace("2o5", ""), nutrient.lower().replace("k2o", "k")}:
                matched.append(item)

        if matched:
            return matched

    return []


def _find_recommendation_rows(table: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not table:
        return []

    for key in (
        "recommendations",
        "recomendacoes",
        "fertilization_recommendations",
        "adubacao",
        "doses",
        "coverages",
        "coberturas",
    ):
        value = table.get(key)
        if isinstance(value, list):
            return value

    return []


def _match_dose_by_classification(
    rows: list[dict[str, Any]],
    nutrient: str,
    classification: str | None,
) -> float | None:
    if not rows or not classification:
        return None

    nutrient_lower = nutrient.lower()
    classification_lower = classification.lower()

    for row in rows:
        row_nutrient = str(row.get("nutrient") or row.get("nutriente") or "").lower()
        row_class = str(
            row.get("classification")
            or row.get("classe")
            or row.get("soil_class")
            or row.get("classe_solo")
            or ""
        ).lower()

        if row_nutrient and row_nutrient not in {nutrient_lower, nutrient_lower.replace("2o5", ""), nutrient_lower.replace("k2o", "k")}:
            continue

        if row_class and row_class != classification_lower:
            continue

        dose = (
            row.get("dose")
            or row.get("dose_kg_ha")
            or row.get("kg_ha")
            or row.get("recommended_dose")
            or row.get("dose_recomendada")
        )

        if dose is None:
            continue

        try:
            return float(str(dose).replace(",", "."))
        except ValueError:
            continue

    return None


def calculate_fertilization_recommendation(
    fertility_analysis: dict[str, Any] | None,
    crop: dict[str, Any] | None,
    crop_fertilization_table: dict[str, Any] | None,
    soil_fertility_interpretation_table: dict[str, Any] | None,
) -> dict[str, Any]:
    p = _num(fertility_analysis, "p", "fosforo", "phosphorus")
    k = _num(fertility_analysis, "k", "potassio", "potassium")
    organic_matter = _num(fertility_analysis, "mo", "materia_organica", "organic_matter")
    clay = _num(fertility_analysis, "argila", "clay")

    p_ranges = _find_ranges(soil_fertility_interpretation_table, "p")
    k_ranges = _find_ranges(soil_fertility_interpretation_table, "k")
    mo_ranges = _find_ranges(soil_fertility_interpretation_table, "mo")

    p_classification = classify_soil_fertility_level(p, p_ranges)
    k_classification = classify_soil_fertility_level(k, k_ranges)
    mo_classification = classify_soil_fertility_level(organic_matter, mo_ranges)

    rows = _find_recommendation_rows(crop_fertilization_table)

    n_dose = _match_dose_by_classification(rows, "n", mo_classification.get("classification"))
    p2o5_dose = _match_dose_by_classification(rows, "p2o5", p_classification.get("classification"))
    k2o_dose = _match_dose_by_classification(rows, "k2o", k_classification.get("classification"))

    fallback_used = False

    if n_dose is None and crop:
        n_dose = _num(crop_fertilization_table, "n", "nitrogenio", "nitrogen")
        fallback_used = fallback_used or n_dose is not None

    if p2o5_dose is None:
        p2o5_dose = _num(crop_fertilization_table, "p2o5", "fosforo", "phosphorus")
        fallback_used = fallback_used or p2o5_dose is not None

    if k2o_dose is None:
        k2o_dose = _num(crop_fertilization_table, "k2o", "potassio", "potassium")
        fallback_used = fallback_used or k2o_dose is not None

    return {
        "enabled": True,
        "status": "CALCULATED_INITIAL_VERSION",
        "crop": {
            "name": (crop or {}).get("name") or (crop or {}).get("nome"),
            "provided": bool(crop),
        },
        "soil_interpretation": {
            "phosphorus": p_classification,
            "potassium": k_classification,
            "organic_matter": mo_classification,
            "clay_percent": clay,
        },
        "nutrient_recommendation": {
            "status": "CALCULATED_PARTIAL" if any(v is not None for v in [n_dose, p2o5_dose, k2o_dose]) else "INSUFFICIENT_DATA",
            "n_kg_ha": n_dose,
            "p2o5_kg_ha": p2o5_dose,
            "k2o_kg_ha": k2o_dose,
            "source": "crop_fertilization_table",
            "fallback_direct_table_fields_used": fallback_used,
        },
        "application_plan": {
            "status": "PENDING_DETAILED_RULES",
            "base_fertilization": "Aplicar P2O5 e parte do K2O na adubação de base conforme cultura e tabela técnica.",
            "topdressing": "Parcelar N e K2O em cobertura conforme exigência da cultura, textura do solo e manejo.",
        },
        "table_crossing": {
            "crop_table_available": bool(crop_fertilization_table),
            "soil_interpretation_table_available": bool(soil_fertility_interpretation_table),
            "recommendation_rows_found": len(rows),
        },
    }


