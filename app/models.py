# app/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, func, ForeignKey, Enum
from sqlalchemy.orm import relationship
from database import Base
import enum


class UserGroup(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    group = Column(Enum(UserGroup), default=UserGroup.USER, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Связь с объявлениями
    advertisements = relationship("Advertisement", back_populates="user")

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "group": self.group.value if self.group else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Advertisement(Base):
    __tablename__ = "advertisements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String(1000), nullable=False)
    price = Column(Float, nullable=False)
    author = Column(String(100), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Связь с пользователем
    user = relationship("User", back_populates="advertisements")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "price": self.price,
            "author": self.author,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }