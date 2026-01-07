from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class AppModeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        app_mode = request.headers.get("X-App-Mode", "private")

        if app_mode not in ("private", "public"):
            app_mode = "private"

        request.state.app_mode = app_mode
        response = await call_next(request)

        return response