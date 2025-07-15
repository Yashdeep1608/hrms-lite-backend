from fastapi.responses import JSONResponse
from typing import Any, Dict
from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeMeta
import json
def safe_serialize(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    elif isinstance(obj.__class__, DeclarativeMeta):  # SQLAlchemy model
        return {col.name: getattr(obj, col.name) for col in obj.__table__.columns}
    elif isinstance(obj, (dict, list, str, int, float, bool)) or obj is None:
        return obj
    else:
        try:
            return json.loads(json.dumps(obj, default=str))  # fallback
        except Exception:
            return str(obj)  # final fallback
class ResponseHandler:
    @staticmethod
    def success(
        data: Any = None,
        message: str = "Success",
        code: int = 200
    ) -> JSONResponse:
        return JSONResponse(
            status_code=code,
            content={
                "status": "success",
                "code": code,
                "message": message,
                "data": safe_serialize(data),
            },
        )

    @staticmethod
    def bad_request(
        message: str = "Bad Request",
        error: Any = {},
        data: Any = None,
        code: int = 400,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=code,
            content={
                "status": "error",
                "code": code,
                "message": message,
                "data": safe_serialize(data),
                "error": safe_serialize(error),
            },
        )

    @staticmethod
    def unauthorized(
        message: str = "Unauthorized",
        error: Any = {},
        data: Any = None,
        code: int = 401,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=code,
            content={
                "status": "error",
                "code": code,
                "message": message,
                "data": safe_serialize(data),
                "error": safe_serialize(error),
            },
        )

    @staticmethod
    def not_found(
        message: str = "Not Found",
        error: Any = {},
        data: Any = None,
        code: int = 404,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=code,
            content={
                "status": "error",
                "code": code,
                "message": message,
                "data": safe_serialize(data),
                "error": safe_serialize(error),
            },
        )

    @staticmethod
    def internal_error(
        message: str = "Internal Server Error",
        error: Any = {},
        data: Any = None,
        code: int = 500,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=code,
            content={
                "status": "error",
                "code": code,
                "message": message,
                "data": safe_serialize(data),
                "error": safe_serialize(error),
            },
        )
