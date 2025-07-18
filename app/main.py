from fastapi import FastAPI
from app.helpers.response import ResponseHandler
from app.helpers.translator import Translator
from app.helpers.utils import get_lang_from_request
from fastapi.middleware.cors import CORSMiddleware
from app.api.admin.v1 import auth, coupon, user, business, location, service, product, contact,payment,faq
from fastapi.openapi.utils import get_openapi
from fastapi.security import OAuth2PasswordBearer
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
# Use dependency-based authentication, not middleware!
# from app.middlewares.auth import AuthMiddleware  # REMOVE THIS LINE

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/v1/auth/login")
translator = Translator()

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Project API",
        version="1.0",
        description="API docs with JWT authentication",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    for path in openapi_schema["paths"].values():
        for operation in path.values():
            operation["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app = FastAPI(title="Project API", version="1.0")

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    lang = get_lang_from_request(request)
    if exc.status_code == 401:
        # You can customize the message or use localization here
        return ResponseHandler.unauthorized(message=translator.t("unauthorized",lang))
    return ResponseHandler.bad_request(
        message=translator.t("something_went_wrong",lang),
        data={"detail": exc.detail},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.openapi = custom_openapi

# REMOVE this line, as authentication is now handled by dependencies!
# app.add_middleware(AuthMiddleware)

# Include routers with dependency-based authentication
app.include_router(auth.router)
app.include_router(business.public_router)
app.include_router(business.router)
app.include_router(user.router)
app.include_router(location.router)
app.include_router(service.router)
app.include_router(product.router)
app.include_router(contact.router)
app.include_router(coupon.router)
app.include_router(payment.router)
app.include_router(faq.router)