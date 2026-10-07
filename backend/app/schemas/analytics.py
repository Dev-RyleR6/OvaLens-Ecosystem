from typing import List

from pydantic import BaseModel, ConfigDict


class HatcheryOverviewKPIs(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_eggs_scanned: int
    total_fertile: int
    total_infertile: int
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
    fertility_rate: float
    hatched_count: int
    hatchability_rate: float


class BreedComparisonResponse(BaseModel):
    breeds: List[BreedMetricItem]


class MortalityTrendsResponse(BaseModel):
    day_10_cull_rate: float
    total_culled_eggs: int


class EconomicYieldResponse(BaseModel):
    penoy_culled_day_10: int
    penoy_unit_price_php: float = 14.00
    estimated_penoy_salvage_value_php: float
    projected_duckling_revenue_php: float
    electricity_saved_estimated_php: float
    total_economic_benefit_php: float


class Day10OutcomeItem(BaseModel):
    stage_name: str
    day_marker: int = 10
    infertile_count: int
    cull_rate_percentage: float
    description: str


class BreedDay10Outcome(BaseModel):
    breed: str
    initial_eggs: int
    day_10_infertile_penoy: int
    hatched_ducklings: int
    day_10_cull_rate: float
    final_hatchability_rate: float


class MortalityProgressionResponse(BaseModel):
    day_10_outcome: Day10OutcomeItem
    breed_breakdown: List[BreedDay10Outcome]
