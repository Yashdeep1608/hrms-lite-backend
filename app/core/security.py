from passlib.context import CryptContext # type: ignore
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError # type: ignore
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from app.db.session import get_db
from app.models import User
import os
from fastapi.security import OAuth2PasswordBearer

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("SECRET_KEY", "your-default-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 180))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="admin/login")

def get_username_password_hash(password: str) -> str:
    """Hash the password using bcrypt."""
    return pwd_context.hash(password)

def verify_username_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against the hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

