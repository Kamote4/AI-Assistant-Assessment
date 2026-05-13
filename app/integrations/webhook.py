import hashlib
import hmac
import json
import threading

import requests

from config import config
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def push_result(result: dict, raw_enquiry: str) -> None:
    """
    Fire-and-forget POST of the analysis result to WEBHOOK_URL.

    Runs in a background thread so the main API response is never delayed.
    Does nothing if WEBHOOK_URL is not configured.
    """
    if not config.WEBHOOK_URL:
        return

    payload = {
        "event": "enquiry.analysed",
        "classification":      result.get("classification"),
        "classifications":     result.get("classifications", []),
        "confidence":          result.get("confidence"),
        "urgency":             result.get("urgency"),
        "needs_human_review":  result.get("needs_human_review"),
        "summary":             result.get("summary"),
        "recommended_action":  result.get("recommended_action"),
        "suggested_response":  result.get("suggested_response"),
        "reason":              result.get("reason"),
        "category_scores":     result.get("category_scores", {}),
        "processing_time_ms":  result.get("processing_time_ms"),
    }

    thread = threading.Thread(target=_send, args=(payload,), daemon=True)
    thread.start()


def _send(payload: dict) -> None:
    body = json.dumps(payload, default=str)
    headers = {"Content-Type": "application/json"}

    if config.WEBHOOK_SECRET:
        sig = hmac.new(
            config.WEBHOOK_SECRET.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()
        headers["X-Webhook-Signature"] = f"sha256={sig}"

    try:
        response = requests.post(
            config.WEBHOOK_URL,
            data=body,
            headers=headers,
            timeout=config.WEBHOOK_TIMEOUT,
        )
        logger.info(
            f"Webhook delivered | url={config.WEBHOOK_URL} | "
            f"status={response.status_code}"
        )
    except requests.exceptions.Timeout:
        logger.warning(f"Webhook timed out after {config.WEBHOOK_TIMEOUT}s")
    except requests.exceptions.ConnectionError as exc:
        logger.warning(f"Webhook delivery failed (connection error): {exc}")
    except Exception as exc:
        logger.warning(f"Webhook delivery failed: {exc}")
