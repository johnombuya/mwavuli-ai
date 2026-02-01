# Project Mwavuli – Frontend

Next.js analytics dashboard for the Mwavuli content verification platform. Displays risk distribution, keyword trends, toxicity trends, hourly patterns, and county-level analysis. Data is fetched from the backend analytics API with optional date range filtering.

## Features

- **Summary cards**: Total reports, risk distribution (HIGH/MEDIUM/LOW), date range
- **Charts**: Risk distribution, keyword trends, toxicity trends, hourly patterns
- **County heatmap**: Geographic view of risk levels by Kenyan county
- **Date range filter**: Filter analytics by start and end date
- **Auto-refresh**: Configurable polling (e.g. 2-minute) for live updates
- **Responsive layout**: Works on desktop and mobile

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

Create a `.env.local` file in the `frontend` folder (optional; defaults work for local dev):

| Variable | Description | Default |
|----------|-------------|---------|
| `BACKEND_URL` | Backend API base URL (used for `/api/*` rewrites) | `http://localhost:8000` |

Example:

```bash
# .env.local
BACKEND_URL=http://localhost:8000
```

For production or a different host, set `BACKEND_URL` to your backend URL (e.g. `https://api.yourdomain.com`).

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
docker run -p 3000:3000 -e BACKEND_URL=http://host.docker.internal:8000 mwavuli-frontend
```

Adjust `BACKEND_URL` if the backend runs elsewhere (e.g. another container or host).

## Project structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── globals.css
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   ├── charts/
│   │   │   ├── HourlyPatternsChart.tsx
│   │   │   ├── KeywordTrendsChart.tsx
│   │   │   ├── RiskDistributionChart.tsx
│   │   │   └── ToxicityTrendsChart.tsx
│   │   ├── dashboard/
│   │   │   ├── CountyHeatmap.tsx
│   │   │   └── SummaryCards.tsx
│   │   └── ui/
│   │       ├── DateRangePicker.tsx
│   │       └── LoadingSpinner.tsx
│   └── types/
│       └── api.ts
├── next.config.js      # API rewrites → BACKEND_URL
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── README.md
```

## API usage

The frontend calls the backend via Next.js rewrites:

- Browser requests: `GET /api/v1/analytics/summary` (etc.)
- Next.js rewrites to: `{BACKEND_URL}/api/v1/analytics/summary`

So the app only needs to target `/api/...`; the backend URL is configured in `BACKEND_URL` and `next.config.js`.

## Troubleshooting

- **Blank or no data:** Ensure the backend is running at `BACKEND_URL` and that Firestore has report data (or run some verify requests first).
- **CORS errors:** Backend CORS is set to allow the frontend origin; if you use a different port or host, update backend CORS in `app/main.py`.
- **Build errors:** Run `npm run lint` and fix any TypeScript/ESLint issues; ensure Node 20+.
