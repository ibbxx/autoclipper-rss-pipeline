from fastapi import APIRouter
from app.api.routes.health import router as health
from app.api.routes.channels import router as channels
from app.api.routes.videos import router as videos

router = APIRouter()
router.include_router(health)
router.include_router(channels)
router.include_router(videos)
