# Project Mwavuli – Backend

FastAPI backend for the Mwavuli content verification and analytics platform. Handles text and media verification, analytics aggregation, and data export. Designed for the Kenyan political context with lexicon-based detection, AI toxicity analysis (Detoxify), and context-aware analysis (Google Gemini).

## Features

- **Text verification** (`POST /api/v1/verify/text`): Lexicon checks, Detoxify toxicity, Gemini context and translation (English, Swahili, Sheng)
- **Media verification** (`POST /api/v1/verify/media`): Placeholder or optional real analysis (e.g. Gemini Vision)
- **Analytics API**: Summary, by-county, by-date, recent reports (paginated)
- **Data export**: CSV/JSON export for external tools
- **Firebase Firestore**: Anonymized report logging

## Prerequisites

- Python 3.10+
- Firebase project with Firestore enabled
- Google Gemini API key
- (Optional) Twilio account for WhatsApp integration

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

### 3. Environment variables

Copy the example env file and set your values:

```bash
cp .env.example .env
```

Edit `.env`:

| Variable | Description |
|----------|-------------|
| `FIREBASE_SERVICE_ACCOUNT_PATH` | Path to your Firebase service account JSON (e.g. `./firebase-service-account.json`) |
| `FIREBASE_DATABASE_ID` | Firestore database ID (leave empty for default) |
| `GEMINI_API_KEY` | Google Gemini API key ([Google AI Studio](https://makersuite.google.com/app/apikey)) |
| `TWILIO_AUTH_TOKEN` | (Optional) Twilio auth token for WhatsApp |

Place your Firebase service account JSON in the backend folder (or path you set) and ensure it is listed in `.gitignore`.

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

## Project structure

```
backend/
├── app/
│   └── main.py          # FastAPI app, routes, lifespan
├── models/
│   └── text_analyzer.py  # MwavuliAnalyzer (lexicon, Detoxify, Gemini)
├── utils/
│   ├── db.py            # Firestore save_report, get_report, get_recent_reports
│   ├── analytics.py     # Analytics aggregation
│   ├── export.py        # CSV/JSON export
│   └── lexicon.py       # Kenya-specific keywords
├── scripts/
│   ├── seed_dummy_reports.py   # Seed Firestore with dummy reports for analytics testing
│   ├── test_api.sh
│   └── test_analytics.sh
├── docs/
│   ├── ANALYTICS.md
│   └── LOOKER_STUDIO_SETUP.md
├── requirements.txt
├── .env.example
├── Dockerfile
└── README.md
```

## API overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/verify/text` | Verify text content |
| POST | `/api/v1/verify/media` | Verify media (placeholder or real) |
| GET | `/api/v1/analytics/summary` | Summary stats (risk, date range) |
| GET | `/api/v1/analytics/by-county` | Counts by county |
| GET | `/api/v1/analytics/by-date` | Counts by date |
| GET | `/api/v1/analytics/recent` | Recent reports (paginated) |
| GET | `/api/v1/export/csv` | Export reports as CSV |
| GET | `/api/v1/export/json` | Export reports as JSON |

Full request/response details: http://localhost:8000/docs

## Troubleshooting

- **Detoxify model error:** Clear cache: `Remove-Item -Recurse -Force "$env:USERPROFILE\.cache\torch\hub\*"` (Windows) or `rm -rf ~/.cache/torch/hub/*` (Linux/macOS), then restart.
- **Firebase 404:** Ensure Firestore is enabled and `FIREBASE_DATABASE_ID` matches your database (or leave empty for default).
- **Gemini errors:** Check `GEMINI_API_KEY` and quota at [Google AI Studio](https://makersuite.google.com/app/apikey).
