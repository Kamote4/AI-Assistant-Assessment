# Strata Enquiry AI Assistant

A production-minded AI-powered staff tool that helps a strata management consultancy process incoming client enquiries. The AI classifies enquiries, detects urgency, summarises the message, recommends a staff action, drafts a professional reply, and fires an outbound webhook so results can flow into any downstream system — all while keeping staff in full control before anything is sent.

---

## Business Problem

Strata Management Consultants receives a high volume of client enquiries via email and web forms. Staff must read each message, determine the nature of the request, decide who should handle it, and write a response. This is time-consuming and inconsistent, especially during peak periods.

## Solution Summary

This tool acts as a first-pass filter. Staff paste a client message into the web UI, click **Analyse**, and within seconds see:

- The primary classification and all applicable categories
- Per-category confidence breakdown (bar chart)
- Urgency level
- A plain-English summary
- A recommended next action
- A draft reply they can edit and send

Enquiries that are vague, risky, legal, or angry are automatically flagged for manual review. The AI never sends anything — staff remain in full control.

---

## Features

- Classify enquiries into five categories
- **Multi-label classification** — surfaces all applicable categories, not just the top one
- **Per-category confidence breakdown** — visual bar chart for all five categories
- Urgency detection (Low / Medium / High)
- Enquiry summary
- Recommended staff action
- AI-drafted suggested response (editable, copy-to-clipboard)
- Human review flagging with banner for risky or unclear messages
- Risk signal detection using spaCy lemmatization (legal, safety, threat keywords)
- Six sample enquiries for quick testing
- **Interactive health check CLI** (`health_check_main.py`) — runs any enquiry through every pipeline step with PASS/FAIL output and a timestamped log file
- **Outbound webhook** — fires the full result as JSON to any configured URL after each analysis (n8n, Zapier, Make, Slack, CRM, etc.)
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
| NLP | spaCy `en_core_web_sm` (risk signal detection) |
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
├── main.py                   Entry point — full pipeline sequential flow
├── health_check_main.py      Interactive CLI pipeline health checker
├── config.py                 All configuration from environment variables
├── requirements.txt
├── .env.example              Template for environment variables
├── .gitignore
├── README.md
│
├── app/
│   ├── integrations/
│   │   └── webhook.py            Outbound webhook (fire-and-forget POST)
│   │
│   ├── services/
│   │   ├── preprocessor.py       Input validation, cleaning, spaCy risk detection
│   │   ├── prompt_builder.py     Builds system + user prompts for Ollama
│   │   ├── ollama_service.py     Ollama API client with typed error handling
│   │   ├── enquiry_analyzer.py   Business review rules (human-review flags)
│   │   ├── health_service.py     Health check logic
│   │   └── rag_engine.py         Placeholder for future RAG implementation
│   │
│   ├── utils/
│   │   ├── logger.py             Logging setup (file + console, privacy-aware)
│   │   ├── validators.py         Input validation helpers
│   │   ├── json_utils.py         AI response parsing with four fallback strategies
│   │   └── response_helpers.py   Standardised JSON response formatting
│   │
│   └── models/
│       └── schemas.py            AnalysisResult dataclass + ALLOWED_CATEGORIES
│
├── web/
│   ├── templates/
│   │   └── index.html            Staff UI
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

Verify it was pulled:

```bash
ollama list
```

Ollama runs as a background service after installation. If it is not running, start it:

```bash
ollama serve
```

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
python -m spacy download en_core_web_sm
```

### 5. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` if needed. The defaults work for a standard local Ollama installation.

### 6. Run the app

```bash
python main.py
```

The app starts at **http://localhost:5000**.

---

## Pipeline Health Check

Run any enquiry through every step of the pipeline interactively:

```bash
python health_check_main.py
```

Each step prints PASS / FAIL / SKIP. A full summary including per-category confidence breakdown and a timestamped log file are saved to `logs/` after each run.

---

## Outbound Webhook

After every analysis, the app can fire a POST request with the full result to any URL you configure. Set `WEBHOOK_URL` in `.env`:

```
WEBHOOK_URL=https://your-n8n-instance/webhook/...
WEBHOOK_SECRET=optional-hmac-signing-secret
```

Leave `WEBHOOK_URL` blank to disable. The webhook runs in a background thread — it never delays the browser response. If it fails, a warning is logged and the app continues normally.

**Payload sent:**
```json
{
  "event": "enquiry.analysed",
  "classification": "New Client",
  "classifications": ["New Client", "Support Request"],
  "confidence": 0.78,
  "urgency": "Medium",
  "needs_human_review": false,
  "summary": "...",
  "recommended_action": "...",
  "suggested_response": "...",
  "reason": "...",
  "category_scores": {
    "New Client": 0.78,
    "Support Request": 0.62,
    "Complaint": 0.05,
    "General Question": 0.12,
    "Unknown / Needs Human Review": 0.02
  },
  "processing_time_ms": 1420
}
```

**Testing the webhook locally:**

Run a simple receiver in a second terminal:
```bash
python -c "
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-Length']))
        print(json.dumps(json.loads(body), indent=2))
        self.send_response(200); self.end_headers()
    def log_message(self, *a): pass

print('Listening on http://localhost:9000 ...')
HTTPServer(('', 9000), H).serve_forever()
"
```

Set `WEBHOOK_URL=http://localhost:9000` in `.env`, restart the app, and submit any enquiry.

---

## Health Endpoints

**App health:**
```bash
curl http://localhost:5000/health
```

