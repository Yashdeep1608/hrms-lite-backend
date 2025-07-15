# app/middlewares/auth.py

from fastapi import Request
from fastapi.responses import JSONResponse # type: ignore
from starlette.middleware.base import BaseHTTPMiddleware # type: ignore
from jose import jwt, JWTError
from app.db.session import SessionLocal, get_db
from app.crud.user import get_user_by_id
from sqlalchemy.orm import Session

from app.helpers.response import ResponseHandler
from app.helpers.translator import Translator
import os



SECRET_KEY = os.getenv("SECRET_KEY", "your-default-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 180))

EXCLUDE_PATHS = [
    "/docs",               # Swagger UI
    "/openapi.json",       # OpenAPI schema
    "/redoc",               # ReDoc UI,
    "/api/admin/v1/auth",  # Auth APIs
    "/api/admin/v1/location",  # Locations APIs
    "/api/admin/v1/business",
    # "/api/admin/v1/contact"
]
translator = Translator()

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        lang = request.headers.get("Accept-Language", "en")

        # Allow CORS preflight
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip authentication for excluded paths
        if any(request.url.path.startswith(path_exclude) for path_exclude in EXCLUDE_PATHS):
            return await call_next(request)

        # Allow public GETs (optional logic)
        if request.method == "GET" and request.url.path.startswith("/public"):
            return await call_next(request)

        # Check for Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return ResponseHandler.unauthorized(
                message=translator.t("unauthorized", lang)
            )

        token = auth_header.split(" ")[1]
        try:
            # Decode JWT token
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            if not user_id:
                return ResponseHandler.unauthorized(
                    message=translator.t("invalid_token_payload", lang)
                )

            # Use context manager for DB session (prevents leaks)
            with SessionLocal() as db:
                user = get_user_by_id(db, int(user_id))
                if not user:
                    return ResponseHandler.unauthorized(
                        message=translator.t("user_not_found", lang)
                    )
                if not user.is_active or user.is_deleted:
                    return ResponseHandler.unauthorized(
                        message=translator.t("user_inactive_or_deleted", lang)
                    )
                # Attach user to request state for downstream access
                request.state.user = user

        except JWTError:
            return ResponseHandler.unauthorized(message=translator.t("invalid_token", lang))
        except Exception as e:
            return ResponseHandler.unauthorized(error=str(e))

        # All checks passed, continue request
        return await call_next(request)