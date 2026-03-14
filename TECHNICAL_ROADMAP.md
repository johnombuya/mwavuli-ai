# Technical Roadmap: Project Mwavuli MVP

**Document type:** Technical roadmap  
**Purpose:** Outline how we plan to develop the Project Mwavuli MVP. This document will be reviewed by moderators and mentors to guide our incubation journey.  
**Version:** 1.0  
**Date:** January 2025  

---

## Current implementation status (handoff note)

When continuing on another machine: clone the repo, install backend deps (`pip install -r requirements.txt`), run migrations 001–005 on Supabase (or configure Firebase), set `backend/.env` (e.g. `DB_PROVIDER=supabase`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`; optionally `AUTH_DISABLED=true`, `LLM_PROVIDER`, `OLLAMA_*`). For full media verification, install Tesseract and FFmpeg (see backend README). Frontend: `npm install`, set `frontend/.env.local` (`NEXT_PUBLIC_BACKEND_URL`, optional `NEXT_PUBLIC_API_KEY`). Run backend: `uvicorn app.main:app --reload`; frontend: `npm run dev`.

- **Database:** Supabase (PostgreSQL) is the default (`DB_PROVIDER=supabase`); Firebase is still supported. Migrations live in `backend/migrations/` (001–005; includes `media_hashes` for media dedup).
- **Media verification:** Full pipeline: images (Tesseract OCR → text ensemble, then Gemini/Ollama Vision), audio (Whisper → text ensemble), video (FFmpeg keyframes + audio). Upload via `POST /api/v1/verify/media/upload`; WhatsApp webhook handles attached media (`NumMedia`, `MediaUrl0`).
- **Auth:** Optional API keys (`API_KEYS`, `API_KEY_ROLES`); `AUTH_DISABLED=true` bypasses in development.
- **Dashboard:** Briefing Room (executive summary, Kenya map, top threats) and Analyst View (charts). Verify page: text + image/audio/video (file upload and URL).

---

## 1. MVP Definition and Objectives

**Project name:** Project Mwavuli (niru_mwavuli)

**MVP scope:** A content verification system that detects potentially harmful information in the Kenyan political context. The MVP will:

- Accept **text and media** via API; users can check text only, media only, or both.
- Apply lexicon-based keyword detection, AI toxicity analysis, and context-aware checks (text); media analysis (images/video/audio) with option for placeholder or real detection in MVP.
- Return risk levels and multilingual warning messages (English, Swahili, Sheng).
- Store anonymized reports in Firebase for pattern analysis.
- Expose an analytics dashboard (Next.js) for moderators and partners.
- Automated alerts (e.g. spike in HIGH risk by county) to notify moderators of concerning patterns.

**Success criteria for MVP:**

- Text verification API is live and stable.
- Media verification API is available (placeholder or real analysis); both text and media flows report to the same analytics.
- Reports are persisted and queryable.
- Dashboard shows summary analytics and recent reports.
- Automated alerts (e.g. spike in HIGH risk by county) are configurable and delivered (e.g. email, webhook, or in-dashboard).
- Integration path with WhatsApp (n8n/Twilio) is documented and demonstrable.

---

## 2. Technical Approach

### 2.1 Architecture Overview

We will use a backend-for-frontend and API-first design:

- **Backend (Python/FastAPI):** Single service that runs lexicon checks, loads Detoxify for toxicity, calls Google Gemini for translation and Kenyan-context analysis, and reads/writes Firestore. **Text** and **media** verification are both supported: `/api/v1/verify/text` and `/api/v1/verify/media`. Media can use placeholder logic in MVP or optional models (e.g. Gemini Vision, deepfake detection). The backend also exposes analytics endpoints consumed by the dashboard.
- **Data layer:** Firebase Firestore for anonymized reports; no direct Firestore access from the frontend in MVP.
- **Frontend (Next.js):** One application for analytics only (replacing Looker Studio): KPIs, charts, a paginated list of recent reports, and in-dashboard alerts; all fed by the backend analytics API.
- **Alerts:** Automated alerts (e.g. spike in HIGH risk by county) run via backend job or scheduled check; delivery via email, webhook, or in-dashboard.
- **Integration layer:** The same API will be callable from n8n/Twilio for WhatsApp workflows; no custom WhatsApp backend in MVP.

**Data flow (simplified):**

- **Text verification:** Client → POST /api/v1/verify/text → Lexicon → Detoxify → Gemini (context + translation) → (optional: explainability model, Kenyan classifier) → Risk level + messages → Save report to Firestore → Return response.
- **Media verification:** Client → POST /api/v1/verify/media → Media ingestion (image/video/audio) → Placeholder or optional models (e.g. Gemini Vision, deepfake/misinformation detection) → Risk level + messages → Save report to Firestore → Return response.
- **Analytics:** Next.js dashboard → GET /api/v1/analytics/* → FastAPI aggregates from Firestore → Returns JSON → Dashboard renders charts and tables (text and media reports combined).

### 2.2 Technology Choices

| Layer | Choice | Rationale |
|-------|--------|-----------|
| API | FastAPI (Python 3.10+) | Async support, automatic OpenAPI docs, strong typing with Pydantic. |
| Toxicity (text) | Detoxify (multilingual) | Off-the-shelf multilingual toxicity model; reduces custom ML work for MVP. |
| Context & translation | Google Gemini | Single API for Kenyan-context analysis and Swahili/Sheng translation. |
| Lexicon | Custom Python module | Kenya-specific political keywords and risk levels; full control and auditability. |
| Explainability | Phi-3 mini / Gemma 2B / SmolLM2 / Qwen2-0.5B, or structured Gemini | Second model (or dedicated Gemini call) to generate short moderator-facing "why flagged" explanations. |
| Kenyan risk classifier | Fine-tuned DistilBERT / XLM-Roberta / AfricaBERT, or TF-IDF + Logistic Regression | Custom/fine-tuned model on Kenyan political text; extra vote in pipeline; strengthens domain specificity. |
| Media analysis | Placeholder (MVP) + optional: Gemini Vision, deepfake/misinformation models | MVP: media endpoint with placeholder or simple heuristic; optional: vision LLM for image/video caption + risk, or dedicated deepfake/misinformation detection models for real media verification. |
| Database | Firebase Firestore | Anonymized logging, scalable, and familiar for many incubation teams. |
| Dashboard | Next.js (TypeScript, App Router) | Single codebase for analytics UI; easy to export to PDF or share; no dependency on Looker Studio. |
| Charts | Recharts or Tremor | Lightweight, React-friendly, good for KPIs and time series in the dashboard. |

### 2.3 Key Technical Decisions

- **Lexicon-first:** High-risk lexicon matches immediately set risk to HIGH and can bypass heavy model calls for known harmful phrases.
- **Lazy loading:** Detoxify model is loaded on first use to avoid startup failures and to improve cold-start behavior.
- **Anonymization:** Only a hash of the sender identifier is stored; no raw PII in reports.
- **Analytics via API:** Dashboard does not talk to Firestore directly; all analytics go through FastAPI for security, consistency, and future auth/rate-limiting.
- **Text and media as first-class options:** Both `/verify/text` and `/verify/media` are supported; reports from either path use the same schema and analytics, so the dashboard can show combined or filtered views (e.g. by content type).

---

## 3. Development Milestones

We will develop the MVP in twelve milestones.

| Milestone | Name | Description |
|-----------|------|-------------|
| **M1** | Foundation and environment | Project repo, Python env, FastAPI app shell, health check, request/response models. |
| **M2** | Lexicon and core analysis | Kenya-specific lexicon module and text analyzer using lexicon only; POST /verify/text returns risk and English messages. |
| **M3** | Toxicity and risk mapping | Detoxify integration, score-to-risk mapping, combined lexicon + toxicity logic, fallbacks when the model is unavailable. |
| **M4** | Gemini integration | Gemini client, Swahili/Sheng translation, Kenyan-context check that can upgrade risk to HIGH. |
| **M5** | Firebase and reporting | Firestore setup, save_report and read helpers, report_id in API response; every verification logged anonymously. |
| **M6** | Analytics API | Backend aggregation (by risk, county, date) and analytics endpoints for summary, by-county, by-date, and recent reports. |
| **M7** | Media verification (option alongside text) | POST /verify/media with validation and report logging; MVP ships with placeholder or optional real analysis (e.g. Gemini Vision for images/video); deepfake/misinformation models optional in or post-MVP. |
| **M8** | Next.js analytics dashboard | Next.js app, API client, overview page (KPIs + charts), reports table, filters; dashboard replaces Looker Studio for MVP. |
| **M9** | Integration and production readiness | n8n/Twilio request/response docs and example workflow, Dockerfile, security notes, README and troubleshooting. |
| **M10** | Explainability ("Why was this flagged?") | Second model (e.g. Phi-3 mini, Gemma 2B, or SmolLM2) or structured Gemini call to generate a short moderator-facing explanation; new field in response and reports. |
| **M11** | Fine-tuned Kenyan risk classifier | Small fine-tuned or custom classifier (e.g. DistilBERT/XLM-R + labels from Firestore/public data); integrated as extra vote in pipeline; new fields in response and reports. |
| **M12** | Automated alerts | Alerts (e.g. spike in HIGH risk by county) configurable and delivered via email, webhook, or in-dashboard; backend job or scheduled check against analytics; threshold and county filters. |

---

## 4. Timeline

We assume a **15-week** MVP timeline.

| Week | Milestone(s) | Focus |
|------|-----------------------|--------|
| 1 | M1 | Repo, env, FastAPI shell, models. |
| 2 | M2 | Lexicon module, analyzer, /verify/text (lexicon-only). |
| 3 | M3 | Detoxify, risk mapping, combined pipeline. |
| 4 | M4 | Gemini init, translation, context check. |
| 5 | M5 | Firebase, save_report, report_id, get_report/get_recent_reports. |
| 6 | M6 | Analytics aggregation and API endpoints. |
| 6–7 | M7 | Media verification endpoint (placeholder or optional real analysis) and docs. |
| 7–9 | M8 | Next.js app, overview, charts, reports table, filters. |
| 10–11 | M9 | n8n/Twilio docs, Docker, security, README, runbook. |
| 12 | M10 | Explainability: second model or structured Gemini; moderator_explanation in API and Firestore; optional dashboard column. |
| 13 | M11 | Fine-tuned Kenyan risk classifier: data curation, training, integration in analyzer, ensemble rule, new report fields. |
| 14 | M12 | Automated alerts: threshold and county config, backend job or scheduled check, delivery (email, webhook, or in-dashboard). |
| 15 | Buffer and review | Integration testing, mentor review, and adjustments. |

**Dependencies:** M2 → M3 → M4 → M5; M6 and M8 depend on M5; M8 depends on M6. M10 and M11 can be developed in parallel after M5 (and ideally after M4); M11 may use report data from M5 for labeling. M12 depends on M6 (analytics) and optionally M8 (in-dashboard alerts).

---

## 5. Expected Deliverables

Deliverables are grouped by milestone.

### M1 – Foundation and environment

- Repository with `.gitignore`, `requirements.txt`, `env.template`.
- FastAPI application with `/health` and `/` and CORS configured.
- Pydantic models for verify-text and verify-media request/response.
- Brief run instructions in README.

### M2 – Lexicon and core analysis

- `utils/lexicon.py`: high/medium risk keyword lists, `check_lexicon()`, `get_keyword_context()`.
- `models/text_analyzer.py`: analyzer class using lexicon only; returns risk level and English message.
- Working `POST /api/v1/verify/text` returning risk and messages (no DB).

### M3 – Toxicity and risk mapping

- Detoxify (multilingual) integrated with lazy loading and error handling.
- Combined risk logic: lexicon first, then Detoxify score mapped to HIGH/MEDIUM/LOW.
- Consistent English response messages for all risk levels.

### M4 – Gemini integration

- Gemini client initialization (with fallback if key missing).
- `_translate_message()` used to produce Swahili and Sheng in the API response.
- `_check_kenyan_context()` used to upgrade risk to HIGH when appropriate.
- API response includes `messages.english`, `messages.swahili`, `messages.sheng`.

### M5 – Firebase and reporting

- Firestore initialized via service account; collection path documented.
- `utils/db.py`: `save_report()`, `get_report()`, `get_recent_reports()`, sender anonymization.
- Every successful verification stored; `report_id` returned in verify response.

### M6 – Analytics API

- Aggregation logic (by risk_level, county, time range).
- Endpoints: e.g. `/api/v1/analytics/summary`, `/api/v1/analytics/by-county`, `/api/v1/analytics/by-date`, `/api/v1/analytics/recent` (paginated).
- Optional: simple API auth for dashboard; documented in README.

### M7 – Media verification (option alongside text)

- `POST /api/v1/verify/media` with validation (media_url, media_type: image/video/audio, sender_id, county).
- MVP: placeholder risk response and report logging; optional: real analysis (e.g. Gemini Vision for caption + risk, or dedicated deepfake/misinformation models).
- Report saved to Firestore with media metadata (type, URL hash or storage ref); report_id returned; media reports included in analytics and dashboard.
- README and OpenAPI document text + media as two verification options; optional media models documented.

### M8 – Next.js analytics dashboard

- Next.js application (TypeScript, App Router) with env-based API base URL.
- API client calling analytics endpoints with typed responses.
- Overview page: KPI cards (totals, by risk, time window) and at least one chart (e.g. risk distribution or trend).
- Reports page: paginated table (timestamp, risk_level, county, matched_keyword; no PII).
- Optional: date range and risk level filters; CSV export.

### M9 – Integration and production readiness

- Documented request/response format for n8n/Twilio; example workflow (e.g. HTTP Request → IF → Twilio); prebunking_tip included in user-facing replies.
- Dockerfile for the FastAPI service; optional docker-compose.
- README with install, env, run, test script, and troubleshooting (e.g. Detoxify cache, Firebase 404, Gemini errors).
- Security notes: no secrets in repo, CORS, Firestore rules.

### M10 – Explainability ("Why was this flagged?")

- **Objective:** Add a short, moderator-facing explanation for HIGH/MEDIUM risk.
- Second model (e.g. Phi-3 mini, Gemma 2B, SmolLM2, or Qwen2-0.5B) via local inference (Ollama/llama.cpp) or a single inference API, **or** a dedicated structured Gemini call (strict prompt + JSON output) for explanation only.
- Prompt: given text + scores + matched_keyword, output one short sentence explaining why the content was flagged (factual, neutral).
- New field in `/api/v1/verify/text` response (e.g. `moderator_explanation`).
- Same field stored in Firestore reports; optional column in Next.js reports table.
- **Deliverables:** Explanation step in analyzer, updated response model and DB schema, optional dashboard update.

### M11 – Fine-tuned Kenyan risk classifier

- **Objective:** Integrate a custom/fine-tuned model as an extra signal to strengthen Kenyan-domain specificity.
- Data: labeled (text, risk_level) from Firestore reports (after light manual review) and/or public Kenyan political speech examples (e.g. 100–500+ examples).
- Model: fine-tuned small transformer (e.g. DistilBERT-multilingual, XLM-Roberta-base, or AfricaBERT if available) for 2- or 3-class risk; or a lightweight alternative (e.g. TF-IDF + Logistic Regression) framed as custom Kenyan risk model.
- Integration: run classifier in `text_analyzer.py` after lexicon and Detoxify; ensemble rule (e.g. lexicon HIGH OR Detoxify HIGH OR Kenyan classifier HIGH → final HIGH).
- New report fields (e.g. `custom_risk_score`, `kenyan_model_risk`); optional dashboard metric "flagged by Kenyan model."
- **Deliverables:** Trained model artifact (or Hugging Face repo), integration in analyzer, updated API response and Firestore schema, optional dashboard metric.

### M12 – Automated alerts

- **Objective:** Notify moderators when risk patterns exceed configurable thresholds (e.g. spike in HIGH risk by county).
- Backend: scheduled job or trigger that queries analytics (by county, time window) and compares to thresholds; optional persistence of alert config (e.g. Firestore or env).
- Delivery: email, webhook, and/or in-dashboard notification (e.g. banner or alerts panel in Next.js).
- Configurable: threshold (e.g. N HIGH reports in last H hours), county filter, optional risk-level filter.
- **Deliverables:** Alert logic and config, at least one delivery channel (email, webhook, or in-dashboard), README section on configuring alerts.

---

## 6. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Detoxify model download or load failures | Lazy load; document cache-clear steps; fallback to medium risk when model unavailable. |
| Gemini quota or latency | Graceful degradation (e.g. English-only messages, skip context check); optional caching later. |
| Firestore costs or limits | Use indexed queries and limit result set sizes; monitor usage. |
| Dashboard and API out of sync | Single analytics API contract; typed client in Next.js; versioned API path (/api/v1/). |
| Explainability model latency or unavailability | Optional field; fallback to empty or "See scores and matched_keyword"; timeouts. |
| Kenyan classifier data quality or size | Start with lexicon + Detoxify labels; augment with public examples; human review a sample. |
| Media analysis latency or model availability | Media endpoint works with placeholder; optional models (Gemini Vision, deepfake detection) are best-effort with fallback to placeholder or manual review. |

---

## 7. Post-MVP (Out of Scope for This Roadmap)

- Full media/deepfake detection pipeline (if MVP ships with media placeholder only).
- Looker Studio or other BI tools (optional later; Next.js is the MVP analytics surface).
- Public-facing user flows beyond API and dashboard.
- Contextual prebunking with claim extraction (optional future enhancement).

---

## 8. Document Control

- **Prepared for:** [Incubation program name]  
- **Reviewers:** Moderators and mentors  
- **Next review:** As agreed with program timeline  
- **Contact:** [Your team contact]  
