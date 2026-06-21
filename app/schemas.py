# app/schemas.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
import re

from models import UserGroup


# Схемы для пользователей

class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100, description="Имя пользователя")
    password: str = Field(..., min_length=6, max_length=100, description="Пароль")
    group: UserGroup = Field(default=UserGroup.USER, description="Группа пользователя")

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username can only contain letters, numbers and underscore')
        return v


class CreateUserResponse(BaseModel):
    id: int
    username: str
    group: str
    created_at: Optional[str] = None


class GetUserResponse(BaseModel):
    id: int
    username: str
    group: str
    created_at: Optional[str] = None


class UpdateUserRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    password: Optional[str] = Field(None, min_length=6, max_length=100)
    group: Optional[UserGroup] = None

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not re.match(r'^[a-zA-Z0-9_]+$', v):
                raise ValueError('Username can only contain letters, numbers and underscore')
        return v


class LoginRequest(BaseModel):
    username: str = Field(..., description="Имя пользователя")
    password: str = Field(..., description="Пароль")


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    group: str


# Схемы для объявлений

class CreateAdvertisementRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Заголовок объявления")
    description: str = Field(..., min_length=1, max_length=1000, description="Описание объявления")
    price: float = Field(..., gt=0, description="Цена (должна быть больше 0)")
    author: str = Field(..., min_length=1, max_length=100, description="Автор объявления")


class CreateAdvertisementResponse(BaseModel):
    id: int
    user_id: int


class GetAdvertisementResponse(BaseModel):
    id: int
    title: str
    description: str
    price: float
    author: str
    user_id: int
    created_at: Optional[str] = None


class UpdateAdvertisementRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1, max_length=1000)
    price: Optional[float] = Field(None, gt=0)
    author: Optional[str] = Field(None, min_length=1, max_length=100)


class UpdateAdvertisementResponse(BaseModel):
    id: int
    title: str
    description: str
    price: float
    author: str
    user_id: int
    created_at: Optional[str] = None


class OKResponse(BaseModel):
    status: str = "ok"


class ErrorResponse(BaseModel):
    detail: str