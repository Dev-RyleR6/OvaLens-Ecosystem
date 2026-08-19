from typing import List, Dict
from pydantic import BaseModel


class HatcheryOverviewKPIs(BaseModel):
    total_eggs_scanned: int
    overall_fertility_rate: float
    day_10_cull_rate: float
    total_hatched_ducklings: int
    overall_hatchability_rate: float
    active_batches_count: int
    average_inference_latency_ms: float


class BreedMetricItem(BaseModel):
    breed: str
    total_eggs: int
    fertile_count: int
    infertile_count: int
    abnormal_count: int
    fertility_rate: float
    hatched_count: int
    hatchability_rate: float


class BreedComparisonResponse(BaseModel):
    breeds: List[BreedMetricItem]


class MortalityTrendsResponse(BaseModel):
    day_10_early_mortality_rate: float
    day_18_mid_mortality_rate: float
    day_25_late_mortality_rate: float
    total_culled_eggs: int


class EconomicYieldResponse(BaseModel):
    penoy_culled_day_10: int
    estimated_penoy_salvage_value_php: float  # Infertile * ₱14
    projected_duckling_revenue_php: float     # Hatched * ₱40
    electricity_saved_estimated_php: float    # Culled * ₱2.50
    total_economic_benefit_php: float
