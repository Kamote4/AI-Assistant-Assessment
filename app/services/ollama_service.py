import requests
from config import config
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

_CHAT_ENDPOINT = "/api/chat"


class OllamaConnectionError(Exception):
    pass


class OllamaTimeoutError(Exception):
    pass


class OllamaModelError(Exception):
    pass


def call_ollama(system_prompt: str, user_message: str) -> str:
    """
    Send a chat request to Ollama and return the model's text response.
    Raises OllamaConnectionError, OllamaTimeoutError, or OllamaModelError on failure.
    """
    url = f"{config.OLLAMA_BASE_URL}{_CHAT_ENDPOINT}"
    payload = {
        "model": config.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "stream": False,
        "options": {"temperature": 0.4},
    }

    logger.info(f"Ollama request started | model={config.OLLAMA_MODEL}")

    try:
        response = requests.post(url, json=payload, timeout=config.OLLAMA_TIMEOUT)
        response.raise_for_status()

        content = response.json().get("message", {}).get("content", "")

        if not content:
            logger.warning("Ollama returned an empty content field")
            return ""

        logger.info("Ollama request completed successfully")
        return content

    except requests.exceptions.ConnectionError as exc:
        logger.error(f"Ollama connection failed: {exc}")
        raise OllamaConnectionError(
            "Could not connect to Ollama. Please ensure it is running."
        ) from exc

    except requests.exceptions.Timeout as exc:
        logger.error(f"Ollama request timed out after {config.OLLAMA_TIMEOUT}s")
        raise OllamaTimeoutError(
            f"Ollama did not respond within {config.OLLAMA_TIMEOUT} seconds."
        ) from exc

    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        logger.error(f"Ollama HTTP error: status={status}")
        if status == 404:
            raise OllamaModelError(
                f"Model '{config.OLLAMA_MODEL}' was not found. "
                f"Run: ollama pull {config.OLLAMA_MODEL}"
            ) from exc
        raise OllamaConnectionError(f"Ollama returned HTTP {status}.") from exc

    except Exception as exc:
        logger.error(f"Unexpected Ollama error: {exc}")
        raise
