from typing import Any

from app.recommendation.common import num as _num


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


