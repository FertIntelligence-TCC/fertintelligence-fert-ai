from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RecommendationType(str, Enum):
    ACIDITY_SALINITY = "ACIDITY_SALINITY"
    FERTILIZATION = "FERTILIZATION"


class FertilizerGroup(str, Enum):
    PRIVATE = "PRIVATE"
    PUBLIC = "PUBLIC"
    DEFAULT = "DEFAULT"


class RecommendationRequest(BaseModel):
    recommendation_type: RecommendationType
    property: dict[str, Any] = Field(default_factory=dict)
    plot: dict[str, Any] = Field(default_factory=dict)

    physical_analysis: dict[str, Any] | None = None
    fertility_analysis: dict[str, Any] | None = None
    saturation_extract_analysis: dict[str, Any] | None = None

    annual_crop_folder: dict[str, Any] | None = None
    crop: dict[str, Any] | None = None

    crop_fertilization_table: dict[str, Any] | None = None
    soil_fertility_interpretation_table: dict[str, Any] | None = None
    leaf_analysis_interpretation_table: dict[str, Any] | None = None

    fertilizer_group: FertilizerGroup
    fertilizer_source: dict[str, Any] | None = None


class RecommendationResponse(BaseModel):
    recommendation_type: RecommendationType
    fertilizer_group: FertilizerGroup
    fertilizer_source: dict[str, Any] | None = None
    status: str

    data_used: dict[str, Any]
    interpretation: dict[str, Any]
    diagnosis: list[str]
    correction_recommendation: dict[str, Any]
    fertilization_recommendation: dict[str, Any]
    fertilizer_suggestions: list[dict[str, Any]]
    technical_alerts: list[str]

    next_steps: list[str]
