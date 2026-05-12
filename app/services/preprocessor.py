import re
import spacy
from dataclasses import dataclass
from app.utils.validators import validate_enquiry
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Load once at startup. Parser and NER are not needed for lemmatisation.
_nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])

# Base lemma forms — spaCy maps every morphological variant back to these.
# "complained" / "complaining" → "complain", "damaged" / "damages" → "damage", etc.
# Add to this set when new risk concepts are identified; no prefix tricks needed.
RISK_KEYWORDS: set[str] = {
    # urgency
    "urgent", "emergency", "asap",
    # legal escalation
    "legal", "lawyer", "solicitor", "tribunal", "sue", "litigation",
    # complaints (noun and verb are different lemmas in English)
    "complain", "complaint",
    # safety
    "unsafe", "hazard",
    # physical damage / water
    "damage", "leak", "flood", "mould",
    # threats
    "threat", "threaten",
}


@dataclass
class PreprocessingResult:
    """Structured output of the preprocessing step."""
    clean_text: str
    metadata: dict
    risk_signals: list[str]
    is_potentially_unclear: bool
    validation_error: str | None = None


def preprocess_enquiry(raw_text: str) -> PreprocessingResult:
    """
    Validate, clean, and extract metadata from a raw client enquiry.

    If validation_error is set on the result, the request should be
    rejected before any AI call is made.

    Use clean_text for the AI prompt. Pass metadata and signals as
    context alongside the text.
    """
    # Delegate basic empty/length checks to the existing validator
    error = validate_enquiry(raw_text)
    if error:
        return PreprocessingResult(
            clean_text="",
            metadata=_empty_metadata(),
            risk_signals=[],
            is_potentially_unclear=False,
            validation_error=error,
        )

    clean = _clean_text(raw_text)
    metadata = _extract_metadata(clean)
    risk_signals = _detect_risk_signals(clean)
    is_unclear = _is_potentially_unclear(clean)

    logger.info(
        f"Preprocessing complete | "
        f"chars={metadata['character_count']} | "
        f"words={metadata['word_count']} | "
        f"risk_signals={risk_signals} | "
        f"unclear={is_unclear}"
    )

    return PreprocessingResult(
        clean_text=clean,
        metadata=metadata,
        risk_signals=risk_signals,
        is_potentially_unclear=is_unclear,
    )


# ── Text cleaning ────────────────────────────────────────────────────────────


def _clean_text(text: str) -> str:
    """
    Minimal, safe cleaning that normalises whitespace without altering content.
    Does not lowercase, remove punctuation, rewrite sentences, or strip names.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")          # normalise line endings
    text = text.strip()                                             # trim outer whitespace
    text = re.sub(r"[^\S\n]+", " ", text)                          # collapse spaces/tabs per line
    text = re.sub(r"\n{3,}", "\n\n", text)                         # max one blank line between paragraphs
    text = "\n".join(line.strip() for line in text.split("\n"))    # strip leading/trailing spaces per line
    return text


# ── Metadata extraction ──────────────────────────────────────────────────────


def _extract_metadata(text: str) -> dict:
    return {
        "character_count": len(text),
        "word_count": len(text.split()),
        "has_email": bool(
            re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
        ),
        "has_phone": bool(
            re.search(r"\+?\(?\d[\d\s\-().]{6,}\d", text)
        ),
        "has_question_mark": "?" in text,
    }


# ── Risk signal detection ────────────────────────────────────────────────────


def _detect_risk_signals(text: str) -> list[str]:
    """
    Lemmatise the text with spaCy, then intersect with RISK_KEYWORDS.
    spaCy maps every morphological variant to its base form before comparison,
    so "complained", "complaining", "complaints" all resolve to "complain",
    "damaged" / "damages" resolve to "damage", and so on — no manual prefix
    tricks required. Returns matched keywords in alphabetical order.
    """
    doc = _nlp(text)
    lemmas = {token.lemma_.lower() for token in doc if not token.is_space and not token.is_punct}
    return sorted(lemmas & RISK_KEYWORDS)


# ── Clarity heuristics ───────────────────────────────────────────────────────


def _is_potentially_unclear(text: str) -> bool:
    """
    Light heuristics for obviously vague or nonsensical messages.
    These are hints for the AI and post-processing rules, not hard classifications.
    The AI may still produce a confident result even when this returns True.
    """
    words = text.split()

    # Very few words after cleaning — almost certainly too vague to classify
    if len(words) < 4:
        return True

    # Symbol/number-heavy text with very little alphabetic content
    alpha = sum(1 for c in text if c.isalpha())
    if alpha / max(len(text), 1) < 0.5:
        return True

    # Highly repetitive word pattern (e.g. "help help help help help help")
    if len(words) >= 6:
        unique_ratio = len({w.lower() for w in words}) / len(words)
        if unique_ratio < 0.4:
            return True

    return False


# ── Helpers ──────────────────────────────────────────────────────────────────


def _empty_metadata() -> dict:
    return {
        "character_count": 0,
        "word_count": 0,
        "has_email": False,
        "has_phone": False,
        "has_question_mark": False,
    }
