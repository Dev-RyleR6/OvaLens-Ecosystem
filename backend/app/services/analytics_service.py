from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.batch import BatchModel, DuckBreed, BatchStatus
from app.models.session import CandlingSessionModel, CandlingStage
from app.models.scan import EggScanModel, FertilityClass
from app.schemas.analytics import (
    HatcheryOverviewKPIs, BreedComparisonResponse, BreedMetricItem,
    MortalityTrendsResponse, EconomicYieldResponse
)


class AnalyticsService:
    @staticmethod
    def get_overview_kpis(db: Session) -> HatcheryOverviewKPIs:
        # Total scans
        total_scans = db.query(func.count(EggScanModel.scan_id)).scalar() or 0
        
        # Class distribution
        fertile_count = db.query(func.count(EggScanModel.scan_id)).filter(EggScanModel.final_class == FertilityClass.FERTILE).scalar() or 0
        infertile_count = db.query(func.count(EggScanModel.scan_id)).filter(EggScanModel.final_class == FertilityClass.INFERTILE).scalar() or 0
        abnormal_count = db.query(func.count(EggScanModel.scan_id)).filter(EggScanModel.final_class == FertilityClass.ABNORMAL).scalar() or 0
        
        fertility_rate = (fertile_count / total_scans * 100.0) if total_scans > 0 else 0.0
        cull_rate = ((infertile_count + abnormal_count) / total_scans * 100.0) if total_scans > 0 else 0.0

        # Hatched ducklings & total eggs set across all batches
        batch_totals = db.query(
            func.coalesce(func.sum(BatchModel.hatched_count), 0).label("hatched"),
            func.coalesce(func.sum(BatchModel.initial_egg_count), 0).label("initial")
        ).first()

        hatched = batch_totals.hatched or 0
        initial = batch_totals.initial or 0
        hatchability = (hatched / initial * 100.0) if initial > 0 else 0.0

        active_batches = db.query(func.count(BatchModel.batch_id)).filter(BatchModel.status.in_([BatchStatus.INCUBATING, BatchStatus.CANDLING_DUE])).scalar() or 0
        avg_lat = db.query(func.coalesce(func.avg(EggScanModel.inference_ms), 0.0)).scalar() or 0.0

        return HatcheryOverviewKPIs(
            total_eggs_scanned=total_scans,
            overall_fertility_rate=round(fertility_rate, 2),
            day_10_cull_rate=round(cull_rate, 2),
            total_hatched_ducklings=hatched,
            overall_hatchability_rate=round(hatchability, 2),
            active_batches_count=active_batches,
            average_inference_latency_ms=round(float(avg_lat), 2)
        )

    @staticmethod
    def get_breed_comparison(db: Session) -> BreedComparisonResponse:
        breed_items = []
        for breed in DuckBreed:
            # Batch stats for breed
            batch_stats = db.query(
                func.coalesce(func.sum(BatchModel.initial_egg_count), 0).label("initial"),
                func.coalesce(func.sum(BatchModel.hatched_count), 0).label("hatched")
            ).filter(BatchModel.breed == breed).first()

            initial = batch_stats.initial or 0
            hatched = batch_stats.hatched or 0

            # Scan stats for breed
            scan_stats = db.query(
                func.count(EggScanModel.scan_id).label("total_scans"),
                func.coalesce(func.sum(func.case((EggScanModel.final_class == FertilityClass.FERTILE, 1), else_=0)), 0).label("fertile"),
                func.coalesce(func.sum(func.case((EggScanModel.final_class == FertilityClass.INFERTILE, 1), else_=0)), 0).label("infertile"),
                func.coalesce(func.sum(func.case((EggScanModel.final_class == FertilityClass.ABNORMAL, 1), else_=0)), 0).label("abnormal")
            ).join(BatchModel, EggScanModel.batch_id == BatchModel.batch_id).filter(BatchModel.breed == breed).first()

            total_scans = scan_stats.total_scans or 0
            fertile = scan_stats.fertile or 0
            infertile = scan_stats.infertile or 0
            abnormal = scan_stats.abnormal or 0

            fertility_rate = (fertile / total_scans * 100.0) if total_scans > 0 else 0.0
            hatchability_rate = (hatched / initial * 100.0) if initial > 0 else 0.0

            breed_items.append(BreedMetricItem(
                breed=breed.value,
                total_eggs=total_scans if total_scans > 0 else initial,
                fertile_count=fertile,
                infertile_count=infertile,
                abnormal_count=abnormal,
                fertility_rate=round(fertility_rate, 2),
                hatched_count=hatched,
                hatchability_rate=round(hatchability_rate, 2)
            ))

        return BreedComparisonResponse(breeds=breed_items)

    @staticmethod
    def get_mortality_trends(db: Session) -> MortalityTrendsResponse:
        # Day 10 stats
        d10_stats = db.query(
            func.coalesce(func.sum(CandlingSessionModel.total_scanned), 0).label("total"),
            func.coalesce(func.sum(CandlingSessionModel.abnormal_count), 0).label("abnormal")
        ).filter(CandlingSessionModel.stage == CandlingStage.DAY_10).first()

        d10_total = d10_stats.total or 0
        d10_abnormal = d10_stats.abnormal or 0
        d10_early_rate = (d10_abnormal / d10_total * 100.0) if d10_total > 0 else 0.0

        # Day 18 stats
        d18_stats = db.query(
            func.coalesce(func.sum(CandlingSessionModel.total_scanned), 0).label("total"),
            func.coalesce(func.sum(CandlingSessionModel.abnormal_count), 0).label("abnormal")
        ).filter(CandlingSessionModel.stage == CandlingStage.DAY_18).first()

        d18_total = d18_stats.total or 0
        d18_abnormal = d18_stats.abnormal or 0
        d18_mid_rate = (d18_abnormal / d18_total * 100.0) if d18_total > 0 else 0.0

        # Day 25 stats
        d25_stats = db.query(
            func.coalesce(func.sum(CandlingSessionModel.total_scanned), 0).label("total"),
            func.coalesce(func.sum(CandlingSessionModel.abnormal_count), 0).label("abnormal")
        ).filter(CandlingSessionModel.stage == CandlingStage.DAY_25).first()

        d25_total = d25_stats.total or 0
        d25_abnormal = d25_stats.abnormal or 0
        d25_late_rate = (d25_abnormal / d25_total * 100.0) if d25_total > 0 else 0.0

        total_culled = db.query(func.count(EggScanModel.scan_id)).filter(EggScanModel.final_class.in_([FertilityClass.INFERTILE, FertilityClass.ABNORMAL])).scalar() or 0

        return MortalityTrendsResponse(
            day_10_early_mortality_rate=round(d10_early_rate, 2),
            day_18_mid_mortality_rate=round(d18_mid_rate, 2),
            day_25_late_mortality_rate=round(d25_late_rate, 2),
            total_culled_eggs=total_culled
        )

    @staticmethod
    def get_economic_yield(db: Session) -> EconomicYieldResponse:
        # Day 10 infertile eggs (marketable as commercial Penoy)
        penoy_day_10 = db.query(
            func.coalesce(func.sum(CandlingSessionModel.infertile_count), 0)
        ).filter(CandlingSessionModel.stage == CandlingStage.DAY_10).scalar() or 0

        # Total hatched ducklings
        hatched_total = db.query(func.coalesce(func.sum(BatchModel.hatched_count), 0)).scalar() or 0

        # Total culled eggs
        total_culled = db.query(
            func.coalesce(func.sum(CandlingSessionModel.infertile_count + CandlingSessionModel.abnormal_count), 0)
        ).scalar() or 0

        penoy_value = penoy_day_10 * 14.00  # ₱14/penoy
        duckling_revenue = hatched_total * 40.00  # ₱40/duckling
        electricity_saved = total_culled * 2.50  # ₱2.50 per culled egg in incubator electricity

        return EconomicYieldResponse(
            penoy_culled_day_10=penoy_day_10,
            estimated_penoy_salvage_value_php=round(penoy_value, 2),
            projected_duckling_revenue_php=round(duckling_revenue, 2),
            electricity_saved_estimated_php=round(electricity_saved, 2),
            total_economic_benefit_php=round(penoy_value + duckling_revenue + electricity_saved, 2)
        )
