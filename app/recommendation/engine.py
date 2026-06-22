from typing import Any


def _num(data: dict[str, Any] | None, *keys: str) -> float | None:
    if not data:
        return None

    lowered = {str(k).lower(): v for k, v in data.items()}

    for key in keys:
        value = lowered.get(key.lower())
        if value is None or value == "":
            continue
        try:
            return float(str(value).replace(",", "."))
        except ValueError:
            continue

    return None


def calculate_acidity_salinity_recommendation(
    fertility_analysis: dict[str, Any] | None,
    saturation_extract_analysis: dict[str, Any] | None,
) -> dict[str, Any]:
    ph = _num(fertility_analysis, "ph", "pH", "ph_h2o", "phAgua")
    ca = _num(fertility_analysis, "ca", "calcio", "calcium")
    mg = _num(fertility_analysis, "mg", "magnesio", "magnesium")
    k = _num(fertility_analysis, "k", "potassio", "potassium")
    al = _num(fertility_analysis, "al", "aluminio", "aluminum")
    h_al = _num(fertility_analysis, "h_al", "h+al", "hal", "acidez_potencial")
    t_ctc = _num(fertility_analysis, "t", "ctc", "ctc_ph_7", "ctcPh7")
    prnt = _num(fertility_analysis, "prnt") or 80.0
    target_v = _num(fertility_analysis, "target_v", "v_desejado", "saturacao_bases_desejada") or 60.0

    k_cmol = None
    if k is not None:
        # Quando K vier em mg/dm³, aproxima para cmolc/dm³.
        # Se já vier pequeno, assume que já está em cmolc/dm³.
        k_cmol = k / 391.0 if k > 2 else k

    sb = None
    if ca is not None or mg is not None or k_cmol is not None:
        sb = (ca or 0) + (mg or 0) + (k_cmol or 0)

    if t_ctc is None and sb is not None and h_al is not None:
        t_ctc = sb + h_al

    current_v = None
    if sb is not None and t_ctc and t_ctc > 0:
        current_v = (sb / t_ctc) * 100

    liming_need_t_ha = None
    limestone_dose_t_ha = None

    if current_v is not None and t_ctc is not None and target_v > current_v:
        liming_need_t_ha = t_ctc * (target_v - current_v) / 100
        limestone_dose_t_ha = liming_need_t_ha * (100 / prnt)

    aluminum_saturation = None
    if al is not None and sb is not None:
        effective_ctc = sb + al
        if effective_ctc > 0:
            aluminum_saturation = (al / effective_ctc) * 100

    gypsum_needed = False
    gypsum_reasons: list[str] = []

    if al is not None and al > 0.5:
        gypsum_needed = True
        gypsum_reasons.append("Alumínio trocável elevado.")

    if aluminum_saturation is not None and aluminum_saturation > 20:
        gypsum_needed = True
        gypsum_reasons.append("Saturação por alumínio acima do limite inicial de atenção.")

    if ca is not None and ca < 0.5:
        gypsum_needed = True
        gypsum_reasons.append("Cálcio baixo no solo.")

    ec = _num(
        saturation_extract_analysis,
        "ce",
        "ec",
        "condutividade_eletrica",
        "electrical_conductivity",
    )
    pst = _num(saturation_extract_analysis, "pst", "esp", "percentual_sodio_trocavel")
    sar = _num(saturation_extract_analysis, "sar", "ras", "razao_adsorcao_sodio")

    salinity_class = "NOT_EVALUATED"
    salinity_alerts: list[str] = []

    if ec is not None:
        if ec < 2:
            salinity_class = "NON_SALINE"
        elif ec < 4:
            salinity_class = "SLIGHTLY_SALINE"
            salinity_alerts.append("Condutividade elétrica em faixa de atenção.")
        else:
            salinity_class = "SALINE"
            salinity_alerts.append("Condutividade elétrica elevada; avaliar lixiviação e drenagem.")

    if pst is not None and pst >= 15:
        salinity_alerts.append("PST elevado; risco de sodicidade.")
    if sar is not None and sar >= 13:
        salinity_alerts.append("RAS/SAR elevado; risco de sodicidade.")

    return {
        "enabled": True,
        "status": "CALCULATED_INITIAL_VERSION",
        "liming": {
            "status": "CALCULATED" if limestone_dose_t_ha is not None else "INSUFFICIENT_DATA",
            "ph": ph,
            "sum_of_bases_cmolc_dm3": sb,
            "ctc_ph_7_cmolc_dm3": t_ctc,
            "current_base_saturation_percent": current_v,
            "target_base_saturation_percent": target_v,
            "prnt_percent": prnt,
            "liming_need_t_ha": liming_need_t_ha,
            "limestone_dose_t_ha": limestone_dose_t_ha,
            "method": "Saturação por bases: NC = T x (V2 - V1) / 100; dose corrigida por PRNT.",
        },
        "gypsum": {
            "status": "INITIAL_SCREENING",
            "needed": gypsum_needed,
            "reasons": gypsum_reasons,
            "aluminum_saturation_percent": aluminum_saturation,
            "note": "Triagem inicial. A dose final de gesso será refinada na próxima etapa com dados de subsuperfície e textura.",
        },
        "salinity_correction": {
            "status": "INITIAL_SCREENING" if saturation_extract_analysis else "NOT_EVALUATED",
            "electrical_conductivity_ds_m": ec,
            "pst_percent": pst,
            "sar": sar,
            "classification": salinity_class,
            "alerts": salinity_alerts,
        },
    }


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


