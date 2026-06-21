# app/services.py
from asyncpg.exceptions import UniqueViolationError
from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any

import models
import schemas


async def add_advertisement(
        session: AsyncSession,
        orm_model: type[models.Advertisement],
        item_data: schemas.CreateAdvertisementRequest,
        user_id: int
) -> models.Advertisement:

    # Создаем объявление с привязкой к пользователю
    new_item = orm_model(
        **item_data.model_dump(),
        user_id=user_id
    )
    session.add(new_item)
    try:
        await session.commit()
        await session.refresh(new_item)
        return new_item
    except IntegrityError as e:
        await session.rollback()
        if isinstance(e.orig, UniqueViolationError) and e.orig.pgcode == '23505':
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Advertisement with such data already exists."
            )
        else:
            raise e


async def get_advertisement(
        session: AsyncSession,
        orm_model: type[models.Advertisement],
        item_id: int
) -> models.Advertisement:
    stmt = select(orm_model).where(orm_model.id == item_id)
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Advertisement with id {item_id} not found"
        )
    return item


async def update_advertisement(
        session: AsyncSession,
        orm_model: type[models.Advertisement],
        item_id: int,
        update_data: schemas.UpdateAdvertisementRequest,
        current_user: models.User
) -> models.Advertisement:
    item = await get_advertisement(session, orm_model, item_id)

    # Проверка прав: админ может обновлять любые объявления,
    if current_user.group != models.UserGroup.ADMIN and item.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own advertisements"
        )

    # Преобразуем update_data в словарь, исключая поля со значением None
    update_dict = update_data.model_dump(exclude_unset=True)

    for key, value in update_dict.items():
        setattr(item, key, value)

    await session.commit()
    await session.refresh(item)
    return item


async def delete_advertisement(
        session: AsyncSession,
        orm_model: type[models.Advertisement],
        item_id: int,
        current_user: models.User
) -> None:
    item = await get_advertisement(session, orm_model, item_id)

    # Проверка прав: админ может удалять любые объявления,
    if current_user.group != models.UserGroup.ADMIN and item.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own advertisements"
        )

    await session.delete(item)
    await session.commit()


async def search_advertisements(
        session: AsyncSession,
        orm_model: type[models.Advertisement],
        filters: Dict[str, Any]
) -> list[models.Advertisement]:
    query = select(orm_model)

    filter_conditions = []

    # Поиск по заголовку (частичное совпадение)
    if "title" in filters and filters["title"]:
        filter_conditions.append(orm_model.title.ilike(f"%{filters['title']}%"))

    # Поиск по описанию (частичное совпадение)
    if "description" in filters and filters["description"]:
        filter_conditions.append(orm_model.description.ilike(f"%{filters['description']}%"))

    # Поиск по автору (частичное совпадение)
    if "author" in filters and filters["author"]:
        filter_conditions.append(orm_model.author.ilike(f"%{filters['author']}%"))

    # Поиск по минимальной цене
    if "price_min" in filters and filters["price_min"] is not None:
        filter_conditions.append(orm_model.price >= float(filters["price_min"]))

    # Поиск по максимальной цене
    if "price_max" in filters and filters["price_max"] is not None:
        filter_conditions.append(orm_model.price <= float(filters["price_max"]))

    if filter_conditions:
        query = query.where(and_(*filter_conditions))

    result = await session.execute(query)
    return result.scalars().all()