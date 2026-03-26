from typing import Type, TypeVar, Generic, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends
from app.core.database import get_db

T = TypeVar('T')


class BaseService(Generic[T]):
    """Base service providing common CRUD operations."""
    
    def __init__(self, db: AsyncSession, model_class: Type[T]):
        self.db = db
        self.model_class = model_class
    
    async def get(self, id: str) -> Optional[T]:
        stmt = select(self.model_class).where(self.model_class.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create(self, **kwargs) -> T:
        obj = self.model_class(**kwargs)
        self.db.add(obj)
        await self.db.flush()
        return obj
    
    async def update(self, id: str, **kwargs) -> Optional[T]:
        obj = await self.get(id)
        if not obj:
            return None
        for key, value in kwargs.items():
            setattr(obj, key, value)
        await self.db.flush()
        return obj
    
    async def delete(self, id: str) -> bool:
        obj = await self.get(id)
        if not obj:
            return False
        await self.db.delete(obj)
        await self.db.flush()
        return True
    
    async def list(self, skip: int = 0, limit: int = 100):
        stmt = select(self.model_class).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()