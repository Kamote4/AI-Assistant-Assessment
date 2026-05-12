from app.services.preprocessor import PreprocessingResult
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


def apply_review_rules(result: dict, preprocessing: PreprocessingResult) -> dict:
    """
    Enforce post-processing rules using both the AI result and preprocessing signals.
    Called from main.py step 6 after the model's response has been parsed.
    These rules can override the AI's own needs_human_review flag.
    """
    confidence = result.get("confidence", 0.0)

    # Low confidence always requires a human
    if confidence < 0.70:
        result["needs_human_review"] = True

    # Complaints are always reviewed regardless of confidence
    if result.get("classification") == "Complaint":
        result["needs_human_review"] = True

    # Risk signals detected in preprocessing → flag for review
    if preprocessing.risk_signals:
        result["needs_human_review"] = True

    # Potentially unclear input → flag for review.
    # Override classification only when the AI was also uncertain (confidence < 0.70)
    # so a confident AI result on borderline input is still respected.
    if preprocessing.is_potentially_unclear:
        result["needs_human_review"] = True
        if confidence < 0.70:
            result["classification"] = "Unknown / Needs Human Review"

    return result
