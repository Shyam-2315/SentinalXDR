from fastapi import APIRouter

from app.api.routes.agents import router as agents_router
from app.api.routes.alerts import router as alerts_router
from app.api.routes.attack_chains import incident_router as incident_attack_chain_router
from app.api.routes.attack_chains import router as attack_chains_router
from app.api.routes.auth import router as auth_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.detections import router as detections_router
from app.api.routes.events import router as events_router
from app.api.routes.incidents import router as incidents_router


def build_api_router() -> APIRouter:
    router = APIRouter()
    router.include_router(auth_router)
    router.include_router(agents_router)
    router.include_router(events_router)
    router.include_router(detections_router)
    router.include_router(alerts_router)
    router.include_router(incidents_router)
    router.include_router(attack_chains_router)
    router.include_router(incident_attack_chain_router)
    router.include_router(dashboard_router)
    return router


api_router = build_api_router()
