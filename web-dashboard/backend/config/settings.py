from pydantic_settings import BaseSettings
from typing import List

class AppSettings(BaseSettings):
    app_name: str = "Business AI Web Dashboard Backend"
    admin_email: str = "admin@example.com"
    items_per_user: int = 50

    # Example: Database URL (would come from .env file in production)
    # database_url: str = "postgresql://user:password@localhost/dashboard_db"
    # redis_url: str = "redis://localhost:6379/0"

    # Example: JWT Settings
    jwt_secret_key: str = "your_very_secret_jwt_key_for_dashboard" # Change this!
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Example: CORS settings
    # frontend_url: str = "http://localhost:3000"
    # cors_allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    # Example: API Version Prefix
    # api_v1_prefix: str = "/api/v1"

    class Config:
        # For loading from .env file (requires python-dotenv to be installed)
        # env_file = ".env"
        # env_file_encoding = "utf-8"
        pass

# Instantiate settings for use in the application
# settings = AppSettings()
# print(f"Loaded settings: App Name - {settings.app_name}")
# The actual instantiation and usage would be in modules that need these settings,
# or settings could be passed around via dependency injection.
# For now, this defines the structure.
# The main.py file already has a commented out `from .config.settings import AppSettings`.
# I've updated the JWT secret key to be different from the one in auth_service.py for conceptual clarity,
# though in a real app, auth_service.py would import it from here.
# I'll update auth_service.py to reflect this.
