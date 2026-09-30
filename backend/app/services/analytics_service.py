from sqlalchemy.orm import Session
from sqlalchemy import func, case

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
        
        fertility_rate = (fertile_count / total_scans * 100.0) if total_scans > 0 else 0.0
        cull_rate = (infertile_count / total_scans * 100.0) if total_scans > 0 else 0.0

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
                func.coalesce(func.sum(case((EggScanModel.final_class == FertilityClass.FERTILE, 1), else_=0)), 0).label("fertile"),
                func.coalesce(func.sum(case((EggScanModel.final_class == FertilityClass.INFERTILE, 1), else_=0)), 0).label("infertile")
            ).join(BatchModel, EggScanModel.batch_id == BatchModel.batch_id).filter(BatchModel.breed == breed).first()

            total_scans = scan_stats.total_scans or 0
            fertile = scan_stats.fertile or 0
            infertile = scan_stats.infertile or 0
            abnormal = 0

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
            func.coalesce(func.sum(CandlingSessionModel.infertile_count), 0).label("infertile")
        ).filter(CandlingSessionModel.stage == CandlingStage.DAY_10).first()

        d10_total = d10_stats.total or 0
        d10_infertile = d10_stats.infertile or 0
        d10_early_rate = (d10_infertile / d10_total * 100.0) if d10_total > 0 else 0.0

        total_culled = db.query(func.count(EggScanModel.scan_id)).filter(EggScanModel.final_class == FertilityClass.INFERTILE).scalar() or 0

        return MortalityTrendsResponse(
            day_10_early_mortality_rate=round(d10_early_rate, 2),
            day_18_mid_mortality_rate=0.0,
            day_25_late_mortality_rate=0.0,
            total_culled_eggs=total_culled
        )

    @staticmethod
    def get_economic_yield(db: Session) -> EconomicYieldResponse:
        from app.models.settings import HatcherySettingsModel

        settings = db.query(HatcherySettingsModel).first()
        penoy_price = float(settings.penoy_unit_price_php) if settings else 14.00
        duckling_price = float(settings.duckling_unit_price_php) if settings else 40.00
        kwh_rate = float(settings.electricity_kwh_rate_php) if settings else 12.50
        kwh_saved_per_egg = float(settings.kwh_saved_per_culled_egg) if settings else 0.2000

        power_saved_per_culled_egg = kwh_rate * kwh_saved_per_egg

        # Day 10 infertile eggs (marketable as commercial Penoy)
        penoy_day_10 = db.query(
            func.coalesce(func.sum(CandlingSessionModel.infertile_count), 0)
        ).filter(CandlingSessionModel.stage == CandlingStage.DAY_10).scalar() or 0

        # Total hatched ducklings
        hatched_total = db.query(func.coalesce(func.sum(BatchModel.hatched_count), 0)).scalar() or 0

        # Total culled eggs (both infertile penoy and abnormal/dead)
        total_culled = db.query(
            func.coalesce(func.sum(CandlingSessionModel.infertile_count + CandlingSessionModel.abnormal_count), 0)
        ).scalar() or 0

        penoy_value = penoy_day_10 * penoy_price
        duckling_revenue = hatched_total * duckling_price
        electricity_saved = total_culled * power_saved_per_culled_egg

        return EconomicYieldResponse(
            penoy_culled_day_10=penoy_day_10,
            penoy_unit_price_php=penoy_price,
            estimated_penoy_salvage_value_php=round(penoy_value, 2),
            projected_duckling_revenue_php=round(duckling_revenue, 2),
            electricity_saved_estimated_php=round(electricity_saved, 2),
            total_economic_benefit_php=round(penoy_value + duckling_revenue + electricity_saved, 2)
        )

    @staticmethod
    def get_mortality_progression(db: Session):
        from app.schemas.analytics import (
            MortalityProgressionResponse, StageMortalityItem, BreedMortalityProgression
        )

        # Stage 1: Day 10 Candling (Early unfertilized / non-viable penoy salvage)
        d10_stats = db.query(
            func.coalesce(func.sum(CandlingSessionModel.total_scanned), 0).label("scanned"),
            func.coalesce(func.sum(CandlingSessionModel.infertile_count), 0).label("infertile")
        ).filter(CandlingSessionModel.stage == CandlingStage.DAY_10).first()

        d10_scanned = d10_stats.scanned or 1
        d10_culled = d10_stats.infertile or 0
        d10_rate = (d10_culled / d10_scanned * 100.0) if d10_scanned > 0 else 0.0

        overall_stages = [
            StageMortalityItem(
                stage_name="Day 10 (Candling Inspection)",
                day_marker=10,
                culled_count=d10_culled,
                cull_rate_percentage=round(d10_rate, 2),
                description="Infertile clear yolks and non-viable embryos salvaged as Penoy @ ₱14.00."
            ),
            StageMortalityItem(
                stage_name="Day 18 (Hatcher Basket Transfer)",
                day_marker=18,
                culled_count=0,
                cull_rate_percentage=0.0,
                description="Lockdown transfer of viable fertile eggs from incubation trays to hatcher baskets."
            ),
            StageMortalityItem(
                stage_name="Day 28 (Final Hatch)",
                day_marker=28,
                culled_count=0,
                cull_rate_percentage=0.0,
                description="Final duckling emergence and unhatched cull counting."
            )
        ]

        # Breed breakdown
        breed_breakdowns = []
        for breed in DuckBreed:
            batch_data = db.query(
                func.coalesce(func.sum(BatchModel.initial_egg_count), 0).label("initial"),
                func.coalesce(func.sum(BatchModel.hatched_count), 0).label("hatched")
            ).filter(BatchModel.breed == breed).first()

            init_eggs = batch_data.initial or 0
            hatched = batch_data.hatched or 0

            # Day 10 stats for breed
            b_d10 = db.query(
                func.coalesce(func.sum(CandlingSessionModel.infertile_count), 0).label("infertile"),
                func.coalesce(func.sum(CandlingSessionModel.total_scanned), 0).label("scanned")
            ).join(BatchModel, CandlingSessionModel.batch_id == BatchModel.batch_id).filter(
                BatchModel.breed == breed, CandlingSessionModel.stage == CandlingStage.DAY_10
            ).first()

            d10_inf = b_d10.infertile or 0
            d10_tot = b_d10.scanned or 1

            early_m = (d10_inf / d10_tot * 100.0) if d10_tot > 0 else 0.0
            hatch_r = (hatched / init_eggs * 100.0) if init_eggs > 0 else 0.0

            breed_breakdowns.append(BreedMortalityProgression(
                breed=breed.value,
                initial_eggs=init_eggs,
                day_10_infertile_penoy=d10_inf,
                day_10_early_dead=0,
                day_18_mid_dead=0,
                day_25_late_dead=0,
                hatched_ducklings=hatched,
                early_mortality_rate=round(early_m, 2),
                mid_mortality_rate=0.0,
                late_mortality_rate=0.0,
                final_hatchability_rate=round(hatch_r, 2)
            ))

        return MortalityProgressionResponse(
            overall_stages=overall_stages,
            breed_breakdown=breed_breakdowns
        )
