from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request
import os

API_KEY = os.environ.get("API_KEY")


class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in [
            "/docs",
            "/openapi.json",
        ]:  # Skip authentication for Swagger docs
            return await call_next(request)
        api_key = request.headers.get("API-Key")
        if api_key != API_KEY:
            return JSONResponse(
                status_code=403, content={"detail": "Could not validate credentials"}
            )
        return await call_next(request)
