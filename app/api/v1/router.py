from fastapi import APIRouter
from app.api.v1.endpoints import user, auth, supabase_storage, password_reset

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(user.router, prefix="/users", tags=["Users"])
api_router.include_router(password_reset.router, prefix="/password", tags=["Password"])
api_router.include_router(supabase_storage.router, prefix="/storage", tags=["Storage"])
