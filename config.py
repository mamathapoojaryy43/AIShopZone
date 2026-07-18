"""Application configuration.

Settings are read from environment variables (see .env.example) with
sensible local defaults so the project runs out of the box.
"""
import os
from datetime import timedelta

from dotenv import load_dotenv

# Load variables from a local .env file (if present) into the environment
# so configuration below can read them. Values already set in the real
# environment take precedence over the .env file.
load_dotenv()


class Config:
    """Base configuration shared by all environments."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://root:password@localhost/aishopzone",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # The single admin account (email match). Override via env for real use.
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@aishopzone.com")

    # ----- Localization (India) -----
    CURRENCY_SYMBOL = "₹"
    CURRENCY_CODE = "INR"
    COUNTRY = "India"
    PHONE_PREFIX = "+91"

    AI_PROVIDER = os.environ.get("AI_PROVIDER", "openai")  # or "claude"
    AI_API_KEY = os.environ.get("AI_API_KEY", "")
    AI_MODEL = os.environ.get("AI_MODEL", "gpt-4o-mini")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