def _extract_fertilizers(source: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not source:
        return []

    for key in ("fertilizers", "adubos", "fertilizantes", "items", "data"):
        value = source.get(key)
        if isinstance(value, list):
            return value

    return []


def _fertilizer_nutrients(fertilizer: dict[str, Any]) -> dict[str, float]:
    return {
        "n": _num(fertilizer, "n", "nitrogenio", "nitrogen") or 0.0,
        "p2o5": _num(fertilizer, "p2o5", "fosforo", "phosphorus") or 0.0,
        "k2o": _num(fertilizer, "k2o", "potassio", "potassium") or 0.0,
    }


def _fertilizer_name(fertilizer: dict[str, Any]) -> str | None:
    return (
        fertilizer.get("name")
        or fertilizer.get("nome")
        or fertilizer.get("commercial_name")
        or fertilizer.get("nome_comercial")
    )


def solve_fertilizer_doses(
    nutrient_recommendation: dict[str, Any],
    fertilizer_source: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    targets = {
        "n": nutrient_recommendation.get("n_kg_ha"),
        "p2o5": nutrient_recommendation.get("p2o5_kg_ha"),
        "k2o": nutrient_recommendation.get("k2o_kg_ha"),
    }

    fertilizers = _extract_fertilizers(fertilizer_source)
    suggestions: list[dict[str, Any]] = []

    for nutrient, target in targets.items():
        if target is None:
            continue

        best: dict[str, Any] | None = None

        for fertilizer in fertilizers:
            nutrients = _fertilizer_nutrients(fertilizer)
            concentration = nutrients[nutrient]

            if concentration <= 0:
                continue

            dose = float(target) / (concentration / 100)

            supplied = {
                "n": dose * nutrients["n"] / 100,
                "p2o5": dose * nutrients["p2o5"] / 100,
                "k2o": dose * nutrients["k2o"] / 100,
            }

            residual = {
                "n": supplied["n"] - (targets["n"] or 0),
                "p2o5": supplied["p2o5"] - (targets["p2o5"] or 0),
                "k2o": supplied["k2o"] - (targets["k2o"] or 0),
            }

            penalty = sum(abs(v) for v in residual.values())

            candidate = {
                "target_nutrient": nutrient.upper(),
                "fertilizer_name": _fertilizer_name(fertilizer),
                "fertilizer": fertilizer,
                "dose_kg_ha": round(dose, 2),
                "supplied_kg_ha": {k: round(v, 2) for k, v in supplied.items()},
                "residual_kg_ha": {k: round(v, 2) for k, v in residual.items()},
                "score_penalty": round(penalty, 2),
            }

            if best is None or candidate["score_penalty"] < best["score_penalty"]:
                best = candidate

        if best:
            suggestions.append(best)

    return suggestions
