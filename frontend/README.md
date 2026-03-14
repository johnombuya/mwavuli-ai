# Project Mwavuli – Frontend

Next.js analytics dashboard for the Mwavuli content verification platform. Displays risk distribution, keyword trends, toxicity trends, hourly patterns, and county-level analysis. Data is fetched from the backend analytics API with optional date range filtering.

## Features

- **Mwavuli Intelligence Dashboard**: Briefing Room (executive summary, Kenya map, top threats) and Analyst View (charts)
- **Verify page** (`/verify`): Text paste; image/audio/video upload (drag-and-drop or URL)
- **Summary cards**: Total reports, risk distribution (HIGH/MEDIUM/LOW), date range
- **Charts**: Risk distribution, keyword trends, toxicity trends, hourly patterns, county heatmap, detection-risk matrix
- **Auto-refresh**: Configurable polling for live updates
- **Responsive layout**: Desktop and mobile

## Prerequisites

- Node.js 20+ and npm
- Backend API running (default: http://localhost:8000)

## Setup

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Environment variables

Copy `frontend/.env.example` to `.env.local` and set:

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_BACKEND_URL` | Backend API base URL (for rewrites and API client) | `http://localhost:8000` |
| `NEXT_PUBLIC_API_KEY` | Optional API key for backend auth (when API_KEYS is set) | *(empty)* |

Example:

```bash
cp .env.example .env.local
# Edit: NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
# Optional: NEXT_PUBLIC_API_KEY=your_key (if backend uses API_KEYS)
```

For production, set `NEXT_PUBLIC_BACKEND_URL` to your public API URL.

## Commands

### Development server

```bash
npm run dev
```

- App: http://localhost:3000  
- API requests to `/api/*` are rewritten to `BACKEND_URL` (see `next.config.js`).

### Production build

```bash
npm run build
```

### Production server (after build)

```bash
npm start
```

Runs the production server (default port 3000). Use after `npm run build`.

### Lint

```bash
npm run lint
```

Runs Next.js ESLint.

## Run with Docker

```bash
docker build -t mwavuli-frontend .
docker run -p 3000:3000 -e NEXT_PUBLIC_BACKEND_URL=http://host.docker.internal:8000 mwavuli-frontend
```

Adjust `NEXT_PUBLIC_BACKEND_URL` if the backend runs elsewhere.

## Project structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx           # Dashboard (Briefing Room / Analyst View)
│   │   ├── verify/page.tsx   # Verify text + image/audio/video
│   │   ├── layout.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── dashboard/         # KenyaHotspotMap, ExecutiveSummary, charts, etc.
│   │   ├── charts/
│   │   └── ui/
│   ├── lib/
│   │   ├── api.ts             # API client (verify, analytics)
│   │   └── translations.ts   # EN/SW/Sheng
│   └── contexts/
├── .env.example               # NEXT_PUBLIC_BACKEND_URL, NEXT_PUBLIC_API_KEY
├── next.config.js             # API rewrites → NEXT_PUBLIC_BACKEND_URL
├── package.json
└── README.md
```

## API usage

The frontend calls the backend via Next.js rewrites and the API client in `src/lib/api.ts`:

- Requests to `/api/*` are rewritten to `{NEXT_PUBLIC_BACKEND_URL}/api/*`
- When `NEXT_PUBLIC_API_KEY` is set, the client sends `X-API-Key` for protected routes

## Troubleshooting

- **Blank or no data:** Ensure the backend is running at `NEXT_PUBLIC_BACKEND_URL` and that the database (Supabase/Firebase) has report data, or run some verify requests first.
- **401 on API calls:** Set `AUTH_DISABLED=true` in the backend or add `NEXT_PUBLIC_API_KEY` to match a key in the backend `API_KEYS`.
- **CORS errors:** Backend CORS uses `FRONTEND_URL`; ensure it matches your frontend origin.
- **Build errors:** Run `npm run lint` and fix any TypeScript/ESLint issues; ensure Node 20+.
