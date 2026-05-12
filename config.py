import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Ollama
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gemma4:e2b")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "60"))

    # Flask
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-in-production")

    # Input validation
    MAX_ENQUIRY_LENGTH: int = int(os.getenv("MAX_ENQUIRY_LENGTH", "5000"))
    MIN_ENQUIRY_LENGTH: int = int(os.getenv("MIN_ENQUIRY_LENGTH", "10"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_TO_FILE: bool = os.getenv("LOG_TO_FILE", "True").lower() == "true"
    LOG_FULL_ENQUIRY: bool = os.getenv("LOG_FULL_ENQUIRY", "False").lower() == "true"
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")
    LOG_FILE: str = os.path.join(os.getenv("LOG_DIR", "logs"), "app.log")

    # App metadata
    APP_NAME: str = "Strata Enquiry AI Assistant"
    VERSION: str = "1.0.0"


config = Config()
