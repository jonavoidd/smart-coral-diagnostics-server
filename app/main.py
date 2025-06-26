from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.connection import init_db
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("Database tables created successfully.")
    yield
    print("app shutdown.")


app = FastAPI(lifespan=lifespan)
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Welcome to the API"}
