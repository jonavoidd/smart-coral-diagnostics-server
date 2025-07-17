from fastapi import APIRouter
from app.api.v1.endpoints import (
    admin,
    auth,
    coral_image,
    password_reset,
    user,
    website_content,
)

api_router = APIRouter()
api_router.include_router(admin.router, prefix="/super-admin", tags=["Admin"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(
    coral_image.router, prefix="/coral-image", tags=["Coral Image"]
)
api_router.include_router(password_reset.router, prefix="/password", tags=["Password"])
api_router.include_router(user.router, prefix="/u", tags=["Users"])
api_router.include_router(
    website_content.router, prefix="/admin/website-content", tags=["Website Content"]
)
