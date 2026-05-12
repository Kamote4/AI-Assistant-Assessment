# Future Improvements

Realistic next steps if this tool were to grow into a production internal system.

---

## 1. RAG — Retrieval-Augmented Generation

Implement `rag_engine.py` to inject company-specific context into the prompt before the LLM call.

Planned sources:
- Company FAQ and service descriptions
- Standard response templates per classification
- Strata legislation summaries by state and territory
- Internal routing rules (which team handles which enquiry type)
- Policy documents for disputes, maintenance timelines, levy structures

Approach: embed documents using `nomic-embed-text` (via Ollama), store vectors in ChromaDB or FAISS, retrieve top-k chunks at query time.

---

## 2. Authentication and access control

Add staff login (e.g. Flask-Login + LDAP/SSO integration) so the tool is not accessible to unauthorised users. Assign roles: read-only viewer, analyst, admin.

---

## 3. Persistent enquiry history

Store analyses in a database (PostgreSQL or SQLite for smaller deployments) so staff can:
- Review past enquiries
- Track how enquiries were resolved
- Audit AI suggestions vs final responses sent

---

## 4. Staff feedback loop

Let staff mark AI results as correct or incorrect. Feed this data back to fine-tune prompts or, eventually, a fine-tuned model.

---

## 5. Email / web form integration

Connect to the company's email inbox or web enquiry form via API so enquiries appear automatically in the tool without manual copy-paste.

---

## 6. Batch processing

Add a bulk upload feature (CSV or email export) for processing a backlog of enquiries.

---

## 7. Response sending integration

Allow staff to send the reviewed and edited response directly from the UI via email or CRM integration (e.g. HubSpot, Salesforce). The tool should log the final sent version, not the AI draft.

---

## 8. Log rotation and monitoring

Add `RotatingFileHandler` for log files, integrate with a log aggregation service (e.g. Datadog, Papertrail, or self-hosted ELK), and set up alerts for high error rates or repeated fallback usage.

---

## 9. HTTPS and production deployment

Deploy behind a reverse proxy (Nginx or Caddy) with TLS. Use Gunicorn as the WSGI server instead of Flask's development server.

---

## 10. Model versioning and evaluation

Track which Ollama model version produced each result. Build an offline evaluation harness using the sample enquiries to compare model performance across upgrades.
