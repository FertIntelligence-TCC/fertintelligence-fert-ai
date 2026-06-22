from typing import Any


def num(data: dict[str, Any] | None, *keys: str) -> float | None:
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


def round_optional(value: float | None, digits: int = 2) -> float | None:
    if value is None:
        return None
    return round(value, digits)
