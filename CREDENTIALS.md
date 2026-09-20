# Credentials — where each one goes

| # | Credential | Secret? | WHERE it goes | How |
|---|-----------|---------|---------------|-----|
| 1 | AWS Access Key ID + Secret | **YES** | `~/.aws/credentials` (**never** the repo) | `aws configure --profile travelpilot` |
| 2 | Bedrock: region + model id | No (config) | `backend/.env` | copy from `.env.example` |
| 2 | Bedrock: model ACCESS | grant | Bedrock console → Model access | request Claude access |
| 3 | RDS `DATABASE_URL` (DB password you pick) | yes | `backend/.env` (local) / App Runner env (prod) | you choose it when creating RDS |
| 4 | `ORS_API_KEY` | yes | `backend/.env` | free key from openrouteservice.org — ingestion (Phase 3) AND runtime map route geometry (cache-miss only) |

## The one rule
**The AWS access key (#1) must NOT live in the project directory** — not even in `.env`.
It authenticates Bedrock, RDS, App Runner, Lambda and S3 all at once, so a leak is total.
It belongs in `~/.aws/credentials`, created by `aws configure`. The repo's `.gitignore`
blocks `.env` and `.aws/`, but the safe habit is: keys → `~/.aws`, config → `.env`.

## Step 1 — AWS key (terminal, writes ~/.aws)
```
aws configure --profile travelpilot
```
Enter: Access Key ID, Secret Access Key, region `us-east-1`, output `json`.

## Step 2 — Bedrock config (project)
```
cd backend
copy .env.example .env        # Windows
```
`.env` already has `BEDROCK_MODEL_ID`, `AWS_REGION_NAME`, `AWS_PROFILE=travelpilot`.
Then in the Bedrock console → **Model access** → request the Claude model.

## Verify both
```
cd backend
.venv\Scripts\python.exe -m app.scripts.probe_bedrock
```
Expect "live Converse succeeded". Then flip `USE_MOCK_LLM=false` in `.env`.

## Where the code reads them
- The AWS key is read implicitly by boto3 from the `AWS_PROFILE` in `.env` → `~/.aws`.
- `backend/app/config.py` reads `.env` for region, model id, DB url, ORS key.
- No code ever reads a raw AWS key from the project — by design.

## Map keys — routes vs tiles (two different services)
**Route polylines** come from OUR backend (`GET /trips/{id}/days/{n}/route`),
which reads cached geometry from the `routes` table and calls OpenRouteService
only on a cache miss. The ORS key therefore lives ONLY in `backend/.env`
(`ORS_API_KEY`) — never in `web/`, never in the JS bundle.

**Basemap tiles** (the map imagery behind the route) are a separate service.
CARTO's dark basemap now requires a free API key; without one we fall back to
keyless OSM tiles rendered dark via CSS. For native CARTO tiles, put a free
key in `web/.env.local` as `VITE_CARTO_API_KEY` (or Amplify console env vars)
and domain-restrict it in the CARTO console — frontend keys are public by
design. ORS does NOT serve map tiles; its key cannot fix a tile watermark.
