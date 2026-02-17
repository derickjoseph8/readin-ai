"""Pagination schemas and utilities."""

from typing import TypeVar, Generic, List, Optional, Any
from pydantic import BaseModel, Field
from math import ceil

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Common pagination parameters."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page (max 100)")
    sort_by: Optional[str] = Field(default=None, description="Field to sort by")
    sort_order: Optional[str] = Field(default="desc", description="Sort order (asc/desc)")

    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Return limit for database query."""
        return self.page_size


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    total_items: int = Field(description="Total number of items")
    total_pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_prev: bool = Field(description="Whether there is a previous page")
    next_page: Optional[int] = Field(default=None, description="Next page number")
    prev_page: Optional[int] = Field(default=None, description="Previous page number")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    items: List[Any] = Field(description="List of items for current page")
    meta: PaginationMeta = Field(description="Pagination metadata")

    class Config:
        arbitrary_types_allowed = True


def create_pagination_meta(
    page: int,
    page_size: int,
    total_items: int,
) -> PaginationMeta:
    """
    Create pagination metadata.

    Args:
        page: Current page number (1-indexed)
        page_size: Items per page
        total_items: Total count of items

    Returns:
        PaginationMeta object
    """
    total_pages = ceil(total_items / page_size) if page_size > 0 else 0
    has_next = page < total_pages
    has_prev = page > 1

    return PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev,
        next_page=page + 1 if has_next else None,
        prev_page=page - 1 if has_prev else None,
    )


def paginate(
    items: List[Any],
    page: int,
    page_size: int,
    total_items: int,
) -> PaginatedResponse:
    """
    Create a paginated response.

    Args:
        items: List of items for current page
        page: Current page number
        page_size: Items per page
        total_items: Total count of items

    Returns:
        PaginatedResponse with items and metadata
    """
    return PaginatedResponse(
        items=items,
        meta=create_pagination_meta(page, page_size, total_items),
    )


class CursorPaginationParams(BaseModel):
    """Cursor-based pagination parameters (for large datasets)."""

    cursor: Optional[str] = Field(default=None, description="Cursor for next page")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")
    direction: str = Field(default="next", description="Direction (next/prev)")


class CursorPaginationMeta(BaseModel):
    """Cursor pagination metadata."""

    has_more: bool = Field(description="Whether there are more items")
    next_cursor: Optional[str] = Field(default=None, description="Cursor for next page")
    prev_cursor: Optional[str] = Field(default=None, description="Cursor for previous page")
    count: int = Field(description="Number of items returned")


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """Cursor-based paginated response."""

    items: List[Any] = Field(description="List of items")
    meta: CursorPaginationMeta = Field(description="Cursor pagination metadata")

    class Config:
        arbitrary_types_allowed = True
