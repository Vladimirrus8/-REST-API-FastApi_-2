# app/app.py
from typing import Annotated, Optional
from fastapi import FastAPI, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware

import models
import schemas
import auth
from dependencies import (
    get_db_session,
    get_current_user,
    get_current_active_user,
    get_current_admin_user
)
from lifespan import lifespan
from services import (
    add_advertisement,
    get_advertisement,
    update_advertisement,
    delete_advertisement,
    search_advertisements
)
from config import config

app = FastAPI(
    title="Сервис объявлений",
    description="Сервис объявлений купли/продажи с авторизацией и системой ролей",
    version="2.0.0",
    lifespan=lifespan
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Создаём тип для зависимости сессии
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


# Аутентификация

@app.post("/login", response_model=schemas.LoginResponse, summary="Вход в систему")
async def login(
    login_data: schemas.LoginRequest,
    session: SessionDep
):
    """
    Авторизация пользователя и получение JWT токена
    """
    user = await auth.authenticate_user(session, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Создаем токен
    access_token = auth.create_access_token(
        data={"sub": user.id, "username": user.username, "group": user.group.value}
    )

    return schemas.LoginResponse(
        access_token=access_token,
        user_id=user.id,
        username=user.username,
        group=user.group.value
    )


# Пользователи

@app.post("/user", response_model=schemas.CreateUserResponse, summary="Создать пользователя", status_code=201)
async def create_user(
    user_data: schemas.CreateUserRequest,
    session: SessionDep
):
    new_user = await auth.create_user(session, user_data)
    return schemas.CreateUserResponse(**new_user.to_dict())


@app.get("/user/{user_id}", response_model=schemas.GetUserResponse, summary="Получить пользователя по ID")
async def get_user_by_id(
    user_id: int,
    session: SessionDep,
    current_user: Optional[models.User] = Depends(get_current_user)
):
    user = await auth.get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с ID {user_id} не найден"
        )
    return schemas.GetUserResponse(**user.to_dict())


@app.patch("/user/{user_id}", response_model=schemas.GetUserResponse, summary="Обновить пользователя")
async def update_user_by_id(
    user_id: int,
    update_data: schemas.UpdateUserRequest,
    session: SessionDep,
    current_user: models.User = Depends(get_current_active_user)
):
    updated_user = await auth.update_user(session, user_id, update_data, current_user)
    return schemas.GetUserResponse(**updated_user.to_dict())


@app.delete("/user/{user_id}", response_model=schemas.OKResponse, summary="Удалить пользователя")
async def delete_user_by_id(
    user_id: int,
    session: SessionDep,
    current_user: models.User = Depends(get_current_active_user)
):
    await auth.delete_user(session, user_id, current_user)
    return schemas.OKResponse()


# Объявления

@app.post("/advertisement", response_model=schemas.CreateAdvertisementResponse, summary="Создать объявление", status_code=201)
async def create_advertisement(
    ad_data: schemas.CreateAdvertisementRequest,
    session: SessionDep,
    current_user: models.User = Depends(get_current_active_user)
):
    new_ad = await add_advertisement(session, models.Advertisement, ad_data, current_user.id)
    return schemas.CreateAdvertisementResponse(id=new_ad.id, user_id=new_ad.user_id)


@app.get("/advertisement/{advertisement_id}", response_model=schemas.GetAdvertisementResponse, summary="Получить объявление по ID")
async def get_advertisement_by_id(
    advertisement_id: int,
    session: SessionDep
):
    ad = await get_advertisement(session, models.Advertisement, advertisement_id)
    return schemas.GetAdvertisementResponse(**ad.to_dict())


@app.patch("/advertisement/{advertisement_id}", response_model=schemas.UpdateAdvertisementResponse, summary="Обновить объявление")
async def update_advertisement_by_id(
    advertisement_id: int,
    update_data: schemas.UpdateAdvertisementRequest,
    session: SessionDep,
    current_user: models.User = Depends(get_current_active_user)
):
    updated_ad = await update_advertisement(
        session,
        models.Advertisement,
        advertisement_id,
        update_data,
        current_user
    )
    return schemas.UpdateAdvertisementResponse(**updated_ad.to_dict())


@app.delete("/advertisement/{advertisement_id}", response_model=schemas.OKResponse, summary="Удалить объявление")
async def delete_advertisement_by_id(
    advertisement_id: int,
    session: SessionDep,
    current_user: models.User = Depends(get_current_active_user)
):
    await delete_advertisement(session, models.Advertisement, advertisement_id, current_user)
    return schemas.OKResponse()


@app.get("/advertisement", response_model=list[schemas.GetAdvertisementResponse], summary="Поиск объявлений")
async def search_advertisements_by_fields(
    session: SessionDep,
    title: Optional[str] = Query(None, description="Поиск по заголовку (частичное совпадение)"),
    description: Optional[str] = Query(None, description="Поиск по описанию (частичное совпадение)"),
    price_min: Optional[float] = Query(None, description="Минимальная цена", gt=0),
    price_max: Optional[float] = Query(None, description="Максимальная цена", gt=0),
    author: Optional[str] = Query(None, description="Поиск по автору (частичное совпадение)")
):
    filters = {}
    if title:
        filters["title"] = title
    if description:
        filters["description"] = description
    if price_min is not None:
        filters["price_min"] = price_min
    if price_max is not None:
        filters["price_max"] = price_max
    if author:
        filters["author"] = author

    ads = await search_advertisements(session, models.Advertisement, filters)
    return [schemas.GetAdvertisementResponse(**ad.to_dict()) for ad in ads]