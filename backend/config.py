"""
Production Configuration Management
====================================
Centralized configuration for Pulse of Bharat application
"""

import os
from pathlib import Path
from typing import Optional
try:
    from pydantic_settings import BaseSettings
    from pydantic import validator
except ImportError:
    from pydantic import BaseSettings, validator
import logging


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application Settings
    APP_NAME: str = "Pulse of Bharat - Governance Intelligence API"
    APP_VERSION: str = "2.0.0"
    MODEL_VERSION: str = "DEMOG_COHORT_v2.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")  # development, staging, production
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Server Settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    RELOAD: bool = os.getenv("RELOAD", "True").lower() == "true"
    WORKERS: int = int(os.getenv("WORKERS", "4"))
    
    # CORS Settings
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["*"]
    CORS_ALLOW_HEADERS: list = ["*"]
    
    # Security Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGE_THIS_IN_PRODUCTION_8a7d9b6c5e4f3a2b1c0d9e8f7a6b5c4d")
    API_KEY_ENABLED: bool = os.getenv("API_KEY_ENABLED", "False").lower() == "true"
    API_KEY: Optional[str] = os.getenv("API_KEY", None)
    ALLOWED_IPS: list = os.getenv("ALLOWED_IPS", "").split(",") if os.getenv("ALLOWED_IPS") else []
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true"
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds
    
    # Data Settings
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "chunked_data"
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "True").lower() == "true"
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))  # seconds
    
    # ML Settings
    ML_ENABLED: bool = os.getenv("ML_ENABLED", "True").lower() == "true"
    ANOMALY_CONTAMINATION: float = float(os.getenv("ANOMALY_CONTAMINATION", "0.1"))
    CLUSTERING_ENABLED: bool = os.getenv("CLUSTERING_ENABLED", "True").lower() == "true"
    N_CLUSTERS: int = int(os.getenv("N_CLUSTERS", "8"))
    
    # Forecasting Settings
    FORECAST_ENABLED: bool = os.getenv("FORECAST_ENABLED", "True").lower() == "true"
    FORECAST_HORIZONS: list = [1, 5, 10]  # years
    
    # Logging Settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[Path] = Path(os.getenv("LOG_FILE", "logs/app.log")) if os.getenv("LOG_FILE") else None
    LOG_ROTATION: str = os.getenv("LOG_ROTATION", "10 MB")
    LOG_RETENTION: str = os.getenv("LOG_RETENTION", "10 days")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Database Settings (for future use)
    DATABASE_ENABLED: bool = os.getenv("DATABASE_ENABLED", "False").lower() == "true"
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL", None)
    
    # Redis Cache (for future use)
    REDIS_ENABLED: bool = os.getenv("REDIS_ENABLED", "False").lower() == "true"
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    # Monitoring & Observability
    MONITORING_ENABLED: bool = os.getenv("MONITORING_ENABLED", "True").lower() == "true"
    METRICS_PORT: int = int(os.getenv("METRICS_PORT", "9090"))
    HEALTH_CHECK_ENABLED: bool = True
    
    # Chatbot Settings
    CHATBOT_ENABLED: bool = os.getenv("CHATBOT_ENABLED", "True").lower() == "true"
    CHATBOT_MAX_TOKENS: int = int(os.getenv("CHATBOT_MAX_TOKENS", "1000"))
    CHATBOT_TEMPERATURE: float = float(os.getenv("CHATBOT_TEMPERATURE", "0.7"))
    
    # Export Settings
    EXPORT_ENABLED: bool = os.getenv("EXPORT_ENABLED", "True").lower() == "true"
    MAX_EXPORT_ROWS: int = int(os.getenv("MAX_EXPORT_ROWS", "100000"))
    
    # WebSocket Settings
    WEBSOCKET_ENABLED: bool = os.getenv("WEBSOCKET_ENABLED", "True").lower() == "true"
    WEBSOCKET_ALERT_INTERVAL: int = int(os.getenv("WEBSOCKET_ALERT_INTERVAL", "30"))  # seconds
    
    # Performance Settings
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "4"))
    TIMEOUT: int = int(os.getenv("TIMEOUT", "60"))  # seconds
    KEEP_ALIVE: int = int(os.getenv("KEEP_ALIVE", "5"))  # seconds
    
    # Data Validation
    VALIDATE_PINCODES: bool = os.getenv("VALIDATE_PINCODES", "True").lower() == "true"
    MIN_PINCODE: int = 100000
    MAX_PINCODE: int = 999999
    
    # Thresholds
    RISK_THRESHOLD_CRITICAL: int = int(os.getenv("RISK_THRESHOLD_CRITICAL", "70"))
    RISK_THRESHOLD_HIGH: int = int(os.getenv("RISK_THRESHOLD_HIGH", "50"))
    RISK_THRESHOLD_MEDIUM: int = int(os.getenv("RISK_THRESHOLD_MEDIUM", "30"))
    SECTOR_ALERT_THRESHOLD: int = int(os.getenv("SECTOR_ALERT_THRESHOLD", "50"))
    
    @validator("LOG_FILE", pre=True)
    def create_log_directory(cls, v):
        if v:
            log_path = Path(v)
            log_path.parent.mkdir(parents=True, exist_ok=True)
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Initialize settings
settings = Settings()


# Configure logging based on settings
def setup_logging():
    """Configure application logging"""
    log_handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
    console_handler.setFormatter(logging.Formatter(settings.LOG_FORMAT))
    log_handlers.append(console_handler)
    
    # File handler (if enabled)
    if settings.LOG_FILE:
        try:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                settings.LOG_FILE,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
            file_handler.setFormatter(logging.Formatter(settings.LOG_FORMAT))
            log_handlers.append(file_handler)
        except Exception as e:
            logging.warning(f"Could not setup file logging: {e}")
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format=settings.LOG_FORMAT,
        handlers=log_handlers
    )
    
    # Suppress noisy loggers in production
    if settings.ENVIRONMENT == "production":
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.error").setLevel(logging.ERROR)


# Risk level classification helper
def get_risk_level(score: float) -> str:
    """Get risk level based on score"""
    if score >= settings.RISK_THRESHOLD_CRITICAL:
        return "CRITICAL"
    elif score >= settings.RISK_THRESHOLD_HIGH:
        return "HIGH"
    elif score >= settings.RISK_THRESHOLD_MEDIUM:
        return "MEDIUM"
    else:
        return "LOW"


# Validate pincode helper
def is_valid_pincode(pincode: int) -> bool:
    """Validate Indian pincode format"""
    if not settings.VALIDATE_PINCODES:
        return True
    return settings.MIN_PINCODE <= pincode <= settings.MAX_PINCODE
