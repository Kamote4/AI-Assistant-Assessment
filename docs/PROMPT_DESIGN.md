# Prompt Design

## Overview

The prompt is built in `app/services/prompt_builder.py` and split into two parts:

| Part | Role | Content |
|---|---|---|
| `system_prompt` | Instructions to the model | Classification rules, output format, behaviour constraints |
| `user_message` | The input to analyse | The staff-supplied client enquiry text |

This maps directly to Ollama's `/api/chat` message format (`system` + `user` roles), which encourages the model to treat the system content as persistent rules rather than data to analyse.

---

## Design goals

### 1. Force structured output
The prompt explicitly tells the model to return only a valid JSON object with no markdown, preamble, or commentary. This is critical when using local models that tend to be more verbose than cloud models.

The `json_utils.py` module provides a fallback extraction layer if the model wraps the JSON in code fences or adds surrounding text anyway.

### 2. Use a fixed category list
The prompt names the five allowed classifications and instructs the model to use them exactly. This prevents the model from inventing variations like "Complaint / Legal" or "New Enquiry".

### 3. Draft responses, not sent ones
The prompt explicitly states:
> "The suggested_response is a DRAFT for staff review only. Do not state that any action has already been taken."

This ensures the AI does not write things like "I have passed your enquiry to our team" — which would be a false promise. Instead it writes "A member of our team will be in touch shortly."

### 4. Ask for missing information
When an enquiry lacks enough detail to respond fully, the suggested response should ask clarifying questions rather than guessing or refusing to generate a reply.

### 5. Conservative review flagging
The prompt sets `needs_human_review = true` for:
- Low confidence (below 0.70)
- Vague or nonsensical input
- Angry, threatening, or legal language
- Safety-related or urgent content
- All complaints (even confident ones)

This aligns with the business goal: the AI helps staff work faster, but staff remain accountable.

---

## Confidence calibration

The model is asked to return a confidence value between 0.0 and 1.0. In practice:
- **0.90+** — clear, unambiguous enquiry
- **0.70–0.89** — reasonable confidence, staff review optional
- **Below 0.70** — `needs_human_review` is forced to `true`
- **0.0** — used when the fallback result is returned (parsing failure)

---

## Known limitations

- Small local models (like `gemma4:e2b`) may produce confidence scores inconsistently.
- The model cannot access strata legislation or company-specific policies — all responses are general. RAG (see `rag_engine.py`) would address this in production.
- Very long enquiries that approach the model's context limit may produce lower-quality outputs.
