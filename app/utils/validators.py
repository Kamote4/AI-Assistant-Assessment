from config import config


def validate_enquiry(text: str) -> str | None:
    """
    Validate an incoming enquiry string.
    Returns an error message if invalid, or None if the input is acceptable.
    """
    if not text or not text.strip():
        return "Enquiry cannot be empty."

    stripped = text.strip()

    if len(stripped) < config.MIN_ENQUIRY_LENGTH:
        return (
            f"Enquiry is too short to analyse. "
            f"Please provide more detail (minimum {config.MIN_ENQUIRY_LENGTH} characters)."
        )

    if len(stripped) > config.MAX_ENQUIRY_LENGTH:
        return (
            f"Enquiry exceeds the maximum allowed length of "
            f"{config.MAX_ENQUIRY_LENGTH} characters."
        )

    return None
