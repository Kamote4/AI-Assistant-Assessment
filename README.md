# Enquiry AI Assistant

A production-minded AI-powered staff tool that helps a strata management consultancy process incoming client enquiries. The AI classifies enquiries, detects urgency, summarises the message, recommends a staff action, drafts a professional reply, and fires an outbound webhook so results can flow into any downstream system — all while keeping staff in full control before anything is sent.

---

## Development Environment

This project was built and tested on **Windows 11 + WSL2 (Ubuntu)**. All commands in this guide are run inside WSL unless stated otherwise. If you are on a native Linux or macOS machine the steps are identical — just skip the WSL-specific notes.

**What is WSL?** Windows Subsystem for Linux lets you run a full Linux terminal inside Windows. If you don't have it, open PowerShell as Administrator and run:
```powershell
wsl --install
```
Then restart and open Ubuntu from the Start menu.

---

## Business Problem

The business receives a high volume of client enquiries via email and web forms. Staff must read each message, determine the nature of the request, decide who should handle it, and write a response. This is time-consuming and inconsistent, especially during peak periods.

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

## Architecture

The app is a sequential pipeline. Each step hands its output to the next. All AI processing is local — nothing leaves the machine.

```
  STAFF BROWSER
  ┌─────────────────────────────────────────┐
  │   Paste enquiry text → click Analyse    │
  └─────────────────┬───────────────────────┘
                    │  POST /api/analyze
                    ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │  FLASK PIPELINE  (main.py)                                          │
  │                                                                     │
  │  ① PREPROCESS ──────────────────────── preprocessor.py            │
  │    • Validate length and content                                    │
  │    • Clean text (whitespace, encoding)                              │
  │    • Detect risk signals via spaCy (legal / threat keywords)        │
  │                          │                                          │
  │                          ▼                                          │
  │  ② BUILD PROMPT ─────────────────────── prompt_builder.py         │
  │    • system message: classification rules + JSON schema             │
  │    • user message:   cleaned enquiry + detected risk context        │
  │                          │                                          │
  │                          ▼                                          │
  │  ③ CALL LOCAL LLM ───────────────────── ollama_service.py         │
  │    • POST → Ollama API at localhost:11434                           │
  │    • Model: gemma4:e2b   │   temperature: 0.4                      │
  │    • Returns raw JSON text                                          │
  │                          │                                          │
  │                          ▼                                          │
  │  ④ PARSE & NORMALISE ────────────────── json_utils.py             │
  │    Strategy 1 → direct JSON parse                                   │
  │    Strategy 2 → newline sanitisation + re-parse                     │
  │    Strategy 3 → extract from ``` code fence ```                     │
  │    Strategy 4 → find first { ... } block                            │
  │    ✓ normalise category_scores (clamp each to 0.0 – 1.0)           │
  │    ✓ derive confidence from category_scores[primary_classification] │
  │    ✓ enforce allowed classification labels                          │
  │    ✗ all strategies fail → return safe fallback result              │
  │                          │                                          │
  │                          ▼                                          │
  │  ⑤ BUSINESS RULES ───────────────────── enquiry_analyzer.py       │
  │    Force needs_human_review = true if any of:                       │
  │      • confidence < 0.70                                            │
  │      • vague or nonsensical input                                   │
  │      • legal / angry / threatening language detected by spaCy       │
  │      • classification is Complaint (always flagged)                 │
  │                          │                                          │
  │              ┌───────────┴───────────┐                             │
  │              ▼                       ▼                             │
  │  ⑥ LOG (metadata only)   ⑦ WEBHOOK (background thread)           │
  │     logger.py                webhook.py                            │
  │     no raw enquiry text      fire-and-forget POST                  │
  │     written to logs/         HMAC-SHA256 signed payload            │
  │              │                       │                             │
  └──────────────│───────────────────────│─────────────────────────────┘
                 │                       │
                 ▼                       ▼
  ┌──────────────────────┐   ┌───────────────────────────────────────┐
  │  BROWSER UI          │   │  DOWNSTREAM (optional)                │
  │                      │   │                                       │
  │  • Classifications   │   │   n8n / Zapier / Make / custom        │
  │  • Confidence bars   │   │                                       │
  │  • Urgency level     │   │   ┌──────────┐   ┌────────────────┐  │
  │  • Summary           │   │   │  Gmail   │   │  HubSpot /     │  │
  │  • Recommended action│   │   │  inbox   │   │  Salesforce    │  │
  │  • Draft reply       │   │   └──────────┘   └────────────────┘  │
  │  • Human review flag │   │   ┌──────────┐   ┌────────────────┐  │
  └──────────────────────┘   │   │  Slack   │   │  Google Sheets │  │
                              │   │  alerts  │   │  / audit log   │  │
                              │   └──────────┘   └────────────────┘  │
                              └───────────────────────────────────────┘
```

