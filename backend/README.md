# Project Mwavuli – Backend

FastAPI backend for the Mwavuli content verification and analytics platform. Handles text and media verification, analytics aggregation, and data export. Designed for the Kenyan political context with lexicon-based detection, AI toxicity analysis (Detoxify), and context-aware analysis (Google Gemini).

## Features

- **Text verification** (`POST /api/v1/verify/text`): Lexicon, Detoxify, Kenyan classifier, Gemini/Ollama context and translation; auto sector/county detection
- **Media verification** (`POST /api/v1/verify/media`, `POST /api/v1/verify/media/upload`): Images (OCR + Vision), audio (Whisper), video (FFmpeg keyframes + audio); hash dedup via `media_hashes` table
- **Analytics API**: Summary, risk distribution, keyword/token trends, county analysis, executive summary, topic clusters, lexicon suggestions
- **Database**: Supabase (PostgreSQL) or Firebase; reports and daily aggregates; run migrations 001–005
- **API security**: Optional API keys; `AUTH_DISABLED=true` in development to bypass
- **Webhooks**: Twilio (WhatsApp text + media), Africa's Talking SMS
- **Data export**: CSV/JSON/STIX

## Firestore usage and optimization contract

To keep Firestore usage predictable and affordable as Mwavuli grows, the backend follows these rules:

- **Canonical reports vs aggregates**
  - Raw, per-report data lives in `artifacts/mwavuli/public/data/reports` and is written only via `utils/db.save_report`.
  - Time‑bucketed analytics live in `artifacts/mwavuli/public/data/report_aggregates`, one document per `{date}-{sector}-{org_id}`.

- **Writes**
  - All ingestion and verification flows must call `save_report` (do not write to Firestore directly).
  - `save_report`:
    - Normalizes text and computes a `content_hash` if not provided.
    - Uses `report_exists_by_content_hash` / `report_exists_by_source_url` to skip duplicates.
    - Writes the canonical report and then updates the corresponding daily aggregate document in a transaction.

- **Reads for analytics and dashboards**
  - High‑level analytics in `utils/analytics.py` (risk distributions, keyword trends, summary stats, status counts, etc.) read from `report_aggregates` whenever possible instead of scanning raw `reports`.
  - API endpoints under `/api/v1/analytics/*` are the only supported way for the frontend to access analytics data; frontend code should never query Firestore directly.
  - Every analytics endpoint must:
    - Accept a bounded `(start_date, end_date)` and default to a conservative window when omitted.
    - Prefer aggregates and only fall back to raw `reports` for specialized or low‑volume queries (e.g. STIX export, token exploration).

- **Adding new analytics**
  - When a new metric is needed, do **not** add a new Firestore scan over `reports`.
  - Instead:
    1. Extend the `report_aggregates` document shape with the required counters/summaries.
    2. Update `save_report` to maintain those fields for each new report.
    3. Add a reader function in `utils/analytics.py` that computes the metric by combining aggregate documents.
    4. Expose it via a new or existing `/api/v1/analytics/*` endpoint.

- **Exports and heavy operations**
  - The export endpoints under `/api/v1/export/*` and the STIX export are **analyst/admin tools only**:
    - They require API keys with the appropriate role.
    - They enforce bounded `start_date`/`end_date` windows to avoid unintentional full-dataset scans.
  - Dashboards and automated jobs **must not** poll export endpoints; use the aggregate-backed analytics endpoints instead.

## Prerequisites

- Python 3.10+
- **Database**: Supabase project (recommended) or Firebase with Firestore enabled
- Google Gemini API key
- (Optional) Twilio account for WhatsApp; Tesseract and FFmpeg for full media verification

## Setup

### 1. Create virtual environment

```bash
cd backend
python -m venv .venv
```

**Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows (cmd):**
```cmd
.venv\Scripts\activate.bat
```

**Linux / macOS:**
```bash
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** The first time Detoxify runs, it downloads the multilingual model (~500MB) on the first API call.

#### System dependencies (optional — for media verification)

- **Tesseract OCR** — used for extracting text from images before calling the Vision LLM.
  - **Windows**: `choco install tesseract` or download from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki). Make sure the folder containing `tesseract.exe` is added to your `PATH`, then restart your terminal.
  - **Ubuntu/Debian**: `sudo apt update && sudo apt install -y tesseract-ocr`
  - **macOS** (Homebrew): `brew install tesseract`
- **FFmpeg** — used for extracting keyframes and audio from video files.
  - **Windows**: `choco install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org/download.html) and add the `bin` folder to your `PATH`.
  - **Ubuntu/Debian**: `sudo apt update && sudo apt install -y ffmpeg`
  - **macOS** (Homebrew): `brew install ffmpeg`

