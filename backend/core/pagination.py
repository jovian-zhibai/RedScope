"""Pagination: reusable pagination for list endpoints."""

from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int


async def paginate(db: AsyncSession, query, page: int = 1, page_size: int = 20) -> dict:
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    paginated = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(paginated)
    items = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        "items": items,
    }
