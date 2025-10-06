"""
Log Filtreleme Middleware
Sistem durumu isteklerini loglamayı atlar
"""

from fastapi import Request


async def log_filter_middleware(request: Request, call_next):
    """Sistem durumu isteklerini loglamayı atlar"""
    # Sistem durumu isteklerini loglamayı atla
    if request.url.path == "/api/sistem-durumu":
        # Sessizce işle
        response = await call_next(request)
        return response
    else:
        # Diğer istekleri normal logla
        response = await call_next(request)
        return response
