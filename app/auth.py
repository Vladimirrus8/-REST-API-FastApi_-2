# app/auth.py
import jwt
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

import models
import schemas
from config import config

# Настройка хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Секретный ключ для JWT
SECRET_KEY = config.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 48


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def authenticate_user(
        session: AsyncSession,
        username: str,
        password: str
) -> Optional[models.User]:
    stmt = select(models.User).where(models.User.username == username)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


async def get_user_by_username(
        session: AsyncSession,
        username: str
) -> Optional[models.User]:
    stmt = select(models.User).where(models.User.username == username)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_id(
        session: AsyncSession,
        user_id: int
) -> Optional[models.User]:
    stmt = select(models.User).where(models.User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_user(
        session: AsyncSession,
        user_data: schemas.CreateUserRequest
) -> models.User:
    # Проверяем, не существует ли пользователь с таким именем
    existing_user = await get_user_by_username(session, user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with username '{user_data.username}' already exists"
        )

    # Хешируем пароль
    hashed_password = get_password_hash(user_data.password)

    # Создаем пользователя
    db_user = models.User(
        username=user_data.username,
        hashed_password=hashed_password,
        group=user_data.group
    )

    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)

    return db_user


async def update_user(
        session: AsyncSession,
        user_id: int,
        update_data: schemas.UpdateUserRequest,
        current_user: models.User
) -> models.User:
    user = await get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )

    # Проверяем права: пользователь может обновлять только себя,
    if current_user.group != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own profile"
        )

    # Обновляем поля
    update_dict = update_data.model_dump(exclude_unset=True)

    # Если обновляется пароль, хешируем его
    if "password" in update_dict:
        update_dict["hashed_password"] = get_password_hash(update_dict.pop("password"))

    for key, value in update_dict.items():
        setattr(user, key, value)

    await session.commit()
    await session.refresh(user)

    return user


async def delete_user(
        session: AsyncSession,
        user_id: int,
        current_user: models.User
) -> None:
    user = await get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )

    # Проверяем права: пользователь может удалять только себя,
    if current_user.group != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own profile"
        )

    await session.delete(user)
    await session.commit()