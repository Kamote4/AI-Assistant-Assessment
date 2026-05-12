#!/usr/bin/env python3
"""
health_check_main.py — Interactive end-to-end pipeline health check.

Prompts you for an enquiry in the terminal, runs it through every step of the
analysis pipeline (the same steps defined in main.py), prints a PASS / FAIL /
SKIP result after each step, shows a full analysis summary, and writes a
timestamped log file you can review later.

Usage:
    python health_check_main.py
"""

import sys
import time
import json
from datetime import datetime
from pathlib import Path

# ── Pipeline imports — mirrors main.py ───────────────────────────────────────
from config import config
from app.services.preprocessor import preprocess_enquiry           # Step 2
from app.services.prompt_builder import build_analysis_prompt      # Step 3
from app.services.ollama_service import (                          # Step 4
    call_ollama,
    OllamaConnectionError,
    OllamaTimeoutError,
    OllamaModelError,
)
from app.utils.json_utils import parse_ai_response                 # Step 5
from app.services.enquiry_analyzer import apply_review_rules       # Step 6

# ── Terminal colour helpers ───────────────────────────────────────────────────
_USE_COLOR = sys.stdout.isatty()

def _c(code, text):
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text

def green(t):  return _c("32", t)
def red(t):    return _c("31", t)
def yellow(t): return _c("33", t)
def bold(t):   return _c("1",  t)
def dim(t):    return _c("2",  t)

LINE  = "─" * 62
TOTAL = 7   # number of pipeline steps

# ── Step result constructors ──────────────────────────────────────────────────

def _pass(detail=""):
    return {"ok": True,  "skipped": False, "detail": detail}

def _fail(detail=""):
    return {"ok": False, "skipped": False, "detail": detail}

def _skip():
    return {"ok": False, "skipped": True,  "detail": "skipped — prior step failed"}


def _print_step(n, name, sr):
    if sr["skipped"]:
        badge = yellow("— SKIP")
    elif sr["ok"]:
        badge = green("✓ PASS")
    else:
        badge = red("✗ FAIL")

    label = f"[{n}/{TOTAL}]  {name}"
    print(f"  {label:<42}  {badge}")
    if sr["detail"]:
        print(f"         {dim(sr['detail'])}")
    print()


# ── Individual pipeline step functions ───────────────────────────────────────
# Each returns (step_result, output_data).
# output_data is None on failure so the caller can safely skip later steps.

def step1_parse(raw_text: str):
    if not raw_text.strip():
        return _fail("empty input — nothing to process"), None
    return _pass(f"chars={len(raw_text)}"), raw_text.strip()


def step2_preprocess(raw_text: str):
    preprocessing = preprocess_enquiry(raw_text)
    if preprocessing.validation_error:
        return _fail(f"validation_error={preprocessing.validation_error!r}"), None
    detail = (
        f"words={preprocessing.metadata['word_count']} | "
        f"risk_signals={preprocessing.risk_signals} | "
        f"unclear={preprocessing.is_potentially_unclear}"
    )
    return _pass(detail), preprocessing


def step3_build_prompt(preprocessing):
    system_prompt, user_message = build_analysis_prompt(preprocessing)
    detail = (
        f"system_prompt={len(system_prompt)} chars | "
        f"user_message={len(user_message)} chars"
    )
    return _pass(detail), (system_prompt, user_message)


def step4_call_ollama(system_prompt: str, user_message: str):
    t0 = time.time()
    try:
        raw_response = call_ollama(system_prompt, user_message)
        elapsed = time.time() - t0
        if not raw_response:
            return _fail("Ollama returned an empty response"), None
        detail = (
            f"model={config.OLLAMA_MODEL} | "
            f"response={len(raw_response)} chars | "
            f"took={elapsed:.2f}s"
        )
        return _pass(detail), raw_response
    except OllamaConnectionError as exc:
        return _fail(f"OllamaConnectionError — {exc}"), None
    except OllamaTimeoutError as exc:
        return _fail(f"OllamaTimeoutError — {exc}"), None
    except OllamaModelError as exc:
        return _fail(f"OllamaModelError — {exc}"), None


