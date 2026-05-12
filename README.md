# Strata Enquiry AI Assistant

A production-minded AI-powered staff tool that helps a strata management consultancy process incoming client enquiries. The AI classifies enquiries, detects urgency, summarises the message, recommends a staff action, and drafts a professional reply — all for staff review before anything is sent.

---

## Business Problem

Strata Management Consultants receives a high volume of client enquiries via email and web forms. Staff must read each message, determine the nature of the request, decide who should handle it, and write a response. This is time-consuming and inconsistent, especially during peak periods.

## Solution Summary

This tool acts as a first-pass filter. Staff paste a client message into the web UI, click **Analyse**, and within seconds see:

- The classification and confidence score
- Urgency level
- A plain-English summary
- A recommended next action
- A draft reply they can edit and send

Enquiries that are vague, risky, legal, or angry are automatically flagged for manual review. The AI never sends anything — staff remain in full control.

---

## Features

- Classify enquiries into five categories
- Confidence score (0–100%)
- Urgency detection (Low / Medium / High)
- Enquiry summary
- Recommended staff action
- AI-drafted suggested response (editable)
- Human review flagging for risky or unclear messages
- Six sample enquiries for quick testing
- Health check endpoints (`/health` and `/health/ollama`)
- Structured JSON logging with privacy controls
- Safe fallback when the AI or Ollama is unavailable

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12+, Flask 3 |
| AI Provider | Ollama (local LLM) |
| Default Model | `gemma4:e2b` (configurable) |
| HTTP Client | requests |
| Config | python-dotenv |
| Frontend | Vanilla HTML, CSS, JavaScript |
| Logging | Python standard library `logging` |

## Why Ollama / Local LLM?

- **Privacy** — client enquiry text never leaves the local machine. No cloud API keys, no data sent to third-party services.
- **Cost** — no per-token charges. Suitable for high-volume or budget-constrained environments.
- **Control** — the model and its version are explicitly managed. No surprise capability changes from a cloud provider update.
- **Compliance** — easier to satisfy data residency requirements for sensitive client information.

---

## Folder Structure

```
.
├── app.py                    Entry point
├── config.py                 All configuration from environment variables
├── requirements.txt
├── .env.example              Template for environment variables
├── .gitignore
├── README.md
│
├── app/
│   ├── __init__.py           Flask app factory
│   ├── routes.py             Route handlers (/, /api/analyze, /health, /health/ollama)
│   │
│   ├── services/
│   │   ├── enquiry_analyzer.py   Orchestrates the analysis pipeline
│   │   ├── prompt_builder.py     Builds system + user prompts for Ollama
│   │   ├── ollama_service.py     Ollama API client with error handling
│   │   ├── health_service.py     Health check logic
│   │   └── rag_engine.py         Placeholder for future RAG implementation
│   │
│   ├── utils/
│   │   ├── logger.py             Logging setup (file + console, privacy-aware)
│   │   ├── validators.py         Input validation
│   │   ├── json_utils.py         AI response parsing with fallback strategies
│   │   └── response_helpers.py   Standardised JSON response formatting
│   │
│   ├── models/
│   │   └── schemas.py            AnalysisResult dataclass for type reference
│   │
│   ├── templates/
│   │   └── index.html            Staff UI
│   │
│   └── static/
│       ├── css/style.css
│       └── js/main.js
│
├── logs/                     Log files (created at runtime)
│   └── .gitkeep
│
└── docs/
    ├── PROMPT_DESIGN.md
    ├── SAMPLE_ENQUIRIES.md
    ├── LOGGING.md
    └── FUTURE_IMPROVEMENTS.md
```

---

## Setup Instructions

### Prerequisites

