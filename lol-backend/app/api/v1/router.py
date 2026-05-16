from fastapi import APIRouter

from app.api.endpoints import match, player, stats, analysis, opgg, coach

api_router = APIRouter()

api_router.include_router(match.router)
api_router.include_router(player.router)
api_router.include_router(stats.router)
api_router.include_router(analysis.router)
api_router.include_router(opgg.router)
api_router.include_router(coach.router)
