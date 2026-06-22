from typing import Any

from app.recommendation.common import num as _num


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