def step5_parse_response(raw_response: str):
    result = parse_ai_response(raw_response)
    is_fallback = (
        result.get("confidence") == 0.0
        and result.get("classification") == "Unknown / Needs Human Review"
    )
    detail = (
        f"classification={result.get('classification')!r} | "
        f"confidence={result.get('confidence')} | "
        f"urgency={result.get('urgency')!r}"
    )
    if is_fallback:
        detail += " | ⚠ fallback result used (JSON could not be parsed)"
    return _pass(detail), result


def step6_apply_rules(result: dict, preprocessing):
    result = apply_review_rules(result, preprocessing)

    triggers = []
    if result.get("confidence", 1.0) < 0.70:
        triggers.append("low confidence")
    if result.get("classification") == "Complaint":
        triggers.append("Complaint classification")
    if preprocessing.risk_signals:
        triggers.append(f"risk signals ({', '.join(preprocessing.risk_signals)})")
    if preprocessing.is_potentially_unclear:
        triggers.append("unclear message")

    detail = f"needs_human_review={result.get('needs_human_review')}"
    if triggers:
        detail += f" — triggered by: {'; '.join(triggers)}"
    return _pass(detail), result


def step7_assemble(result: dict, preprocessing, start_time: float):
    processing_time_ms = int((time.time() - start_time) * 1000)
    result["processing_time_ms"] = processing_time_ms
    result["preprocessing"] = {
        "risk_signals":           preprocessing.risk_signals,
        "is_potentially_unclear": preprocessing.is_potentially_unclear,
        "word_count":             preprocessing.metadata["word_count"],
        "character_count":        preprocessing.metadata["character_count"],
    }
    return _pass(f"processing_time_ms={processing_time_ms}"), result


# ── Summary display ───────────────────────────────────────────────────────────

def _print_summary(result: dict, preprocessing):
    pct     = round((result.get("confidence") or 0) * 100)
    signals = preprocessing.risk_signals
    words   = preprocessing.metadata["word_count"]

    print(LINE)
    print(bold("ANALYSIS SUMMARY"))
    print(f"  Classification:     {result.get('classification', '—')}")
    print(f"  Confidence:         {pct}%")
    print(f"  Urgency:            {result.get('urgency', '—')}")
    print(f"  Human review:       {'Yes' if result.get('needs_human_review') else 'No'}")
    print(f"  Risk signals:       {', '.join(signals) if signals else 'none'}")
    print(f"  Word count:         {words}")
    print(f"  Processing time:    {result.get('processing_time_ms', '—')} ms")
    print()
    print(bold("REASON"))
    print(f"  {result.get('reason', '—')}")
    print()
    print(bold("RECOMMENDED ACTION"))
    print(f"  {result.get('recommended_action', '—')}")
    print()
    print(bold("SUGGESTED RESPONSE"))
    print(LINE)
    for line in (result.get("suggested_response") or "—").splitlines():
        print(f"  {line}")
    print(LINE)


# ── Log writer ────────────────────────────────────────────────────────────────

