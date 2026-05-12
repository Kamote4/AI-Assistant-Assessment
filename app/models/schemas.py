from dataclasses import dataclass
from typing import Optional

ALLOWED_CATEGORIES = [
    "New Client",
    "Support Request",
    "Complaint",
    "General Question",
    "Unknown / Needs Human Review",
]

ALLOWED_URGENCY_LEVELS = ["Low", "Medium", "High", "Unknown"]


@dataclass
class AnalysisResult:
    """
    Typed representation of a completed enquiry analysis.
    Used for documentation and IDE support.
    A production system could swap this for a Pydantic model for strict validation.
    """
    classification: str
    confidence: float
    urgency: str
    summary: str
    recommended_action: str
    suggested_response: str
    needs_human_review: bool
    reason: str
    processing_time_ms: Optional[int] = None
