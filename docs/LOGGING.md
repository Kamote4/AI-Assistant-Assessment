# Logging

## Setup

Logging is configured in `app/utils/logger.py` and initialised once when the first module calls `setup_logger()`. All subsequent calls return named child loggers that propagate to the same root handler.

Each log line follows this format:

```
2025-06-01 09:14:32 | INFO     | app.routes | Analysis complete | classification='New Client' | confidence=0.93 | ...
```

---

## Log levels

| Level | Used for |
|---|---|
| DEBUG | Verbose detail (JSON extraction strategy, full enquiry text when enabled) |
| INFO | Normal operational events (startup, requests, completions, health checks) |
| WARNING | Recoverable issues (fallback used, validation failures, missing JSON fields) |
| ERROR | Failures that affected a request (Ollama down, timeout, unexpected exception) |

Set `LOG_LEVEL` in `.env` to control the minimum level captured.

---

## Key events logged

| Event | Level |
|---|---|
| App startup + model configuration | INFO |
| Health check requested / result | INFO / WARNING |
| Analysis request received (length only) | INFO |
| Validation failure | WARNING |
| Ollama request started | INFO |
| Ollama request completed | INFO |
| Ollama connection failure | ERROR |
| Ollama timeout | ERROR |
| Model not found | ERROR |
| JSON parsing success / failure | INFO / WARNING |
| Fallback result used + reason | WARNING |
| Final classification, confidence, urgency, needs_human_review, processing_time_ms | INFO |
| Webhook delivered (URL + HTTP status) | INFO |
| Webhook timeout or connection failure | WARNING |

---

## Privacy rules

By default the **full enquiry text is never logged**. Only safe metadata is captured:
- enquiry length (character count)
- classification
- confidence score
- urgency level
- needs_human_review flag
- processing time in milliseconds
- error type if applicable

Setting `LOG_FULL_ENQUIRY=True` in `.env` enables full text logging at DEBUG level for local development. **This must never be enabled in production** — enquiry text may contain personal information about lot owners or tenants.

---

## File logging

When `LOG_TO_FILE=True`, log output is written to `logs/app.log` (or the directory set by `LOG_DIR`). The `logs/` directory is created automatically if it does not exist.

Log files are not rotated by default. For production, configure `RotatingFileHandler` or use an external log management service.

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Minimum log level |
| `LOG_TO_FILE` | `True` | Write logs to file |
| `LOG_FULL_ENQUIRY` | `False` | Log full enquiry text (development only) |
| `LOG_DIR` | `logs` | Directory for log files |
