import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "development-key-only")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///stocksense.db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    