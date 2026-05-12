from app.services.preprocessor import PreprocessingResult

SYSTEM_PROMPT = """You are an AI assistant helping staff at a strata management consulting company process incoming client enquiries.

Your task is to analyse each enquiry and return a structured JSON response.

Allowed classification categories (use ONLY these exact values):
- New Client
- Support Request
- Complaint
- General Question
- Unknown / Needs Human Review

Rules you must follow:
1. Return ONLY a single valid JSON object. Do not include markdown, code fences, commentary, or any text outside the JSON.
2. Do not invent or assume facts that are not present in the enquiry.
3. The suggested_response is a DRAFT for staff review only. Do not state that any action has already been taken.
4. If information is missing to respond fully, ask for it within the suggested_response.
5. Set needs_human_review to true when ANY of the following apply:
   - confidence is below 0.70
   - the message is vague, unclear, very short, or nonsensical
   - the message contains angry, threatening, or legal language
   - the enquiry is safety-related, urgent, or reputationally sensitive
   - the classification is Complaint
6. Classify vague or nonsensical messages as "Unknown / Needs Human Review".

Required JSON output format (no other text):
{
  "classification": "<one of the five allowed categories>",
  "confidence": <float between 0.0 and 1.0>,
  "urgency": "<Low | Medium | High | Unknown>",
  "summary": "<one-sentence summary of the enquiry>",
  "recommended_action": "<specific action the staff member should take next>",
  "suggested_response": "<professional draft reply for staff to review and edit before sending>",
  "needs_human_review": <true | false>,
  "reason": "<brief explanation of the classification and any review flags>"
}"""


def build_analysis_prompt(preprocessing: PreprocessingResult) -> tuple[str, str]:
    """
    Build (system_prompt, user_message) for the Ollama chat API.

    The user message contains the cleaned enquiry text followed by a short
    context block derived from preprocessing. This gives the model additional
    signals without rewriting or summarising the original message.
    """
    context_lines = [
        f"Word count: {preprocessing.metadata['word_count']}",
        f"Contains email: {'yes' if preprocessing.metadata['has_email'] else 'no'}",
        f"Contains phone number: {'yes' if preprocessing.metadata['has_phone'] else 'no'}",
        f"Contains question: {'yes' if preprocessing.metadata['has_question_mark'] else 'no'}",
    ]

    if preprocessing.risk_signals:
        context_lines.append(
            f"Risk signals detected: {', '.join(preprocessing.risk_signals)}"
        )

    if preprocessing.is_potentially_unclear:
        context_lines.append(
            "Note: automated checks suggest this message may be vague or unclear."
        )

    context = "\n".join(context_lines)

    user_message = (
        f"Please analyse the following client enquiry:\n\n"
        f"{preprocessing.clean_text}\n\n"
        f"--- Analysis context ---\n"
        f"{context}"
    )

    return SYSTEM_PROMPT, user_message
