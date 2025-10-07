import logging
import time

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.router import api_router
from app.core.auth import get_current_user
from app.core.config import settings
from app.schemas.user import UserOut

logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000", "https://smart-coral-diagnostics.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET)

app.include_router(api_router, prefix="/api/v1")


@app.middleware("http")
async def middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.get("/")
async def root():
    return {"message": "Welcome to the API"}


@app.get("/api/v1/me")
async def get_me(request: Request, current_user: UserOut = Depends(get_current_user)):
    try:
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Cookies: {dict(request.cookies)}")

        return {
            "id": current_user.id,
            "email": current_user.email,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "name": f"{current_user.first_name} {current_user.last_name}",
            "is_verified": current_user.is_verified,
            "role": current_user.role,
            "provider": current_user.provider,
            "profile": current_user.profile,
        }
    except Exception as e:
        logger.error(f"error accesing /me: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="unauthorized access to resource",
        )
