from fastapi import APIRouter

from app.api.v1.routers import auth_router

router = APIRouter(prefix="/api/v1", tags=["api"])
router.include_router(auth_router.router, prefix="/", tags=["auth"])