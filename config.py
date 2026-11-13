import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-before-deployment")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///stocksense.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
