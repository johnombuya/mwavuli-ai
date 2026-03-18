# Project Mwavuli - Content Verification & Analytics Platform

A full-stack content verification system designed for detecting harmful information in the Kenyan political context. This system combines lexicon-based keyword detection, AI-powered toxicity analysis, and contextual understanding to identify potentially harmful content during election periods.

## Architecture

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
┌──────▼─────────────────────────────────────┐
│  Next.js Frontend (Port 3000)              │
│  - Mwavuli Intelligence Dashboard          │
│  - Briefing Room / Analyst View            │
│  - Verify page (text + image/audio/video)  │
│  - API rewrites → Backend                   │
└──────┬─────────────────────────────────────┘
       │
┌──────▼─────────────────────────────────────┐
│  FastAPI Backend (Port 8000)                │
│  - Text & media verification               │
│  - Analytics API & export                  │
│  - API key auth (optional; bypass in dev)  │
└──────┬─────────────────────────────────────┘
       │
┌──────▼─────────────────────────────────────┐
│  Supabase (PostgreSQL) or Firebase         │
│  - reports, report_aggregates              │
│  - media_hashes (dedup cache)              │
└────────────────────────────────────────────┘
```

## Features

### Backend
- **Text verification**: Lexicon, Detoxify, Kenyan classifier, Gemini/Ollama context check; auto sector/county detection
- **Media verification**: Images (OCR → text ensemble, Gemini/Ollama Vision), audio (Whisper → text ensemble), video (keyframes + audio via FFmpeg); hash-based dedup cache (`media_hashes` table)
- **Multi-language responses**: English, Swahili, Sheng
- **Database**: Supabase (PostgreSQL) or Firebase; reports and daily aggregates; run migrations in `backend/migrations/` (001–005)
- **Analytics API**: Summary, risk distribution, keyword/token trends, county analysis, executive summary, topic clusters, lexicon suggestions
- **API security**: Optional API keys; set `AUTH_DISABLED=true` in development to bypass
- **Webhooks**: Twilio (WhatsApp text + media), Africa's Talking SMS
- **Data export**: CSV/JSON/STIX

### Frontend
- **Mwavuli Intelligence Dashboard**: Briefing Room (executive summary, Kenya map, top threats) and Analyst View (charts)
- **Verify page**: Text paste; image/audio/video upload (drag-and-drop or URL)
- **Charts**: Risk distribution, keyword trends, toxicity trends, hourly patterns, county heatmap, detection-risk matrix
- **Responsive layout**: Desktop and mobile

## Quick Start with Docker Compose

The easiest way to run the entire application:

```bash
# Start both backend and frontend
docker-compose up

# Or run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

The application will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Manual Setup

### Prerequisites