**Ollama health:**
```bash
curl http://localhost:5000/health/ollama
```

---

## API Reference

`POST /api/analyze`

**Request:**
```json
{ "enquiry": "<client message text>" }
```

**Response:**
```json
{
  "status": "ok",
  "data": {
    "classification": "New Client",
    "classifications": ["New Client", "Support Request"],
    "confidence": 0.78,
    "urgency": "Medium",
    "summary": "...",
    "recommended_action": "...",
    "suggested_response": "...",
    "needs_human_review": false,
    "reason": "...",
    "category_scores": {
      "New Client": 0.78,
      "Support Request": 0.62,
      "Complaint": 0.05,
      "General Question": 0.12,
      "Unknown / Needs Human Review": 0.02
    },
    "processing_time_ms": 1420,
    "preprocessing": {
      "risk_signals": [],
      "is_potentially_unclear": false,
      "word_count": 87,
      "character_count": 512
    }
  }
}
```

---

## Prompt Design

The prompt is split into a `system` message (rules + JSON schema) and a `user` message (the enquiry + preprocessing context). Key design choices:

- The model returns **only valid JSON** — no markdown, no preamble
- The five classification categories are listed explicitly so the model cannot invent variations
- **Multi-label rule** — if an enquiry spans multiple categories, all applicable ones are listed in `classifications` with the dominant one in `classification`
- **`category_scores`** — the model scores all five categories, which drives the confidence bar and encourages deliberate multi-label thinking
- Suggested responses are framed as **drafts**; the model is told not to claim actions have already been taken
- `temperature: 0.4` — reliable structured JSON output with enough range for natural prose in the response draft
- Four JSON extraction fallback strategies in `json_utils.py` handle imperfect model output

See [docs/PROMPT_DESIGN.md](docs/PROMPT_DESIGN.md) for full detail.

---

## Logging

- Logs are written to the console and to `logs/app.log` (when `LOG_TO_FILE=True`)
- **Full enquiry text is never logged by default** — only metadata is captured
- Set `LOG_FULL_ENQUIRY=True` in `.env` for local debugging only. **Never enable this in production**

See [docs/LOGGING.md](docs/LOGGING.md) for full detail.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Empty or whitespace-only input | 422 with friendly message |
| Input too short (< 10 chars) | 422 with guidance |
| Input too long (> 5000 chars) | 422 |
| Ollama not running | 503 — AI service unavailable |
| Ollama timeout | 504 — timeout error |
| Model not pulled | 502 — model error with pull instructions |
| AI returns invalid JSON | Four extraction strategies tried, then safe fallback |
| Webhook delivery failure | Warning logged, app continues normally |
| Any unexpected exception | Caught, logged, safe response returned |

---

## Privacy Notes

- **No cloud APIs.** All AI processing is local via Ollama.
- **No enquiry data stored.** Each analysis is stateless.
- **Full enquiry text is not logged** unless explicitly enabled.
- **Webhook payload does not include raw enquiry text** — only the analysis result.

**For production deployment, add:**
- Staff authentication (SSO / LDAP)
- HTTPS via a reverse proxy (Nginx, Caddy)
- Role-based access control
- Audit logging with appropriate data handling policies
- Secure storage if enquiry archiving is needed

---

## Human Review Flags

The app flags enquiries for human review when:

1. AI confidence is below 0.70
2. The enquiry is vague, very short, or nonsensical
3. The message contains angry, threatening, or legal language (detected by spaCy)
4. The enquiry is safety-related or reputationally sensitive
5. The classification is **Complaint** (always flagged regardless of confidence)

When flagged, a prominent warning banner appears in the UI. The suggested response is still generated but clearly marked as a draft requiring review.

---

## Future Improvements

See [docs/FUTURE_IMPROVEMENTS.md](docs/FUTURE_IMPROVEMENTS.md). Key items:

- RAG integration using company-specific documents (`rag_engine.py` is a placeholder)
- Staff authentication and access control
- Persistent enquiry history with audit trail
- n8n / Zapier workflow integration via the outbound webhook
- Log rotation and production observability

---

## Assessment Alignment

| Requirement | Implementation |
|---|---|
| Five classification categories | `prompt_builder.py`, `schemas.py` ALLOWED_CATEGORIES |
| Confidence score | Derived from `category_scores[primary]` in `json_utils.py` |
| Urgency detection | Included in prompt and JSON output |
| Suggested response (draft) | Generated by model, editable in UI |
| Human review flagging | Business rules in `enquiry_analyzer.py`, UI banner |
| Health checks | `/health` and `/health/ollama` routes |
| Structured logging | `app/utils/logger.py`, privacy-aware |
| Fallback on AI failure | `json_utils.py` FALLBACK_RESULT |
| Configurable model | `OLLAMA_MODEL` environment variable |
| Local LLM (no cloud keys) | Ollama via `requests`, no external API calls |
| Separation of concerns | Services / utils / models / integrations / web all separated |
| Clean README | This document |

---

## Assumptions

1. Ollama runs locally on the default port (11434), configurable via `OLLAMA_BASE_URL`.
2. The model `gemma4:e2b` is available in Ollama's registry under that exact name.
3. The app is run from the project root directory (`python main.py`).
4. Python 3.10+ is required for `str | None` union type syntax in type hints.
5. The `.venv` virtual environment directory is excluded from version control.
6. No database or persistent storage is needed — each analysis is stateless.
7. Staff using the tool are trusted internal users. Authentication is out of scope for this assessment.