- Python 3.12 or later
- [Ollama](https://ollama.com) installed and running

### 1. Install and start Ollama

Download Ollama from https://ollama.com and follow the installation instructions for your platform.

Pull the default model:

```bash
ollama pull gemma4:e2b
```

Verify the model was pulled successfully:

```bash
ollama list
```

You should see `gemma4:e2b` in the output.

Ollama runs as a background service automatically after installation on most platforms. If it is not already running, start it in a separate terminal and leave it open:

```bash
ollama serve
```

> **Note:** `ollama run gemma4:e2b` opens an interactive chat session — that is useful for manual testing but is **not** what the app uses. The app calls Ollama's HTTP API directly, so you only need `ollama serve` running.

### 2. Clone / navigate to the project

```bash
cd /path/to/ai-assessment
```

### 3. Create and activate a virtual environment

```bash
python -m venv .venv
```

**Linux / macOS / WSL:**

```bash
source .venv/bin/activate
```

**Windows (PowerShell):**

```powershell
.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` if you need to change the Ollama URL, model, or logging settings. The defaults work for a standard local Ollama installation.

### 6. Run the app

```bash
python app.py
```

The app starts at **http://localhost:5000**.

---

## Testing the Health Endpoints

**App health:**

```bash
curl http://localhost:5000/health
```

Expected response:

```json
{"service": "Strata Enquiry AI Assistant", "status": "ok"}
```

**Ollama health:**

```bash
curl http://localhost:5000/health/ollama
```

Expected response (when Ollama is running and model is pulled):

```json
{
  "model": "gemma4:e2b",
  "model_available": true,
  "ollama_connected": true,
  "status": "ok"
}
```

---

## Example Enquiries

See [docs/SAMPLE_ENQUIRIES.md](docs/SAMPLE_ENQUIRIES.md) for six detailed examples with expected outputs. The UI also includes quick-fill sample buttons for all six categories.

---

## Expected API Output

`POST /api/analyze` with body `{"enquiry": "<text>"}` returns:

```json
{
  "status": "ok",
  "data": {
    "classification": "New Client",
    "confidence": 0.93,
    "urgency": "Low",
    "summary": "Committee member seeking information about professional strata management services for a 42-unit building.",
    "recommended_action": "Send a services and fees information pack and schedule an introductory call.",
    "suggested_response": "Thank you for reaching out to Strata Management Consultants. We would be delighted to discuss how we can assist with managing your building at...",
    "needs_human_review": false,
    "reason": "Clear new client enquiry with sufficient detail to classify confidently.",
    "processing_time_ms": 3241
  }
}
```

---

## Prompt Design

The prompt is split into a `system` message (persistent rules for the model) and a `user` message (the enquiry text). Key design choices:

- The model is told to return **only valid JSON** with no markdown or preamble, because local models can be verbose.
- The five classification categories are listed explicitly so the model cannot invent variations.
- Suggested responses are framed as **drafts**, and the model is instructed not to claim actions have been taken.
- Complaints, low-confidence results, and risky language always trigger `needs_human_review: true`.
- `json_utils.py` provides three fallback extraction strategies (direct parse → code fence extraction → first brace block) in case the model adds surrounding text.

See [docs/PROMPT_DESIGN.md](docs/PROMPT_DESIGN.md) for full detail.

---

## Logging

- Logs are written to the console and to `logs/app.log` (when `LOG_TO_FILE=True`).
- Each log line includes timestamp, level, module name, and a structured message.
- **Full enquiry text is never logged by default.** Only metadata is captured: length, classification, confidence, urgency, needs_human_review, processing time, and error type.
- Set `LOG_FULL_ENQUIRY=True` in `.env` for local debugging only. **Never enable this in production** — enquiry text may contain personal information.

See [docs/LOGGING.md](docs/LOGGING.md) for full detail.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Empty or whitespace-only input | 422 error with friendly message |
| Input too short (< 10 chars) | 422 error with guidance |
| Input too long (> 5000 chars) | 422 error |
| Ollama not running | Fallback result returned, `needs_human_review: true` |
| Ollama timeout | Fallback result returned, reason explains the timeout |
| Model not pulled | Fallback result with "model not found" reason |
| AI returns invalid JSON | `json_utils.py` attempts three extraction strategies, then returns fallback |
| Any unexpected exception | Caught, logged, fallback returned — app never crashes |

---

## Privacy Notes

- **No cloud APIs used.** All AI processing is local via Ollama.
- **No enquiry data is stored.** Each analysis is stateless — nothing is written to a database.
- **Full enquiry text is not logged** unless `LOG_FULL_ENQUIRY=True` (disabled by default).
- No authentication is implemented in this prototype.

**For production deployment, add:**
- Staff authentication (SSO / LDAP)
- HTTPS via a reverse proxy (Nginx, Caddy)
- Role-based access control
- Audit logging if enquiry history is required (with appropriate data handling policies)
- Secure storage if enquiry archiving is needed

---

## Human Review Approach

The AI flags enquiries for human review when:

1. Confidence is below 0.70
2. The enquiry is vague, very short, or nonsensical
3. The message contains angry, threatening, or legal language
4. The enquiry is safety-related or reputationally sensitive
5. The classification is **Complaint** (always flagged, regardless of confidence)

When flagged, the UI displays a prominent warning banner. The suggested response is still generated but clearly marked as a draft requiring review.

This design means staff always make the final call. The AI is an accelerator, not an autonomous actor.

---

## Future Improvements

See [docs/FUTURE_IMPROVEMENTS.md](docs/FUTURE_IMPROVEMENTS.md) for a full list. Key items:

- RAG integration using company-specific documents (`rag_engine.py` is already a placeholder)
- Staff authentication and access control
- Persistent enquiry history with audit trail
- Email / web form integration for automatic enquiry ingestion
- Log rotation and production observability

---

## Assessment Alignment

| Requirement | Implementation |
|---|---|
| Five classification categories | `prompt_builder.py`, `json_utils.py` ALLOWED_CATEGORIES |
| Confidence score | Returned by model, normalised to 0.0–1.0 in `json_utils.py` |
| Urgency detection | Included in prompt and JSON output |
| Suggested response (draft) | Generated by model, editable in UI |
| Human review flagging | Business rules in `enquiry_analyzer.py`, UI banner |
| Health checks | `/health` and `/health/ollama` routes |
| Structured logging | `app/utils/logger.py`, privacy-aware |
| Fallback on AI failure | `json_utils.py` FALLBACK_RESULT, caught in `enquiry_analyzer.py` |
| Configurable model | `OLLAMA_MODEL` environment variable, never hardcoded |
| Local LLM (no cloud keys) | Ollama via `requests`, no external API calls |
| Separation of concerns | Services / utils / models / routes / config all separated |
| Clean README | This document |

---

## Assumptions

1. Ollama is run locally on the default port (11434). This is configurable via `OLLAMA_BASE_URL`.
2. The model `gemma4:e2b` refers to a model available in Ollama's registry under that exact name.
3. The app is run from the project root directory (`python app.py`).
4. Python 3.10+ is required for the `str | None` union type syntax used in type hints.
5. The `.venv` virtual environment directory is excluded from version control.
6. No database or persistent storage is needed for this prototype — each analysis is stateless.
7. Staff using the tool are trusted internal users. Authentication is out of scope for this assessment.
