"""
main.py — Entry point. Read this file to follow the full request lifecycle.

The analyse pipeline (POST /api/analyze) is written out step-by-step here so
you can trace the logic from top to bottom in one place.  Each step delegates
to a focused module for its implementation; the *sequence* lives here.

Pipeline:
  Step 1 — Parse the incoming HTTP request
  Step 2 — Preprocess: validate, clean, extract metadata and risk signals
  Step 3 — Build the AI prompt from the preprocessed data
  Step 4 — Call the local Ollama model
  Step 5 — Parse and normalise the model's JSON response
  Step 6 — Apply business review rules (human-review flags)
  Step 7 — Enrich with timing + preprocessing data and return
"""

import os
import time
from flask import Flask, render_template, request, jsonify

# ── Configuration and logging ─────────────────────────────────────────────────
from config import config
from app.utils.logger import setup_logger

# ── Step 2 — Preprocessing ────────────────────────────────────────────────────
from app.services.preprocessor import preprocess_enquiry

# ── Step 3 — Prompt assembly ──────────────────────────────────────────────────
from app.services.prompt_builder import build_analysis_prompt

# ── Step 4 — LLM call ────────────────────────────────────────────────────────
from app.services.ollama_service import (
    call_ollama,
    OllamaConnectionError,
    OllamaTimeoutError,
    OllamaModelError,
)

# ── Step 5 — Response parsing ─────────────────────────────────────────────────
from app.utils.json_utils import parse_ai_response

# ── Step 6 — Business review rules ───────────────────────────────────────────
from app.services.enquiry_analyzer import apply_review_rules

# ── Supporting utilities ──────────────────────────────────────────────────────
from app.services.health_service import check_app_health, check_ollama_health
from app.utils.response_helpers import success_response, error_response
from app.integrations.webhook import push_result

# ── Flask app ─────────────────────────────────────────────────────────────────
logger = setup_logger(__name__)

_ROOT = os.path.dirname(os.path.abspath(__file__))
_WEB  = os.path.join(_ROOT, "web")

app = Flask(
    __name__,
    template_folder=os.path.join(_WEB, "templates"),
    static_folder=os.path.join(_WEB, "static"),
    static_url_path="/static",
)
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["DEBUG"]      = config.FLASK_DEBUG


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():

    start_time = time.time()

    # ── Step 1: Parse the incoming request ────────────────────────────────────
    data = request.get_json(silent=True)
    if not data:
        logger.warning("Rejected: missing JSON body")
        return error_response("Invalid request: JSON body required.", 400)

    raw_text = data.get("enquiry", "")

    # ── Step 2: Preprocess ────────────────────────────────────────────────────
    # Validates length, normalises whitespace, detects risk keywords, and checks
    # whether the message is potentially vague or nonsensical.
    # If validation_error is set the input is rejected before any AI call is made.
    preprocessing = preprocess_enquiry(raw_text)

    if preprocessing.validation_error:
        logger.warning(f"Validation failed: {preprocessing.validation_error}")
        return error_response(preprocessing.validation_error, 422)

    if config.LOG_FULL_ENQUIRY:
        logger.debug(f"Enquiry (clean): {preprocessing.clean_text}")

    logger.info(
        f"Request accepted | chars={preprocessing.metadata['character_count']} | "
        f"words={preprocessing.metadata['word_count']} | "
        f"risk_signals={preprocessing.risk_signals} | "
        f"unclear={preprocessing.is_potentially_unclear}"
    )

    # ── Step 3: Build the AI prompt ───────────────────────────────────────────
    # Returns (system_prompt, user_message).  The user message appends a short
    # structured context block (word count, contact details, risk signals, clarity
    # flags) so the model has signal beyond the raw text alone.
    system_prompt, user_message = build_analysis_prompt(preprocessing)

    # ── Step 4: Call the local Ollama model ───────────────────────────────────
    # POSTs to Ollama's /api/chat with stream:false and returns the model's raw
    # text output.  Infrastructure failures surface as typed exceptions so the
    # caller gets a meaningful HTTP error rather than a silent fallback.
    try:
        raw_response = call_ollama(system_prompt, user_message)
    except OllamaConnectionError:
        logger.error("Ollama is not running or unreachable")
        return error_response("AI service unavailable. Ensure Ollama is running.", 503)
    except OllamaTimeoutError:
        logger.error("Ollama request timed out")
        return error_response("AI service timed out. Please try again.", 504)
    except OllamaModelError as exc:
        logger.error(f"Ollama model error: {exc}")
        return error_response(f"AI model error: {exc}", 502)

    # ── Step 5: Parse the model's JSON response ───────────────────────────────
    # Local models sometimes produce imperfect JSON (literal \n inside strings,
    # markdown code fences, mixed prose).  parse_ai_response tries four extraction
    # strategies then validates and normalises every field.  Returns a safe
    # fallback dict if every strategy fails so the app stays usable.
    result = parse_ai_response(raw_response)

    # ── Step 6: Apply business review rules ───────────────────────────────────
    # These rules run after the AI responds and can override its output.
    # A result is flagged for human review when any of the following are true:
    #   • AI confidence is below 70 %
    #   • Classification is Complaint
    #   • Risk signals were detected during preprocessing (step 2)
    #   • Message was flagged as potentially unclear in preprocessing (step 2)
    result = apply_review_rules(result, preprocessing)

    # ── Step 7: Enrich and return ─────────────────────────────────────────────
    processing_time_ms = int((time.time() - start_time) * 1000)
    result["processing_time_ms"] = processing_time_ms
    result["preprocessing"] = {
        "risk_signals":           preprocessing.risk_signals,
        "is_potentially_unclear": preprocessing.is_potentially_unclear,
        "word_count":             preprocessing.metadata["word_count"],
        "character_count":        preprocessing.metadata["character_count"],
    }

    logger.info(
        f"Analysis complete | "
        f"classification={result.get('classification')!r} | "
        f"confidence={result.get('confidence')} | "
        f"urgency={result.get('urgency')!r} | "
        f"needs_human_review={result.get('needs_human_review')} | "
        f"processing_time_ms={processing_time_ms}"
    )

    # Fire-and-forget webhook push (no-op if WEBHOOK_URL is not configured)
    push_result(result, raw_text)

    return success_response(result)


@app.route("/health")
def health():
    return jsonify(check_app_health())


@app.route("/health/ollama")
def health_ollama():
    result = check_ollama_health()
    status_code = 200 if result.get("ollama_connected") else 503
    return jsonify(result), status_code


# ── Error handlers ────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return jsonify({"status": "error", "message": "Endpoint not found."}), 404


@app.errorhandler(500)
def server_error(e):
    logger.error(f"Unhandled server error: {e}")
    return jsonify({"status": "error", "message": "An unexpected server error occurred."}), 500


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info(f"Starting {config.APP_NAME} v{config.VERSION}")
    logger.info(f"Ollama model: {config.OLLAMA_MODEL} @ {config.OLLAMA_BASE_URL}")
    logger.info(f"Debug mode: {config.FLASK_DEBUG}")
    app.run(host="0.0.0.0", port=5000, debug=config.FLASK_DEBUG)
