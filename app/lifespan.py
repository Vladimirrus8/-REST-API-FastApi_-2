# app/lifespan.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from database import engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код ДО yield выполнится при старте приложения
    print("Starting up advertisement service...")
    async with engine.begin() as conn:
        # Создаём все таблицы
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Код ПОСЛЕ yield выполнится при остановке приложения
    print("Shutting down advertisement service...")
    await engine.dispose()