def _save_log(
    raw_text: str,
    step_results: list,
    result: dict,
    preprocessing,
) -> Path:
    log_dir = Path(config.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path  = log_dir / f"health_check_{timestamp}.log"

    pct = round((result.get("confidence") or 0) * 100) if result else 0

    sections = [
        f"health_check_main.py — {datetime.now().isoformat()}",
        f"model: {config.OLLAMA_MODEL}  |  ollama: {config.OLLAMA_BASE_URL}",
        "=" * 62,
        "",
        "ENQUIRY (raw input)",
        "-" * 40,
        raw_text,
        "",
        "PIPELINE STEPS",
        "-" * 40,
    ]

    for sr in step_results:
        status = "PASS" if sr["ok"] else ("SKIP" if sr["skipped"] else "FAIL")
        sections.append(f"  [{sr['step']}/{TOTAL}]  {sr['name']:<30}  {status}")
        if sr["detail"]:
            sections.append(f"         {sr['detail']}")

    if result:
        signals = preprocessing.risk_signals if preprocessing else []
        sections += [
            "",
            "SUMMARY",
            "-" * 40,
            f"  Classification:     {result.get('classification', '—')}",
            f"  Confidence:         {pct}%",
            f"  Urgency:            {result.get('urgency', '—')}",
            f"  Human review:       {'Yes' if result.get('needs_human_review') else 'No'}",
            f"  Risk signals:       {', '.join(signals) if signals else 'none'}",
            f"  Processing time:    {result.get('processing_time_ms', '—')} ms",
            "",
            "REASON",
            f"  {result.get('reason', '—')}",
            "",
            "RECOMMENDED ACTION",
            f"  {result.get('recommended_action', '—')}",
            "",
            "SUGGESTED RESPONSE",
            "-" * 40,
            result.get("suggested_response") or "—",
            "",
            "FULL RESULT (JSON)",
            "-" * 40,
            json.dumps(result, indent=2, default=str),
        ]

    log_path.write_text("\n".join(sections), encoding="utf-8")
    return log_path


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print()
    print(bold("Strata Enquiry — Pipeline Health Check"))
    print(LINE)
    print()

    # ── Collect input ─────────────────────────────────────────────────────────
    print("Enter your enquiry below.")
    print(dim("(Press Enter on a blank line when done.  Ctrl+C to quit.)"))
    print()

    lines = []
    try:
        while True:
            line = input()
            if line == "" and lines:
                break
            lines.append(line)
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        sys.exit(0)

    raw_text = "\n".join(lines).strip()
    if not raw_text:
        print(red("No input provided. Exiting."))
        sys.exit(1)

    print()
    print(f"Running {TOTAL}-step pipeline…")
    print(LINE)
    print()

    # ── Run each pipeline step ────────────────────────────────────────────────
    overall_start = time.time()
    step_results  = []
    ok            = True

    # Step 1 — always runs; the other steps need its output
    sr, raw_text_clean = step1_parse(raw_text)
    step_results.append({**sr, "step": 1, "name": "Parse input"})
    _print_step(1, "Parse input", sr)
    ok = sr["ok"]

    # Step 2
    sr, preprocessing = step2_preprocess(raw_text_clean) if ok else (_skip(), None)
    step_results.append({**sr, "step": 2, "name": "Preprocess"})
    _print_step(2, "Preprocess", sr)
    ok = ok and sr["ok"]

    # Step 3
    sr, prompts = step3_build_prompt(preprocessing) if ok else (_skip(), None)
    step_results.append({**sr, "step": 3, "name": "Build AI prompt"})
    _print_step(3, "Build AI prompt", sr)
    ok = ok and sr["ok"]

    # Step 4
    sr, raw_response = step4_call_ollama(*prompts) if ok else (_skip(), None)
    step_results.append({**sr, "step": 4, "name": "Call Ollama"})
    _print_step(4, "Call Ollama", sr)
    ok = ok and sr["ok"]

    # Step 5
    sr, result = step5_parse_response(raw_response) if ok else (_skip(), None)
    step_results.append({**sr, "step": 5, "name": "Parse JSON response"})
    _print_step(5, "Parse JSON response", sr)
    ok = ok and sr["ok"]

    # Step 6
    sr, result = step6_apply_rules(result, preprocessing) if ok else (_skip(), None)
    step_results.append({**sr, "step": 6, "name": "Apply review rules"})
    _print_step(6, "Apply review rules", sr)
    ok = ok and sr["ok"]

    # Step 7
    sr, result = step7_assemble(result, preprocessing, overall_start) if ok else (_skip(), None)
    step_results.append({**sr, "step": 7, "name": "Assemble final result"})
    _print_step(7, "Assemble final result", sr)

    # ── Outcome banner ────────────────────────────────────────────────────────
    passed  = sum(1 for s in step_results if s["ok"])
    failed  = sum(1 for s in step_results if not s["ok"] and not s["skipped"])
    skipped = sum(1 for s in step_results if s["skipped"])

    print(LINE)
    if failed == 0:
        verdict = green(f"All {passed} steps passed")
    else:
        parts = [red(f"{failed} step{'s' if failed != 1 else ''} failed")]
        if skipped:
            parts.append(yellow(f"{skipped} skipped"))
        verdict = f"{passed}/{TOTAL} passed — " + ", ".join(parts)
    print(f"  Result: {verdict}")
    print(LINE)
    print()

    # ── Summary ───────────────────────────────────────────────────────────────
    if result and preprocessing:
        _print_summary(result, preprocessing)

    # ── Save log ──────────────────────────────────────────────────────────────
    log_path = _save_log(raw_text, step_results, result or {}, preprocessing)
    print()
    print(dim(f"Full log saved to: {log_path}"))
    print()


if __name__ == "__main__":
    main()
