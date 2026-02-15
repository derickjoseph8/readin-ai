"""GZip compression middleware for API responses."""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware as StarletteGZipMiddleware
import gzip
import io
from typing import Callable


class GZipMiddleware(StarletteGZipMiddleware):
    """
    GZip compression middleware with configurable options.

    Compresses responses larger than minimum_size bytes when client
    accepts gzip encoding.
    """

    def __init__(
        self,
        app,
        minimum_size: int = 500,  # Only compress responses > 500 bytes
        compresslevel: int = 6,   # Compression level 1-9 (6 is default)
    ):
        super().__init__(app, minimum_size=minimum_size, compresslevel=compresslevel)


# For backward compatibility, also export as a function
def create_gzip_middleware(minimum_size: int = 500, compresslevel: int = 6):
    """
    Create a GZip middleware with custom settings.

    Args:
        minimum_size: Minimum response size in bytes to trigger compression
        compresslevel: Compression level (1=fastest, 9=smallest, 6=default)

    Usage:
        app.add_middleware(GZipMiddleware, minimum_size=500, compresslevel=6)
    """
    def middleware(app):
        return GZipMiddleware(app, minimum_size=minimum_size, compresslevel=compresslevel)
    return middleware
