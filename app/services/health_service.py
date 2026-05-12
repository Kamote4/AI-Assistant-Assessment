import requests
from config import config
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def check_app_health() -> dict:
    """Return basic application health status."""
    logger.debug("App health check requested")
    return {
        "status": "ok",
        "service": config.APP_NAME,
        "version": config.VERSION,
    }


def check_ollama_health() -> dict:
    """
    Check Ollama connectivity and whether the configured model is available.
    Uses the /api/tags endpoint to list pulled models.
    """
    logger.info("Ollama health check requested")

    result = {
        "status": "ok",
        "ollama_connected": False,
        "model": config.OLLAMA_MODEL,
        "model_available": False,
    }

    try:
        response = requests.get(
            f"{config.OLLAMA_BASE_URL}/api/tags",
            timeout=5,
        )
        response.raise_for_status()
        result["ollama_connected"] = True

        models = response.json().get("models", [])
        pulled_names = [m.get("name", "") for m in models]
        model_available = any(
            config.OLLAMA_MODEL == name or name.startswith(config.OLLAMA_MODEL)
            for name in pulled_names
        )
        result["model_available"] = model_available

        if not model_available:
            result["status"] = "warning"
            result["message"] = (
                f"Model '{config.OLLAMA_MODEL}' is not available. "
                f"Run: ollama pull {config.OLLAMA_MODEL}"
            )

        logger.info(
            f"Ollama health check | connected=True | model_available={model_available}"
        )

    except requests.exceptions.ConnectionError:
        result["status"] = "error"
        result["error"] = "Cannot connect to Ollama. Make sure it is running."
        logger.warning("Ollama health check failed: connection refused")

    except requests.exceptions.Timeout:
        result["status"] = "error"
        result["error"] = "Ollama did not respond within the timeout period."
        logger.warning("Ollama health check timed out")

    except Exception as exc:
        result["status"] = "error"
        result["error"] = f"Unexpected error: {exc}"
        logger.error(f"Ollama health check unexpected error: {exc}")

    return result
