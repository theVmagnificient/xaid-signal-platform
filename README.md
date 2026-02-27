# xAID Signal Radar

**Lead signal monitoring platform for xAID.ai** — automatically tracks when to reach out to radiology companies.

## What it does

Monitors 9,500+ radiology companies in the Prereads US pipeline and surfaces three types of outreach signals:

| Signal | Example | Score |
|--------|---------|-------|
| 🔄 **Job Change** | New Head of Radiology joins MediCore Imaging | 10 |
| 💼 **Job Posting** | RadiologyPartners posts Body Radiologist opening | 10 |
| 📰 **AI News** | Regional Imaging adopts Aidoc AI | 9 |

## Stack

| Layer | Tech |
|-------|------|
| Database | [Supabase](https://supabase.com) (PostgreSQL) |
| Backend | Python + FastAPI |
| Frontend | Next.js 14 + Tailwind CSS |
| Signal sources | Google News RSS (free) + TheirStack + Exa.ai |
| Scheduler | GitHub Actions (daily cron) |
| Deployment | Vercel (frontend) + Railway (backend) |

## Quick Start

### 1. Set up Supabase

1. Create a project at [supabase.com](https://supabase.com)
2. Run `supabase/migrations/001_initial.sql` in the SQL editor
3. Copy your project URL and service role key

### 2. Backend

```bash
cd backend
cp .env.example .env
# Fill in SUPABASE_URL and SUPABASE_SERVICE_KEY

pip install -r requirements.txt

# Import leads from xlsx
python scripts/import_leads.py \
  --deals "../Exported Deals.xlsx" \
  --people "../Exported People.xlsx"

# Start API
uvicorn app.main:app --reload
```

### 3. Frontend

```bash
cd frontend
cp .env.local.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000

npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### 4. Run signals manually

```bash
cd backend
python scripts/run_signals.py --type full
```

## API Keys (optional, add as needed)

| Service | Used for | Cost | Get key |
|---------|----------|------|---------|
| TheirStack | Job posting signals | $59/mo | [theirstack.com](https://theirstack.com) |
| Exa.ai | Semantic news search | $50/mo or free tier | [exa.ai](https://exa.ai) |
| Apollo.io | Job change enrichment | Free tier available | [apollo.io](https://apollo.io) |

Google News RSS works out of the box with no API key.

## Signal Scoring

### Job Changes
| Title | Score |
|-------|-------|
| Head of Radiology, CMO, CTO, COO, Radiology Chair | 10 |
| CEO, CFO, VP of Operations, Practice Manager | 7 |

### Job Postings
| Title | Score |
|-------|-------|
| Body Radiologist, CT Radiologist, Cross-Sectional, Neuroradiologist | 10 |
| Diagnostic Radiologist, Staff Radiologist, Teleradiologist | 7 |

### News
| Category | Score |
|----------|-------|
| AI vendor adoption (Aidoc, Gleamer, Nuance) | 9 |
| PACS upgrade/migration | 8 |
| General tech adoption | 6 |

## Deployment

### Vercel (frontend)
```bash
cd frontend
npx vercel --prod
```
Set env var: `NEXT_PUBLIC_API_URL=https://your-railway-backend.railway.app`

### Railway (backend)
1. Connect GitHub repo
2. Set root directory to `backend/`
3. Add env vars from `.env.example`

### GitHub Actions (daily cron)
Add these secrets to your repo:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `THEIRSTACK_API_KEY` (optional)
- `EXA_API_KEY` (optional)
- `RAILWAY_TOKEN` (for auto-deploy)
- `VERCEL_TOKEN` (for auto-deploy)

## Pipedrive Sync

When the Pipedrive API token rate limit resets, sync directly:
```bash
# Coming: pipedrive live sync
POST /api/sync/pipedrive
```

Currently works via xlsx export from Pipedrive → import script.