- Python 3.10+ (tested with Python 3.11+)
- Node.js 20+ and npm
- **Database**: Supabase project (recommended) or Firebase with Firestore
- Google Gemini API key
- Optional (for local AI and full media verification):
  - **Ollama** for running a local LLM (and optionally a vision model) — see [backend README](backend/README.md#local-llm-ollama-optional)
  - **Tesseract OCR** and **FFmpeg** — see [backend README](backend/README.md#system-dependencies-optional--for-media-verification-and-local-ai)

### Backend Setup

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Create virtual environment**:
   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate
   
   # Linux/Mac
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Database**: Use **Supabase** (default) or Firebase.
   - **Supabase**: Create a project at [supabase.com](https://supabase.com). In **Settings → API** copy the project URL and service_role key. Run all migrations in order in the SQL Editor: `backend/migrations/001_initial_schema.sql` through `005_add_media_hashes.sql`.
   - **Firebase**: Enable Firestore, create a service account, download the JSON key. See `backend/.env.example` for `FIREBASE_SERVICE_ACCOUNT_PATH` and `FIREBASE_DATABASE_ID`.

5. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env: DB_PROVIDER=supabase (or firebase), SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY,
   # GEMINI_API_KEY; optionally API_KEYS, AUTH_DISABLED=true for dev.
   ```

6. **Run backend**:
   ```bash
   uvicorn app.main:app --reload
   ```

### Frontend Setup

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env.local
   # Set NEXT_PUBLIC_BACKEND_URL=http://localhost:8000 (or your backend URL)
   # Optional: NEXT_PUBLIC_API_KEY for backend API key auth
   ```

4. **Run frontend**:
   ```bash
   npm run dev
   ```

## Project Structure

```
niru_mwavuli/
├── backend/                    # FastAPI backend
│   ├── app/main.py            # FastAPI app, routes, webhooks
│   ├── models/
│   │   ├── text_analyzer.py   # MwavuliAnalyzer (lexicon, Detoxify, Gemini/Ollama)
│   │   └── media_analyzer.py  # Image/audio/video verification (OCR, Vision, Whisper, FFmpeg)
│   ├── utils/
│   │   ├── db.py              # save_report, get_repository
│   │   ├── db_supabase.py     # Supabase implementation
│   │   ├── db_firebase.py     # Firebase implementation (optional)
│   │   ├── analytics.py       # Analytics and executive summary
│   │   ├── lexicon.py         # Kenya-specific keywords
│   │   └── export.py          # CSV/JSON/STIX export
│   ├── migrations/            # SQL migrations (run 001–005 on Supabase)
│   ├── docs/                  # Backend documentation
│   ├── scripts/               # Seed, backfill, ingestion, tests
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
├── frontend/                   # Next.js frontend
│   ├── src/app/
│   │   ├── page.tsx           # Dashboard (Briefing Room / Analyst View)
│   │   ├── verify/page.tsx    # Verify text + image/audio/video
│   │   ├── layout.tsx
│   │   └── globals.css
│   ├── src/components/
│   │   ├── dashboard/         # Charts, Kenya map, executive summary, etc.
│   │   ├── charts/
│   │   └── ui/
│   ├── src/lib/
│   │   ├── api.ts             # API client (verify, analytics)
│   │   └── translations.ts   # EN/SW/Sheng
│   ├── .env.example           # NEXT_PUBLIC_BACKEND_URL, NEXT_PUBLIC_API_KEY
│   ├── next.config.js         # API rewrites
│   └── README.md
│
├── docker-compose.yml
├── TECHNICAL_ROADMAP.md
└── README.md
```

## API Endpoints

### Verification

- `POST /api/v1/verify/text` - Verify text content
- `POST /api/v1/verify/media` - Verify media by URL (image/audio/video)
- `POST /api/v1/verify/media/upload` - Verify uploaded file (multipart; image/audio/video)

### Reports & Appeals

- `PATCH /api/v1/reports/{report_id}` - Update report status (pending/reviewed/escalated)
- `POST /api/v1/reports/{report_id}/appeal` - Submit appeal
- `GET /api/v1/reports/appeals` - List appeals (filter by status, report_id)
- `POST /api/v1/reports/appeals/{appeal_id}/resolve` - Resolve appeal (upheld/overturned)

### Analytics

All analytics endpoints accept optional `sector` and `org_id` query parameters.

- `GET /api/v1/analytics/summary` - Overall statistics
- `GET /api/v1/analytics/risk-distribution` - Risk level breakdown
- `GET /api/v1/analytics/county-analysis` - County-level analysis
- `GET /api/v1/analytics/keyword-trends` - Top keywords
- `GET /api/v1/analytics/toxicity-trends` - Toxicity over time
- `GET /api/v1/analytics/hourly-patterns` - Hour-based patterns
- `GET /api/v1/analytics/daily-patterns` - Day-of-week patterns
- `GET /api/v1/analytics/detection-comparison` - Lexicon vs Gemini
- `GET /api/v1/analytics/geographic-heatmap` - County risk map
- `GET /api/v1/analytics/national-risk-level` - Traffic-light risk indicator
- `GET /api/v1/analytics/daily-summary` - Natural language 24 h summary
- `GET /api/v1/analytics/coordinated-campaigns` - Flagged coordinated activity

### Admin

- `GET /api/v1/admin/emergency-mode` - Check emergency mode status
- `POST /api/v1/admin/emergency-mode` - Toggle emergency mode

### Export

- `GET /api/v1/export/reports` - Export raw reports (CSV/JSON)
- `GET /api/v1/export/analytics` - Export aggregated analytics
- `GET /api/v1/export/stix` - Export HIGH-risk reports as STIX 2.1 bundle
- `GET /api/v1/export/looker-studio` - Optimized export for Looker Studio

### System

- `GET /health` - Basic health check
- `GET /api/v1/health` - Enhanced health check with service status
- `GET /docs` - Interactive API documentation

## Development

### Running Services Separately

**Backend**:
```bash
cd backend
uvicorn app.main:app --reload
```

**Frontend**:
```bash
cd frontend
npm run dev
```

### Testing

**Backend API Tests**:
```bash
cd backend
bash scripts/test_api.sh
bash scripts/test_analytics.sh
```

**Frontend**:
```bash
cd frontend
npm run lint
```

## Production Deployment

### Docker Compose (Recommended)

1. **Build images**:
   ```bash
   docker-compose build
   ```

2. **Run in production mode**:
   ```bash
   docker-compose up -d
   ```

3. **Update frontend Dockerfile** for production:
   ```dockerfile
   # In frontend/Dockerfile, change CMD to:
   RUN npm run build
   CMD ["npm", "start"]
   ```

### Environment Variables

**Backend** (`backend/.env`):
```env
FIREBASE_SERVICE_ACCOUNT_PATH=./firebase-service-account.json
FIREBASE_DATABASE_ID=mwavuli-nira-db
GEMINI_API_KEY=your_key_here
FRONTEND_URL=https://your-frontend-domain.com
# Optional: see backend/.env.example for INGESTION_* and ALERT_* settings
```

**Frontend** (`frontend/.env.local`):
```env
NEXT_PUBLIC_BACKEND_URL=http://backend:8000  # or https://api.your-domain.com
NEXT_PUBLIC_API_KEY=  # optional; match backend API_KEYS
```

## Troubleshooting

### Backend Issues

**Model Loading Error**: Clear Detoxify cache:
```bash
# Windows
Remove-Item -Recurse -Force "$env:USERPROFILE\.cache\torch\hub\*"

# Linux/Mac
rm -rf ~/.cache/torch/hub/*
```

**Firebase Database Error**: Ensure `FIREBASE_DATABASE_ID` matches your Firestore database ID.

### Frontend Issues

**API Connection Error**: 
- Check `NEXT_PUBLIC_BACKEND_URL` in `frontend/.env.local`
- Verify backend is running on port 8000
- Check browser console for CORS or 401 errors (set `AUTH_DISABLED=true` or `NEXT_PUBLIC_API_KEY` in dev)

**Build Errors**:
```bash
cd frontend
rm -rf node_modules .next
npm install
npm run build
```

### Docker Issues

**Port Conflicts**: Edit `docker-compose.yml` to change ports:
```yaml
ports:
  - "8001:8000"  # Backend on 8001
  - "3001:3000"  # Frontend on 3001
```

**Volume Mount Issues**: Ensure file permissions are correct.

## Operations / Runbook

### Database migrations (Supabase)

Run migrations in order in the Supabase SQL Editor: `backend/migrations/001_initial_schema.sql` through `005_add_media_hashes.sql`. After schema changes, optionally run `python scripts/backfill_aggregates.py` to recompute daily aggregates, and `python scripts/backfill_sector_county.py` to backfill sector/county on existing reports.

### Purge expired reports

Data retention is controlled by `DATA_RETENTION_DAYS` (default 365). Run the purge script periodically (e.g. weekly via cron):

```bash
cd backend
python scripts/purge_expired_reports.py          # delete expired reports
python scripts/purge_expired_reports.py --dry-run # preview only
```

### Early warning alerts

The alert script checks the last 24 hours of HIGH-risk reports against `ALERT_HIGH_RISK_THRESHOLD` and POSTs to `ALERT_WEBHOOK_URL`:

```bash
cd backend
python scripts/run_alerts.py   # suggest running every 15 min via cron
```

### Emergency mode

Toggle at runtime (requires admin API key):

```bash
# Enable
curl -X POST "https://your-host/api/v1/admin/emergency-mode?enable=true" -H "X-API-Key: YOUR_ADMIN_KEY"

# Disable
curl -X POST "https://your-host/api/v1/admin/emergency-mode?enable=false" -H "X-API-Key: YOUR_ADMIN_KEY"
```

When active, alert thresholds are halved and the dashboard refreshes every 30 seconds with a prominent red banner.

### Media verification

Full pipeline: images (Tesseract OCR → text ensemble, then Gemini/Ollama Vision), audio (Whisper → text ensemble), video (FFmpeg keyframes + audio). Use `POST /api/v1/verify/media/upload` for file uploads; dedup via `media_hashes` table. Install Tesseract and FFmpeg for full support (see [backend README](backend/README.md)).

### Bias testing

Run the ethnic-balance bias test framework:

```bash
cd backend
python scripts/bias_test.py
```

## Security Notes

- **Never commit** `.env`, `.env.local`, `firebase-service-account.json`, or Supabase service role key to git
- Set `SENDER_HASH_SALT` to a long random string in production
- Set `API_KEYS` and `API_KEY_ROLES` to restrict API access; use `AUTH_DISABLED=true` only in development
- Configure `FRONTEND_URL` for CORS in production
- Rotate database and Gemini credentials if accidentally exposed
- Use environment variables for all sensitive data in production

## Documentation

- [Backend README](backend/README.md) — setup, env vars, migrations, scripts
- [Analytics API](backend/docs/ANALYTICS.md)
- [Twilio WhatsApp](backend/docs/TWILIO_WHATSAPP.md) — webhook + media attachments
- [Looker Studio Setup](backend/docs/LOOKER_STUDIO_SETUP.md)
- [Firestore Indexes](backend/docs/FIRESTORE_INDEXES.md) (when using Firebase)
- [Technical Roadmap](TECHNICAL_ROADMAP.md)

## License

[Add your license here]

## Support

For issues and questions:
- Open an issue on GitHub
- Contact the development team

## Acknowledgments

- Detoxify for toxicity detection
- Google Gemini for translation and context analysis
- Firebase for data storage
- FastAPI for the web framework
- Next.js for the frontend framework
- Recharts for data visualization
