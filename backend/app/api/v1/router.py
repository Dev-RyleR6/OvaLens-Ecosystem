from fastapi import APIRouter
from app.api.v1.endpoints import auth, devices, batches, sessions, scans, analytics, reports, users, audit_logs

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(audit_logs.router)
api_router.include_router(devices.router)
api_router.include_router(batches.router)
api_router.include_router(sessions.router)
api_router.include_router(scans.router)
api_router.include_router(analytics.router)
api_router.include_router(reports.router)
