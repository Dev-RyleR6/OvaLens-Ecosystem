from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.analytics import (
    HatcheryOverviewKPIs, BreedComparisonResponse, MortalityTrendsResponse, EconomicYieldResponse
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Hatchery Analytics"])


@router.get("/overview", response_model=HatcheryOverviewKPIs, summary="Get overall hatchery KPIs")
def get_overview(db: Session = Depends(get_db)):
    return AnalyticsService.get_overview_kpis(db)


@router.get("/breed-comparison", response_model=BreedComparisonResponse, summary="Get breed fertility and hatch yield comparisons")
def get_breed_comparison(db: Session = Depends(get_db)):
    return AnalyticsService.get_breed_comparison(db)


@router.get("/mortality-trends", response_model=MortalityTrendsResponse, summary="Get Day 10 vs Day 18 vs Day 25 mortality breakdown")
def get_mortality_trends(db: Session = Depends(get_db)):
    return AnalyticsService.get_mortality_trends(db)


@router.get("/economic-yield", response_model=EconomicYieldResponse, summary="Get Day-10 Penoy salvage revenue & financial ROI")
def get_economic_yield(db: Session = Depends(get_db)):
    return AnalyticsService.get_economic_yield(db)