### Key design decisions

- **Local-only LLM** — Ollama runs on the same machine; enquiry text never reaches a cloud API
- **`category_scores` in the prompt** — forces the model to score all five categories, which naturally produces multi-label output and a consistent confidence value (derived from `category_scores[primary]`, not the model's self-reported number)
- **Four parse strategies** — small local models sometimes wrap JSON in markdown fences or add preamble text; the fallback chain handles this without crashing
- **Background webhook thread** — the webhook runs as a daemon thread so it cannot block or slow down the browser response
- **Staff always in the loop** — the tool generates a draft, not a sent reply; the human review flag escalates anything uncertain

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

Before you start, make sure you have the following installed:

| Tool | Check command | Version used | Min required |
|---|---|---|---|
| Python | `python3 --version` | 3.12.3 | 3.10+ |
| pip | `pip --version` | 24.0 | any |
| Git | `git --version` | 2.43.0 | any |
| Ollama | `ollama --version` | 0.23.2 | any |

If Python is not installed on WSL/Ubuntu:
```bash
sudo apt update && sudo apt install python3 python3-pip python3-venv -y
```

---

### Step 1 — Install Ollama

> **WSL note:** Install Ollama on **Windows**, not inside WSL. Download the Windows installer from [ollama.com](https://ollama.com). Once installed, Ollama runs as a Windows background service and WSL can reach it automatically at `localhost:11434`.

After installing, open a **Windows** terminal (not WSL) and pull the model:

```bash
ollama pull gemma4:e2b
```

Verify it downloaded:
```bash
ollama list
```

You should see `gemma4:e2b` in the list. Ollama will now run automatically in the background every time Windows starts.

---

### Step 2 — Clone the repository

Inside your WSL terminal:

```bash
git clone https://github.com/Kamote4/AI-Assistant-Assessment.git
cd AI-Assistant-Assessment
```

---

### Step 3 — Create a virtual environment

A virtual environment keeps this project's dependencies separate from the rest of your system.

```bash
python3 -m venv .venv
```

**Activate it:**
```bash
source .venv/bin/activate
```

Your terminal prompt will change to show `(.venv)` at the start — this means it is active.

> **Important:** You need to activate the virtual environment every time you open a new terminal window before running any project commands. If you see `ModuleNotFoundError` errors, it usually means the venv is not active.

---

### Step 4 — Install dependencies

```bash
pip install -r requirements.txt
```

Then download the spaCy language model (used for risk signal detection):
```bash
python -m spacy download en_core_web_sm
```

---

### Step 5 — Configure environment variables

Copy the example config file:
```bash
cp .env.example .env
```

The defaults work out of the box for a standard local setup. Open `.env` in your editor if you need to change the model name, Ollama URL, or logging settings.

---

### Step 6 — Run the app

```bash
python main.py
```

You should see:
```
INFO  Starting Strata Enquiry AI Assistant
INFO  Ollama model: gemma4:e2b @ http://localhost:11434
```

Open your **Windows browser** and go to **http://localhost:5000**.

> **WSL note:** Even though the app runs inside WSL, you open it in your normal Windows browser at `localhost:5000`. WSL2 automatically forwards ports between Windows and Linux — no extra configuration needed.

---

## Pipeline Health Check

Run any enquiry through every step of the pipeline interactively. Make sure your virtual environment is active first:

```bash
python health_check_main.py
```

Type or paste an enquiry, then press **Enter on a blank line** to submit. Each pipeline step prints PASS / FAIL / SKIP. A full summary with per-category confidence breakdown is shown at the end, and a timestamped log file is saved to `logs/`.

---

## Outbound Webhook

After every analysis, the app can fire a POST request with the full result to any URL you configure. Set `WEBHOOK_URL` in `.env`:

```
WEBHOOK_URL=https://your-n8n-instance/webhook/...
WEBHOOK_SECRET=optional-hmac-signing-secret
```

Leave `WEBHOOK_URL` blank to disable. The webhook runs in a background thread — it never delays the browser response. If delivery fails, a warning is logged and the app continues normally.

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

Open a second WSL terminal, activate the venv, and run:
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

Set `WEBHOOK_URL=http://localhost:9000` in `.env`, restart the app, submit any enquiry, and watch the JSON appear in the second terminal.

---

## Health Endpoints

```bash
curl http://localhost:5000/health
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

## Troubleshooting

**`ModuleNotFoundError: No module named 'flask'` (or any other module)**
Your virtual environment is not active. Run:
```bash
source .venv/bin/activate
```

**`Could not connect to Ollama`**
Ollama is not running. On Windows, open Task Manager and check if Ollama is in the system tray. If not, launch it from the Start menu. Then retry.

**`Model 'gemma4:e2b' was not found`**
The model has not been pulled yet. In a Windows terminal run:
```bash
ollama pull gemma4:e2b
```

**App starts but browser shows "connection refused"**
Make sure you are opening `http://localhost:5000` (not HTTPS). Flask's development server does not use HTTPS by default.

**WSL can't reach `localhost:11434` (Ollama)**
In rare WSL network configurations, `localhost` may not forward to Windows. Try using the Windows host IP instead. Find it with:
```bash
cat /etc/resolv.conf | grep nameserver
```
Then set `OLLAMA_BASE_URL=http://<that-ip>:11434` in your `.env`.

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

**Current deployment:** The app runs locally and was exposed publicly during development using [ngrok](https://ngrok.com), which tunnels `localhost:5000` to a public HTTPS URL. This is sufficient for demos and testing but not intended for production.

**For a production deployment, the next steps would include:**
- Staff authentication (SSO / LDAP)
- HTTPS via a reverse proxy (Nginx, Caddy)
- Role-based access control
- Audit logging with appropriate data handling policies
- Secure storage if enquiry archiving is needed

See [docs/FUTURE_IMPROVEMENTS.md](docs/FUTURE_IMPROVEMENTS.md) for the full roadmap.

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
- n8n / Zapier workflow integration via the outbound webhook (webhook is built — n8n wiring is next)
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

1. Ollama runs on the Windows host at port 11434 (WSL accesses it via `localhost`).
2. The model `gemma4:e2b` is available in Ollama's registry under that exact name.
3. The app is run from the project root directory (`python main.py`).
4. Python 3.10+ is required for `str | None` union type syntax in type hints.
5. The `.venv` virtual environment directory is excluded from version control.
6. No database or persistent storage is needed — each analysis is stateless.
7. Staff using the tool are trusted internal users. Authentication is out of scope for this assessment.

---

## AI Tools Used During Development

This project was built with the assistance of AI tools, as permitted by the assessment instructions.

| Tool | How it was used |
|---|---|
| **ChatGPT** | Initial brainstorming and architecture design — helped map out the pipeline stages, folder structure, and overall approach before any code was written |
| **Claude Code** | Primary coding assistant throughout the build — iterative back-and-forth conversation covering implementation, debugging, prompt engineering, the category scores fix, webhook integration, and documentation |

