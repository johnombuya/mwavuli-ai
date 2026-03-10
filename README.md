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
│  - Analytics Dashboard                     │
│  - Real-time Updates (2-min polling)      │
│  - API Rewrites → Backend                  │
└──────┬─────────────────────────────────────┘
       │
┌──────▼─────────────────────────────────────┐
│  FastAPI Backend (Port 8000)               │
│  - Content Verification                    │
│  - Analytics API                           │
│  - Data Export                             │
└──────┬─────────────────────────────────────┘
       │
┌──────▼──────┐
│  Firestore  │
└─────────────┘
```

## Features

### Backend
- **Lexicon-Based Detection**: Immediate flagging of high-risk Kenyan political keywords (e.g., "madoadoa", "kwekwe")
- **AI Toxicity Analysis**: Multilingual toxicity detection using Detoxify
- **Context-Aware Analysis**: Google Gemini integration for detecting subtle political incitement
- **Multi-Language Support**: Responses in English, Swahili, and Sheng
- **Firebase Integration**: Anonymized logging of reports for pattern analysis
- **Analytics API**: Comprehensive analytics endpoints for data analysis
- **Data Export**: CSV/JSON export for external tools

### Frontend
- **Real-time Dashboard**: Live analytics with 2-minute auto-refresh
- **Interactive Charts**: Risk distribution, keyword trends, toxicity trends, hourly patterns
- **County Analysis**: Geographic heatmap of risk levels by county
- **Date Range Filtering**: Filter analytics by date range
- **Responsive Design**: Works on desktop and mobile devices

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
- Firebase project with Firestore enabled
- Google Gemini API key

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

4. **Set up Firebase**:
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Create a new project or select existing project
   - Enable **Firestore Database**
   - Create a Service Account and download the JSON key file
   - Use `backend/firebase-service-account.example.json` as a template for the required fields
   - For local development, save it as `firebase-service-account.json` in the `backend/` directory and ensure it is listed in `.gitignore`
   - For staging/production, do **not** commit the JSON file; store it via your hosting provider’s secret manager or mount it as a file, and set `FIREBASE_SERVICE_ACCOUNT_PATH` in `backend/.env` to that path (e.g. `/secrets/firebase-service-account.json`)

5. **Configure environment variables**:
   ```bash
   # Copy template
   cp .env.example .env
   
   # Edit .env and fill in:
   FIREBASE_SERVICE_ACCOUNT_PATH=./firebase-service-account.json
   FIREBASE_DATABASE_ID=mwavuli-nira-db  # Leave empty for default
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

6. **Run backend**:
  
```bash
cd backend
source .venv/Scripts/activate
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
   # Copy template
   cp .env.local.example .env.local
   
   # Edit .env.local:
   BACKEND_URL=http://localhost:8000
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

4. **Run frontend**:
   ```bash
   npm run dev
   ```

## Project Structure

```
niru_mwavuli/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # FastAPI application
│   │   └── __init__.py
│   ├── models/
│   │   └── text_analyzer.py   # MwavuliAnalyzer class
│   ├── utils/
│   │   ├── db.py              # Firebase Firestore utility
│   │   ├── lexicon.py         # Kenya-specific keywords
│   │   ├── analytics.py       # Analytics functions
│   │   └── export.py          # Data export utilities
│   ├── docs/                  # Backend documentation
│   ├── scripts/               # Test scripts
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile            # Backend Docker image
│   └── .env                  # Backend environment variables
│
├── frontend/                   # Next.js frontend
│   ├── src/
│   │   ├── app/              # Next.js App Router
│   │   │   ├── layout.tsx    # Root layout with React Query
│   │   │   ├── page.tsx      # Dashboard home
│   │   │   └── globals.css   # Global styles
│   │   ├── components/       # React components
│   │   │   ├── dashboard/    # Dashboard components
│   │   │   ├── charts/       # Chart components
│   │   │   └── ui/           # UI components
│   │   ├── lib/              # Utilities
│   │   │   ├── api.ts        # API client
│   │   │   └── utils.ts      # Helper functions
│   │   └── types/            # TypeScript types
│   │       └── api.ts
│   ├── package.json          # Node dependencies
│   ├── next.config.js        # Next.js config with rewrites
│   ├── Dockerfile           # Frontend Docker image
│   └── .env.local           # Frontend environment variables
│
├── docker-compose.yml        # Docker Compose configuration
└── README.md                 # This file
```

## API Endpoints

### Verification

- `POST /api/v1/verify/text` - Verify text content
- `POST /api/v1/verify/media` - Verify media content (placeholder)

### Analytics

- `GET /api/v1/analytics/summary` - Overall statistics
- `GET /api/v1/analytics/risk-distribution` - Risk level breakdown
- `GET /api/v1/analytics/county-analysis` - County-level analysis
- `GET /api/v1/analytics/keyword-trends` - Top keywords
- `GET /api/v1/analytics/toxicity-trends` - Toxicity over time
- `GET /api/v1/analytics/hourly-patterns` - Hour-based patterns
- `GET /api/v1/analytics/daily-patterns` - Day-of-week patterns
- `GET /api/v1/analytics/detection-comparison` - Lexicon vs Gemini
- `GET /api/v1/analytics/geographic-heatmap` - County risk map

### Export

- `GET /api/v1/export/reports` - Export raw reports (CSV/JSON)
- `GET /api/v1/export/analytics` - Export aggregated analytics
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
source .venv/Scripts/activate
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
BACKEND_URL=http://backend:8000  # Docker service name
NEXT_PUBLIC_API_URL=https://api.your-domain.com  # Public API URL
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
- Check `BACKEND_URL` in `frontend/.env.local`
- Verify backend is running on port 8000
- Check browser console for CORS errors

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

## Security Notes

- **Never commit** `.env`, `.env.local`, or `firebase-service-account.json` to git
- Rotate Firebase credentials if accidentally exposed
- Keep API keys secure and rotate regularly
- Use environment variables for all sensitive data in production
- Configure CORS appropriately for production (update `ALLOWED_ORIGINS` in `backend/app/main.py`)

## Documentation

- [Analytics API Documentation](backend/docs/ANALYTICS.md)
- [Looker Studio Setup Guide](backend/docs/LOOKER_STUDIO_SETUP.md)

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
