import math
from datetime import datetime, timezone
from typing import Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.batch import BatchModel, DuckBreed, BatchStage, BatchStatus
from app.models.scan import EggScanModel, FertilityClass
from app.models.settings import HatcherySettingsModel
from app.schemas.batch import BatchForecastResponse
from app.core.exceptions import EntityNotFoundException


class ForecastService:
    """
    Biological Duck Embryo Hatch Yield & Economic Predictive Engine.
    Models embryonic viability retention across 28 days of incubation.
    """

    # Baseline breed fertility & post-Day-10 embryo survival parameters
    BREED_PARAMETERS: Dict[DuckBreed, Dict[str, float]] = {
        DuckBreed.KAYUMANGGI: {
            "baseline_fertility": 88.5,
            "post_day10_viability_rate": 89.0,  # ~89% of Day-10 fertile eggs survive to Day 28 hatch
            "day18_mortality_factor": 6.5,
            "day25_mortality_factor": 4.5,
        },
        DuckBreed.ITIM: {
            "baseline_fertility": 82.0,
            "post_day10_viability_rate": 84.0,  # Native breeds have slightly higher late mortality
            "day18_mortality_factor": 9.0,
            "day25_mortality_factor": 7.0,
        },
        DuckBreed.KHAKI: {
            "baseline_fertility": 86.0,
            "post_day10_viability_rate": 86.5,
            "day18_mortality_factor": 7.5,
            "day25_mortality_factor": 6.0,
        },
    }

    @classmethod
    def get_batch_forecast(cls, db: Session, batch_id: str) -> BatchForecastResponse:
        batch = db.query(BatchModel).filter(BatchModel.batch_id == batch_id).first()
        if not batch:
            raise EntityNotFoundException(f"Batch '{batch_id}' not found.")

        settings = db.query(HatcherySettingsModel).first()
        penoy_price = settings.penoy_unit_price_php if settings else 14.0
        duckling_price = settings.duckling_unit_price_php if settings else 40.0

        # Retrieve actual scan data for this batch
        scan_counts = db.query(
            EggScanModel.final_class,
            func.count(EggScanModel.scan_id).label("count")
        ).filter(EggScanModel.batch_id == batch_id).group_by(EggScanModel.final_class).all()

        scans_map = {c[0]: c[1] for c in scan_counts}
        fertile_scanned = scans_map.get(FertilityClass.FERTILE, 0)
        infertile_penoy = scans_map.get(FertilityClass.INFERTILE, 0)
        abnormal_scanned = scans_map.get(FertilityClass.ABNORMAL, 0)
        total_scanned = fertile_scanned + infertile_penoy + abnormal_scanned

        breed_params = cls.BREED_PARAMETERS.get(
            batch.breed,
            cls.BREED_PARAMETERS[DuckBreed.KAYUMANGGI]
        )
        baseline_fertility = breed_params["baseline_fertility"]
        viability_rate = breed_params["post_day10_viability_rate"]

        # Calculate detected or estimated fertility
        if total_scanned > 0:
            detected_fertility_rate = round((fertile_scanned / total_scanned) * 100, 2)
            penoy_count = infertile_penoy
            confidence_level = "HIGH" if total_scanned >= (batch.initial_egg_count * 0.5) else "MEDIUM"
        else:
            # Fallback to breed baseline before candling
            detected_fertility_rate = baseline_fertility
            penoy_count = math.floor(batch.initial_egg_count * (1.0 - (baseline_fertility / 100.0)))
            confidence_level = "LOW"

        # Predicted Day 28 Hatched Count
        if total_scanned > 0 and fertile_scanned > 0:
            # If partially scanned, scale up proportionally to total set egg count
            projected_fertile_total = (fertile_scanned / total_scanned) * batch.initial_egg_count
            predicted_hatched = math.floor(projected_fertile_total * (viability_rate / 100.0))
        else:
            predicted_hatched = math.floor(batch.initial_egg_count * (baseline_fertility / 100.0) * (viability_rate / 100.0))

        # Clamp hatched count within biological boundary
        predicted_hatched = max(0, min(predicted_hatched, batch.initial_egg_count))
        predicted_hatchability = round((predicted_hatched / batch.initial_egg_count) * 100, 2) if batch.initial_egg_count > 0 else 0.0
        predicted_unhatched = max(0, batch.initial_egg_count - predicted_hatched)

        # Financial Revenue Forecasts
        penoy_realized_rev = round(penoy_count * penoy_price, 2)
        projected_duckling_rev = round(predicted_hatched * duckling_price, 2)
        projected_total_rev = round(penoy_realized_rev + projected_duckling_rev, 2)

        # Anomaly Diagnostics
        anomaly_status = "OPTIMAL"
        advisory_notes: List[str] = []

        fertility_diff = detected_fertility_rate - baseline_fertility
        if fertility_diff < -15.0:
            anomaly_status = "CRITICAL"
            advisory_notes.append(
                f"Severe fertility deficiency ({detected_fertility_rate:.1f}% vs {baseline_fertility:.1f}% breed baseline). "
                "Inspect setter temperature calibration, humidity levels, and breeder flock nutritional status immediately."
            )
        elif fertility_diff < -8.0:
            anomaly_status = "WARNING"
            advisory_notes.append(
                f"Fertility is below typical {batch.breed.value} benchmarks by {abs(fertility_diff):.1f}%. "
                "Monitor Day 18 moisture loss and air cell development closely."
            )
        else:
            advisory_notes.append(
                f"Batch embryonic progression is optimal ({detected_fertility_rate:.1f}% fertility). "
                f"Projected harvest yield of ~{predicted_hatched} viable ducklings on Day 28."
            )

        if batch.status == BatchStatus.COMPLETED and batch.hatched_count:
            # If batch is already hatched, show actuals vs predictions
            advisory_notes.append(
                f"Batch completed: Actual hatched ducklings were {batch.hatched_count} "
                f"({((batch.hatched_count / batch.initial_egg_count) * 100):.1f}% hatchability)."
            )

        now = datetime.now(timezone.utc)
        set_date = batch.set_date if batch.set_date.tzinfo else batch.set_date.replace(tzinfo=timezone.utc)
        elapsed_days = max(0, (now - set_date).days)

        return BatchForecastResponse(
            batch_id=batch.batch_id,
            batch_code=batch.batch_code,
            breed=batch.breed,
            initial_egg_count=batch.initial_egg_count,
            elapsed_days=elapsed_days,
            current_stage=batch.current_stage,
            status=batch.status,
            detected_fertility_rate=detected_fertility_rate,
            breed_baseline_fertility=baseline_fertility,
            expected_embryo_viability_rate=viability_rate,
            predicted_hatched_count=predicted_hatched,
            predicted_hatchability_rate=predicted_hatchability,
            predicted_unhatched_count=predicted_unhatched,
            penoy_realized_revenue_php=penoy_realized_rev,
            projected_duckling_revenue_php=projected_duckling_rev,
            projected_total_revenue_php=projected_total_rev,
            anomaly_status=anomaly_status,
            confidence_level=confidence_level,
            advisory_notes=advisory_notes
        )
