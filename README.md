# Demand Hunter MVP

Internal web console for: roots → keywords → SERP → competitor weakness → social evidence → MVP card → feedback.

## Run

```bash
cd demand-hunter/backend
uvicorn app.main:app --host 0.0.0.0 --port 8100

cd demand-hunter/frontend
npm install
NEXT_PUBLIC_API_URL=http://127.0.0.1:8100 npm run dev
```

Default SearXNG endpoint: `http://127.0.0.1:8080`. Configure via `POST /api/settings`.

## MVP coverage

- Dashboard
- Root Library
- Keyword Discovery/List/Detail
- SERP top 10 via SearXNG
- SERP gap tags
- Competitor weakness from SERP pages
- Reddit/HN social evidence via SearXNG site search
- Opportunity Cards with Action/Watch/Reject
- Review feedback writeback
- Run History
- Settings for SearXNG/Brave/Tavily/LLM keys
