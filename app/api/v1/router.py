from fastapi import APIRouter
from app.api.v1.endpoints import (
    admin,
    archived_image,
    audit_trail,
    auth,
    coral_image,
    dev_test,
    password_reset,
    settings,
    trend,
    user,
    website_content,
)

api_router = APIRouter()

api_router.include_router(admin.router, prefix="/super-admin", tags=["Admin"])
api_router.include_router(
    archived_image.router, prefix="/archive", tags=["Archived Data"]
)
api_router.include_router(audit_trail.router, prefix="/audit", tags=["Audit Trails"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(
    coral_image.router, prefix="/coral-image", tags=["Coral Image"]
)
api_router.include_router(password_reset.router, prefix="/password", tags=["Password"])
api_router.include_router(user.router, prefix="/u", tags=["Users"])
api_router.include_router(settings.router, prefix="/settings", tags=["Settings"])
api_router.include_router(trend.router, prefix="/trends", tags=["Trends"])
api_router.include_router(
    website_content.router, prefix="/admin/website-content", tags=["Website Content"]
)
api_router.include_router(dev_test.router, prefix="/dev", tags=["Developer Routes"])
