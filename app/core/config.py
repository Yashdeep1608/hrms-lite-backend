# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str

    # AWS
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_S3_BUCKET_NAME: str
    AWS_S3_REGION: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    
    # Database config
    POSTGRES_USER:str
    POSTGRES_PASSWORD:str
    POSTGRES_DB:str

    RAZORPAY_KEY_ID: str
    RAZORPAY_KEY_SECRET: str
    
    ADMIN_BYPASS_OTP:str
    
    GUPSHUP_API_KEY:str
    GUPSHUP_SOURCE_NUMBER:str
    GUPSHUP_APP_NAME   :str
    GUPSHUP_OTP_TEMPLATE:str

    class Config:
        env_file = ".env"

settings = Settings()
