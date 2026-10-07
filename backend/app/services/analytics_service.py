from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.batch import BatchModel, BatchStatus, DuckBreed
from app.models.scan import EggScanModel, FertilityClass
from app.models.session import CandlingSessionModel, CandlingStage
from app.schemas.analytics import (
    BreedComparisonResponse,
    BreedDay10Outcome,
    BreedMetricItem,
    Day10OutcomeItem,
    EconomicYieldResponse,
    HatcheryOverviewKPIs,
    MortalityProgressionResponse,
    MortalityTrendsResponse,
)


class AnalyticsService:
    """Analytics for the Day 10, two-class candling contract."""

    @staticmethod
    def get_overview_kpis(db: Session) -> HatcheryOverviewKPIs:
        total_scans = db.query(func.count(EggScanModel.scan_id)).scalar() or 0
        fertile_count = db.query(func.count(EggScanModel.scan_id)).filter(
            EggScanModel.final_class == FertilityClass.FERTILE
        ).scalar() or 0
        infertile_count = db.query(func.count(EggScanModel.scan_id)).filter(
            EggScanModel.final_class == FertilityClass.INFERTILE
        ).scalar() or 0

        batch_totals = db.query(
            func.coalesce(func.sum(BatchModel.hatched_count), 0).label("hatched"),
            func.coalesce(func.sum(BatchModel.initial_egg_count), 0).label("initial"),
        ).first()
        hatched = batch_totals.hatched or 0
        initial = batch_totals.initial or 0
        active_batches = db.query(func.count(BatchModel.batch_id)).filter(
            BatchModel.status.in_([BatchStatus.INCUBATING, BatchStatus.CANDLING_DUE])
        ).scalar() or 0
        avg_latency = db.query(func.coalesce(func.avg(EggScanModel.inference_ms), 0.0)).scalar() or 0.0

        return HatcheryOverviewKPIs(
            total_eggs_scanned=total_scans,
            total_fertile=fertile_count,
            total_infertile=infertile_count,
            overall_fertility_rate=round(fertile_count / total_scans * 100, 2) if total_scans else 0.0,
            day_10_cull_rate=round(infertile_count / total_scans * 100, 2) if total_scans else 0.0,
            total_hatched_ducklings=hatched,
            overall_hatchability_rate=round(hatched / initial * 100, 2) if initial else 0.0,
            active_batches_count=active_batches,
            average_inference_latency_ms=round(float(avg_latency), 2),
        )

    @staticmethod
    def get_breed_comparison(db: Session) -> BreedComparisonResponse:
        items = []
        for breed in DuckBreed:
            batch_stats = db.query(
                func.coalesce(func.sum(BatchModel.initial_egg_count), 0).label("initial"),
                func.coalesce(func.sum(BatchModel.hatched_count), 0).label("hatched"),
            ).filter(BatchModel.breed == breed).first()
            scan_stats = db.query(
                func.count(EggScanModel.scan_id).label("total"),
                func.coalesce(func.sum(case((EggScanModel.final_class == FertilityClass.FERTILE, 1), else_=0)), 0).label("fertile"),
                func.coalesce(func.sum(case((EggScanModel.final_class == FertilityClass.INFERTILE, 1), else_=0)), 0).label("infertile"),
            ).join(BatchModel, EggScanModel.batch_id == BatchModel.batch_id).filter(
                BatchModel.breed == breed
            ).first()

            initial = batch_stats.initial or 0
            hatched = batch_stats.hatched or 0
            total = scan_stats.total or 0
            fertile = scan_stats.fertile or 0
            items.append(BreedMetricItem(
                breed=breed.value,
                total_eggs=total if total else initial,
                fertile_count=fertile,
                infertile_count=scan_stats.infertile or 0,
                fertility_rate=round(fertile / total * 100, 2) if total else 0.0,
                hatched_count=hatched,
                hatchability_rate=round(hatched / initial * 100, 2) if initial else 0.0,
            ))
        return BreedComparisonResponse(breeds=items)

    @staticmethod
    def _day_10_totals(db: Session):
        return db.query(
            func.coalesce(func.sum(CandlingSessionModel.total_scanned), 0).label("total"),
            func.coalesce(func.sum(CandlingSessionModel.infertile_count), 0).label("infertile"),
        ).filter(CandlingSessionModel.stage == CandlingStage.DAY_10).first()

    @staticmethod
    def get_mortality_trends(db: Session) -> MortalityTrendsResponse:
        stats = AnalyticsService._day_10_totals(db)
        total = stats.total or 0
        infertile = stats.infertile or 0
        return MortalityTrendsResponse(
            day_10_cull_rate=round(infertile / total * 100, 2) if total else 0.0,
            total_culled_eggs=infertile,
        )

    @staticmethod
    def get_economic_yield(db: Session) -> EconomicYieldResponse:
        from app.models.settings import HatcherySettingsModel

        settings = db.query(HatcherySettingsModel).first()
        penoy_price = float(settings.penoy_unit_price_php) if settings else 14.0
        duckling_price = float(settings.duckling_unit_price_php) if settings else 40.0
        savings_per_egg = (
            float(settings.electricity_kwh_rate_php) * float(settings.kwh_saved_per_culled_egg)
            if settings else 2.5
        )
        infertile = AnalyticsService._day_10_totals(db).infertile or 0
        hatched = db.query(func.coalesce(func.sum(BatchModel.hatched_count), 0)).scalar() or 0
        penoy_value = infertile * penoy_price
        duckling_revenue = hatched * duckling_price
        electricity_saved = infertile * savings_per_egg
        return EconomicYieldResponse(
            penoy_culled_day_10=infertile,
            penoy_unit_price_php=penoy_price,
            estimated_penoy_salvage_value_php=round(penoy_value, 2),
            projected_duckling_revenue_php=round(duckling_revenue, 2),
            electricity_saved_estimated_php=round(electricity_saved, 2),
            total_economic_benefit_php=round(penoy_value + duckling_revenue + electricity_saved, 2),
        )

    @staticmethod
    def get_mortality_progression(db: Session) -> MortalityProgressionResponse:
        stats = AnalyticsService._day_10_totals(db)
        total = stats.total or 0
        infertile = stats.infertile or 0
        breed_breakdown = []
        for breed in DuckBreed:
            batch_data = db.query(
                func.coalesce(func.sum(BatchModel.initial_egg_count), 0).label("initial"),
                func.coalesce(func.sum(BatchModel.hatched_count), 0).label("hatched"),
            ).filter(BatchModel.breed == breed).first()
            breed_stats = db.query(
                func.coalesce(func.sum(CandlingSessionModel.total_scanned), 0).label("total"),
                func.coalesce(func.sum(CandlingSessionModel.infertile_count), 0).label("infertile"),
            ).join(BatchModel, CandlingSessionModel.batch_id == BatchModel.batch_id).filter(
                BatchModel.breed == breed,
                CandlingSessionModel.stage == CandlingStage.DAY_10,
            ).first()
            breed_total = breed_stats.total or 0
            breed_infertile = breed_stats.infertile or 0
            initial = batch_data.initial or 0
            hatched = batch_data.hatched or 0
            breed_breakdown.append(BreedDay10Outcome(
                breed=breed.value,
                initial_eggs=initial,
                day_10_infertile_penoy=breed_infertile,
                hatched_ducklings=hatched,
                day_10_cull_rate=round(breed_infertile / breed_total * 100, 2) if breed_total else 0.0,
                final_hatchability_rate=round(hatched / initial * 100, 2) if initial else 0.0,
            ))

        return MortalityProgressionResponse(
            day_10_outcome=Day10OutcomeItem(
                stage_name="Day 10 Candling",
                infertile_count=infertile,
                cull_rate_percentage=round(infertile / total * 100, 2) if total else 0.0,
                description="Infertile eggs rejected during the single candling checkpoint and salvaged as Penoy.",
            ),
            breed_breakdown=breed_breakdown,
        )
