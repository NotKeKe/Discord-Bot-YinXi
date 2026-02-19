from fastapi import APIRouter

from . import player

router = APIRouter(
    prefix="/api",
    tags=["API"],
    responses={404: {"description": "Not found"}},
)

router.include_router(player.router)

__all__ = [
    "router"
]