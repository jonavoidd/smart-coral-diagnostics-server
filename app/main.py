from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
import time

from app.api.v1.router import api_router
from app.core.auth import get_current_user
from app.schemas.user import UserOut


app = FastAPI()
app.include_router(api_router, prefix="/api/v1")

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
async def get_me(current_user: UserOut = Depends(get_current_user)):
    return current_user