In containerised deployments (e.g. Docker), you can install both with:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    ffmpeg \
  && rm -rf /var/lib/apt/lists/*
```

If Tesseract is missing, the backend will log a non-fatal warning and skip OCR for images; if FFmpeg is missing, video keyframe/audio extraction will be skipped.

### 3. Database and migrations

- Set `DB_PROVIDER=supabase` (or `firebase`) in `.env`.
- **Supabase**: Set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`. Run all migrations in order in the Supabase SQL Editor: `migrations/001_initial_schema.sql` through `005_add_media_hashes.sql`. The `media_hashes` table is required for media dedup; without it the backend still runs but cache lookups will fail (non-fatal).
- **Firebase**: Set `FIREBASE_SERVICE_ACCOUNT_PATH` and optionally `FIREBASE_DATABASE_ID`. No SQL migrations; schema is document-based.

### 4. Environment variables

Copy the example env file and set your values:

```bash
cp .env.example .env
```

Edit `.env` and fill in the following:

**Core backend configuration**

| Variable | Required | Default / Example | Description |
|----------|----------|-------------------|-------------|
| `DB_PROVIDER` | No | `supabase` | `supabase` or `firebase`. |
| `SUPABASE_URL` | When Supabase | *(empty)* | Supabase project URL (Settings → API). |
| `SUPABASE_SERVICE_ROLE_KEY` | When Supabase | *(empty)* | Supabase service_role key (Settings → API). |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | When Firebase | `./firebase-service-account.json` | Path to Firebase service account JSON. |
| `FIREBASE_DATABASE_ID` | No | *(empty)* or `mwavuli-nira-db` | Firestore database ID; leave empty for default. |
| `GEMINI_API_KEY` | Yes | `your_gemini_api_key_here` | Google Gemini API key ([Google AI Studio](https://makersuite.google.com/app/apikey)). |
| `LLM_PROVIDER` | No | `auto` | `gemini`, `ollama`, or `auto` (try Gemini, fallback Ollama). |
| `OLLAMA_BASE_URL` | When using Ollama | `http://localhost:11434` | Ollama server URL. |
| `OLLAMA_MODEL` | No | `llama3` | Ollama model for text. |
| `OLLAMA_VISION_MODEL` | No | `llava` | Ollama vision model for images. |
| `AUTH_DISABLED` | No | `false` | Set `true` in development to skip API key checks. |
| `API_KEYS` | No | *(empty)* | Comma-separated API keys; empty = all requests allowed. |
| `API_KEY_ROLES` | No | *(empty)* | Optional key:role pairs (e.g. `key1:admin,key2:analyst`). |
| `TWILIO_ACCOUNT_SID` | No | *(empty)* | Twilio Account SID. See [Twilio WhatsApp](docs/TWILIO_WHATSAPP.md). |
| `TWILIO_AUTH_TOKEN` | No | *(empty)* | Twilio Auth Token. |
| `TWILIO_WHATSAPP_FROM` | No | `whatsapp:+14155238886` | Twilio WhatsApp number with `whatsapp:` prefix. |
| `HF_MODEL_REPO` | No | *(empty)* | HuggingFace repo for Kenyan classifier (e.g. `user/mwavuli-kenyan-classifier`). |
| `HF_TOKEN` | No | *(empty)* | HuggingFace token for private repos. |

**Web ingestion / auto-reports (optional)**

| Variable | Required | Default / Example | Description |
|----------|----------|-------------------|-------------|
| `INGESTION_ENABLED` | No | `false` | Kill switch for web ingestion. Set to `true` to enable ingestion. |
| `INGESTION_RSS_FEEDS` | No | *(empty)* | Comma-separated list of allowlisted RSS/Atom feed URLs. |
| `INGESTION_SCRAPE_DOMAINS` | No | *(empty)* | Comma-separated list of allowlisted domains for scraping (e.g. `example.com`). |
| `INGESTION_SCRAPE_SEED_URLS` | No | *(empty)* | Optional comma-separated list of seed URLs to scrape; each host must be in `INGESTION_SCRAPE_DOMAINS`. |
| `INGESTION_RATE_LIMIT_REQ_PER_MIN` | No | `30` | Max requests per minute across all sources. |
| `INGESTION_USER_AGENT` | No | `MwavuliElectionMonitor/1.0` | User-Agent string sent with ingestion requests. |
| `INGESTION_ELECTION_KEYWORDS` | No | *(empty)* | Optional comma-separated keywords; if set, only items containing at least one keyword are verified. |
| `INGESTION_JOB_ID` | No | *(empty)* | Optional run identifier for ingestion audit logs. |
| `INGESTION_ADMIN_ENABLED` | No | `false` | Enable `GET /api/v1/ingestion/status` admin status endpoint. |

**Alerts / early warning (optional)**

| Variable | Required | Default / Example | Description |
|----------|----------|-------------------|-------------|
| `ALERT_WEBHOOK_URL` | No | *(empty)* | If set, `run_alerts.py` POSTs a JSON payload here when high-risk counts exceed the threshold. |
| `ALERT_HIGH_RISK_THRESHOLD` | No | `10` | Number of HIGH-risk reports in the last 24h that will trigger an alert. |

Example `backend/.env` for local development (Supabase):

```env
DB_PROVIDER=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
GEMINI_API_KEY=your_gemini_api_key_here
AUTH_DISABLED=true
API_KEYS=

LLM_PROVIDER=auto
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_VISION_MODEL=llava

TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

INGESTION_ENABLED=false
ALERT_WEBHOOK_URL=
ALERT_HIGH_RISK_THRESHOLD=10
```

See `.env.example` for all options. When using Firebase, set `DB_PROVIDER=firebase`, `FIREBASE_SERVICE_ACCOUNT_PATH`, and optionally `FIREBASE_DATABASE_ID`. Do not commit `.env` or service account JSON to git.

## Commands

### Run development server

```bash
uvicorn app.main:app --reload
```

- API: http://localhost:8000  
- OpenAPI docs: http://localhost:8000/docs  
- Health: http://localhost:8000/health  

### Run production server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Run with Docker

```bash
docker build -t mwavuli-backend .
docker run -p 8000:8000 --env-file .env mwavuli-backend
```

## Testing

### Unit tests (ingestion)

From the `backend` directory (with venv activated and dependencies installed):

```bash
python -m unittest tests.test_ingestion -v
```

Tests cover URL normalisation, RSS parsing (if `feedparser` is installed), deduplication, and the pipeline with mocked fetcher/analyzer. Pipeline tests are skipped if `app.ingestion.pipeline` cannot be imported (e.g. missing dependencies). See [docs/FIRESTORE_INDEXES.md](docs/FIRESTORE_INDEXES.md) for Firestore index notes.

### Test script (Bash)

From the `backend` directory:

```bash
bash scripts/test_api.sh
```

Or from project root:

```bash
bash backend/scripts/test_api.sh
```

### Test analytics endpoints

```bash
bash scripts/test_analytics.sh
```

### Manual cURL examples

**Health check:**
```bash
curl http://localhost:8000/health
```

**Verify text (safe):**
```bash
curl -X POST http://localhost:8000/api/v1/verify/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, how are you?", "sender_id": "test123"}'
```

**Verify text (high-risk):**
```bash
curl -X POST http://localhost:8000/api/v1/verify/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Those madoadoa must leave", "sender_id": "test456", "county": "Nairobi"}'
```

## Seed dummy data

To populate Firestore with dummy reports for testing the analytics dashboard:

1. **Environment:** Ensure `backend/.env` has `FIREBASE_SERVICE_ACCOUNT_PATH` (path to your Firebase service account JSON). Optionally set `FIREBASE_DATABASE_ID` if using a non-default Firestore database.

2. **Activate venv** (from `backend/`):
   ```bash
   .\.venv\Scripts\Activate.ps1   # Windows PowerShell
   # or: source .venv/bin/activate  # Linux/macOS
   ```

3. **Dry run** (generate reports without writing to Firestore):
   ```bash
   python scripts/seed_dummy_reports.py --dry-run
   ```

4. **Seed Firestore** (default: 200 reports, last 30 days, mixed risk levels):
   ```bash
   python scripts/seed_dummy_reports.py
   ```

5. **Options:**
   - `--preset minimal|default|large` — 50, 200, or 1000 reports (default: `default`).
   - `--count N` — Override count for the random generator.
   - `--generator NAME` — Use specific generators (e.g. `random`, `election_spike`, `fixed_minimal`). Can be repeated.
   - `--dry-run` — Do not write to Firestore.

   Examples:
   ```bash
   python scripts/seed_dummy_reports.py --preset minimal
   python scripts/seed_dummy_reports.py --count 500
   python scripts/seed_dummy_reports.py --generator fixed_minimal --generator election_spike --dry-run
   ```

6. **Adding more dummy data later:** Edit `scripts/seed_dummy_reports.py`. Define a function that returns a list of report dicts (use `build_report(...)` for the correct shape), then register it in `REPORT_GENERATORS`. Run with `--generator your_name` or call it from `main()`.

## Web ingestion and auto-reports

The ingestion pipeline continuously fetches content from allowlisted RSS feeds and (optionally) allowlisted websites, deduplicates by URL and content hash, optionally filters by keywords, runs each item through the same verification pipeline as the API, and saves reports with `source_type`, `source_url`, and `created_by=system`. This keeps Mwavuli ahead of the curve without manual submission.

### Enabling ingestion

1. In `.env`, set `INGESTION_ENABLED=true`.
2. Configure allowlisted sources (only these are ever fetched):
   - `INGESTION_RSS_FEEDS` — Comma-separated RSS/Atom feed URLs.
   - `INGESTION_SCRAPE_DOMAINS` — Comma-separated domains allowed for scraping (e.g. `example.com`).
   - `INGESTION_SCRAPE_SEED_URLS` — (Optional) Comma-separated URLs to scrape; each URL’s host must be in `INGESTION_SCRAPE_DOMAINS`.
3. Optional: `INGESTION_ELECTION_KEYWORDS` — Comma-separated keywords; only items containing at least one keyword are verified (empty = verify all). `INGESTION_RATE_LIMIT_REQ_PER_MIN`, `INGESTION_USER_AGENT`, `INGESTION_JOB_ID`, `INGESTION_ADMIN_ENABLED` — see `.env.example`.

### Running the pipeline

From the `backend` directory (with venv activated):

```bash
python scripts/run_ingestion.py
```

This runs one cycle (fetch → dedupe → filter → verify → save) and prints counts.

### Scheduling with cron

To run every 30 minutes:

```cron
0,30 * * * * cd /path/to/backend && .venv/bin/python scripts/run_ingestion.py
```

Windows Task Scheduler or a similar cron equivalent can be used instead.

### Safety

- **Kill switch:** Set `INGESTION_ENABLED=false` (or leave unset) to disable all fetching and verification.
- **Allowlist:** Only URLs from `INGESTION_RSS_FEEDS` or hosts in `INGESTION_SCRAPE_DOMAINS` are fetched; no arbitrary URLs.
- **robots.txt:** The scraper checks and obeys robots.txt for each host.
- **Rate limiting:** Configurable `INGESTION_RATE_LIMIT_REQ_PER_MIN` and polite delays between requests.
- **User-Agent:** Set an identifiable `INGESTION_USER_AGENT` so site owners can contact you.
- **Circuit breaker:** A domain that returns repeated 4xx/5xx or timeouts is skipped for the rest of the run.
- **Audit log:** Each run writes to the `ingestion_audit` Firestore collection (`artifacts/mwavuli/public/data/ingestion_audit`) with action, URL, reason, and optional risk_level. Use it to see why items were skipped or stored.

### Ingestion status endpoint

If `INGESTION_ADMIN_ENABLED=true`, `GET /api/v1/ingestion/status` returns the last run summary (timestamp, job_id, counts). The run_ingestion script writes this after each cycle.

### High-risk review

Reports created by ingestion have `created_by=system` and optional `source_url`. In the dashboard you can filter for `risk_level=HIGH` and `created_by=system` to flag auto-created high-risk content for human review before any external use or escalation.

### Alerts / early warning

An optional job can notify moderators when HIGH risk reports in the last 24 hours exceed a threshold. Set `ALERT_WEBHOOK_URL` (and optionally `ALERT_HIGH_RISK_THRESHOLD`, default 10) in `.env`, then run:

```bash
python scripts/run_alerts.py
```

Schedule with cron (e.g. hourly): `0 * * * * cd /path/to/backend && python scripts/run_alerts.py`. On breach, the script POSTs a JSON payload to the webhook (event, timestamp, window_hours, high_risk_count, threshold, distribution).

### Firestore index (optional)

For deduplication, the pipeline queries reports by `source_url` and optionally by `content_hash`. Firestore allows single-field equality queries without a composite index. If you add more complex queries later, create the required indexes in the Firebase Console or via `firestore.indexes.json`.

## Project structure

```
backend/
├── app/
│   ├── main.py             # FastAPI app, routes, webhooks, lifespan
│   └── ingestion/           # Web ingestion pipeline
├── models/
│   ├── text_analyzer.py    # MwavuliAnalyzer (lexicon, Detoxify, Gemini/Ollama)
│   └── media_analyzer.py   # Image/audio/video (OCR, Vision, Whisper, FFmpeg)
├── utils/
│   ├── db.py               # save_report, get_repository
│   ├── db_base.py          # ReportRepository interface
│   ├── db_supabase.py      # Supabase implementation
│   ├── db_firebase.py      # Firebase implementation (optional)
│   ├── db_helpers.py       # enrich_report, aggregate helpers
│   ├── analytics.py        # Analytics, executive summary
│   ├── export.py           # CSV/JSON/STIX export
│   └── lexicon.py          # Kenya-specific keywords
├── migrations/             # SQL migrations (Supabase; run 001–005)
│   ├── 001_initial_schema.sql
│   ├── 002_add_embeddings.sql
│   ├── 003_add_clusters.sql
│   ├── 004_add_gemini_labels.sql
│   └── 005_add_media_hashes.sql
├── scripts/
│   ├── run_ingestion.py    # One ingestion cycle (cron)
│   ├── seed_dummy_reports.py
│   ├── backfill_aggregates.py   # Recompute report_aggregates
│   ├── backfill_sector_county.py # Backfill sector/county (Gemini/Ollama)
│   ├── backfill_embeddings.py   # Backfill embeddings for reports
│   ├── cluster_reports.py       # Topic clustering (HDBSCAN)
│   ├── test_api.sh
│   └── test_analytics.sh
├── docs/
│   ├── ANALYTICS.md
│   ├── TWILIO_WHATSAPP.md
│   ├── LOOKER_STUDIO_SETUP.md
│   └── FIRESTORE_INDEXES.md
├── requirements.txt
├── .env.example
├── Dockerfile
└── README.md
```

## API overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health`, `/api/v1/health` | Health check |
| POST | `/api/v1/verify/text` | Verify text content |
| POST | `/api/v1/verify/media` | Verify media by URL (image/audio/video) |
| POST | `/api/v1/verify/media/upload` | Verify uploaded file (multipart) |
| GET | `/api/v1/analytics/summary` | Summary stats |
| GET | `/api/v1/analytics/risk-distribution` | Risk breakdown |
| GET | `/api/v1/analytics/keyword-trends` | Top keywords |
| GET | `/api/v1/analytics/executive-summary` | AI-generated brief |
| GET | `/api/v1/analytics/recent` | Recent reports (paginated) |
| GET | `/api/v1/export/reports` | Export reports (CSV/JSON) |
| POST | `/api/v1/webhooks/twilio` | Twilio WhatsApp (text + media) |

Protected routes require `X-API-Key` when `API_KEYS` is set; use `AUTH_DISABLED=true` in development. Full details: http://localhost:8000/docs

## Scripts (optional)

- **backfill_aggregates.py** — Recompute `report_aggregates` from `reports` (run after bulk import or schema fix).
- **backfill_sector_county.py** — Backfill `sector` and `county` on existing reports using local matching and/or Gemini/Ollama (`--engine ollama`, `--skip-gemini`, etc.).
- **backfill_embeddings.py** — Compute and store embeddings for reports (for semantic coordination).
- **cluster_reports.py** — Run HDBSCAN clustering and write to `report_clusters` (for topic-cluster analytics).

## Troubleshooting

- **Detoxify model error:** Clear cache: `Remove-Item -Recurse -Force "$env:USERPROFILE\.cache\torch\hub\*"` (Windows) or `rm -rf ~/.cache/torch/hub/*` (Linux/macOS), then restart.
- **Supabase "table not found":** Run migrations 001–005 in the Supabase SQL Editor. If `media_hashes` is missing, media dedup is skipped (non-fatal).
- **Firebase 404:** Ensure Firestore is enabled and `FIREBASE_DATABASE_ID` matches your database (or leave empty for default).
- **Gemini errors:** Check `GEMINI_API_KEY` and quota at [Google AI Studio](https://makersuite.google.com/app/apikey).
- **401 on API calls:** Set `AUTH_DISABLED=true` in dev or send a valid `X-API-Key` from `API_KEYS`.
