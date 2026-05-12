import json
import re
from app.models.schemas import ALLOWED_CATEGORIES
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

REQUIRED_FIELDS = [
    "classification",
    "confidence",
    "urgency",
    "summary",
    "recommended_action",
    "suggested_response",
    "needs_human_review",
    "reason",
]

FALLBACK_RESULT: dict = {
    "classification": "Unknown / Needs Human Review",
    "confidence": 0.0,
    "urgency": "Unknown",
    "summary": "The AI could not reliably analyse this enquiry.",
    "recommended_action": "A staff member should manually review the enquiry.",
    "suggested_response": (
        "Thank you for your message. A member of our team will review "
        "your enquiry and get back to you."
    ),
    "needs_human_review": True,
    "reason": "The AI response could not be parsed into the expected format.",
}


def parse_ai_response(raw_text: str) -> dict:
    """
    Parse the AI's raw output into a validated result dict.
    Tries multiple extraction strategies before falling back to a safe default.
    """
    if not raw_text or not raw_text.strip():
        logger.warning("Empty AI response — using fallback")
        return dict(FALLBACK_RESULT)

    parsed = _extract_json(raw_text)
    if parsed is None:
        logger.warning("All JSON extraction strategies failed — using fallback")
        return dict(FALLBACK_RESULT)

    validated = _validate_and_normalise(parsed)
    if validated is None:
        logger.warning("JSON validation failed — using fallback")
        return dict(FALLBACK_RESULT)

    logger.info("AI response parsed and validated successfully")
    return validated


def _extract_json(text: str) -> dict | None:
    """Try four strategies to pull a JSON object from the model output."""

    # Strategy 1: direct parse
    try:
        result = json.loads(text.strip())
        if isinstance(result, dict):
            logger.debug("JSON parsed directly")
            return result
    except json.JSONDecodeError:
        pass

    # Strategy 2: sanitise literal newlines inside string values and retry.
    # Some models embed real '\n' characters rather than the escaped sequence.
    sanitised = _sanitise_newlines(text.strip())
    if sanitised != text.strip():
        try:
            result = json.loads(sanitised)
            if isinstance(result, dict):
                logger.debug("JSON parsed after newline sanitisation")
                return result
        except json.JSONDecodeError:
            pass

    # Strategy 3: extract from markdown code fence (```json ... ``` or ``` ... ```)
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        try:
            result = json.loads(fence.group(1))
            if isinstance(result, dict):
                logger.debug("JSON extracted from markdown code fence")
                return result
        except json.JSONDecodeError:
            pass

    # Strategy 4: find the first { ... } block in mixed-text output
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        try:
            result = json.loads(brace.group(0))
            if isinstance(result, dict):
                logger.debug("JSON extracted from first brace block")
                return result
        except json.JSONDecodeError:
            pass

    logger.warning(f"Could not extract JSON. Response preview: {text[:200]!r}")
    return None


def _sanitise_newlines(text: str) -> str:
    """
    Replace literal newline characters inside JSON string values with \\n.
    Some local models embed real line breaks rather than the escape sequence,
    producing invalid JSON that json.loads() cannot handle directly.
    """
    result = []
    inside_string = False
    escape_next = False
    for ch in text:
        if escape_next:
            result.append(ch)
            escape_next = False
        elif ch == "\\" and inside_string:
            result.append(ch)
            escape_next = True
        elif ch == '"':
            inside_string = not inside_string
            result.append(ch)
        elif ch == "\n" and inside_string:
            result.append("\\n")
        elif ch == "\r" and inside_string:
            result.append("\\r")
        else:
            result.append(ch)
    return "".join(result)


def _validate_and_normalise(data: dict) -> dict | None:
    """Fill missing fields with fallback values and normalise types."""

    # Ensure every required field is present
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        logger.warning(f"AI response missing fields: {missing} — filling with defaults")
        for field in missing:
            data[field] = FALLBACK_RESULT[field]

    # Normalise confidence to a float in [0.0, 1.0]
    try:
        confidence = float(data["confidence"])
        data["confidence"] = round(max(0.0, min(1.0, confidence)), 2)
    except (ValueError, TypeError):
        logger.warning("Invalid confidence value — defaulting to 0.0")
        data["confidence"] = 0.0

    # Enforce allowed classification values
    if data["classification"] not in ALLOWED_CATEGORIES:
        logger.warning(f"Unknown classification '{data['classification']}' — defaulting")
        data["classification"] = "Unknown / Needs Human Review"

    # Ensure needs_human_review is a bool
    if not isinstance(data.get("needs_human_review"), bool):
        data["needs_human_review"] = bool(data.get("needs_human_review", True))

    # Ensure urgency is a non-empty string
    if not isinstance(data.get("urgency"), str) or not data["urgency"]:
        data["urgency"] = "Unknown"

    return data
