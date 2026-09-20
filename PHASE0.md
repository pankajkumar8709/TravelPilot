# Phase 0 — Stack + Strategy Lock

Freezes every infrastructure decision before feature code. This file is the
single reference for the checklist items in `plan.md` Phase 0.

## Stack (locked — no swapping mid-build)
- **Backend:** FastAPI on **App Runner** (`backend/Dockerfile` or `backend/apprunner.yaml`)
- **Frontend:** React + TypeScript (Vite) on **Amplify Hosting** (`amplify.yml`)
- **Database:** **RDS Postgres** via SQLAlchemy (local dev falls back to SQLite — same code path)
- **AI:** **Bedrock** (boto3 Converse) — interest→category prioritization + NL intent only
- **Disruption path:** **EventBridge → SQS → Lambda** (`infra/template.yaml`)
- **Data lake:** **S3** for raw ingestion responses (Phase 10)

## Repo structure (agreed)
```
travel/
  backend/        FastAPI app, core engine, scripts, tests, Dockerfile, apprunner.yaml
    app/
      core/       pure, testable engine: scheduler, validator, suggestions, repair, timeutil
      services/   llm (Bedrock+mock), trip_service (orchestration)
      scripts/    seed, seed_data, probe_rds, probe_bedrock, ingest (Phase 3 real)
    tests/        test_core.py (9), test_api.py (1 e2e) — all green
  web/            React+TS+Vite frontend (theme lock, components, api client)
  infra/          SAM template + Lambda + test-event script (disruption pipeline)
  amplify.yml     Amplify build spec
  plan.md         the build plan (source of truth)
  PHASE0.md       this file
```
Monorepo (frontend + backend + infra together) — simpler for a hackathon; one clone, one PR history.

## Secrets / env strategy
- Local: `backend/.env` (git-ignored); template in `backend/.env.example`.
- Prod: App Runner service env vars (or Secrets Manager refs) for `DATABASE_URL`,
  `BEDROCK_MODEL_ID`, `AWS_REGION_NAME`, `CORS_ORIGINS`, `USE_MOCK_LLM`.
- `AWS_REGION_NAME` is used deliberately — `AWS_REGION` is reserved by the runtime.
- Nothing secret is committed; `.gitignore` covers `.env`, `.aws/`, `*.pem`, `*.db`.
- Frontend: `VITE_API_BASE` set in Amplify console to the App Runner URL.

## Branching strategy
- `main` = always-deployable; feature branches `feat/<phase>-<slug>`; PR into main.
- One owner per phase; deploy from `main` only.

## Manual console checklist (YOUR AWS account — run these, then tick)
- [ ] Create App Runner service from `backend/` (Docker or source). Confirm the "hello" `/health` responds.
- [ ] Create Amplify app pointing at `web/` with `amplify.yml`. Confirm the deployed URL loads.
- [ ] Provision RDS Postgres (db.t3.micro). Then:
      `set DATABASE_URL=... && python -m app.scripts.probe_rds`  → expect "connectivity confirmed".
- [x] Confirm the LLM provider (Groq — Bedrock unavailable on this account):
      `python -m app.scripts.probe_llm`  → "OK — Groq responded". Model: openai/gpt-oss-20b.
- [ ] Deploy the pipeline: `cd infra && sam build && sam deploy --guided`, then
      `set QUEUE_URL=<output> && python send_test_event.py`  → expect the probe log in CloudWatch.
- [ ] Agree branch ownership per phase.

## RDS ↔ Lambda networking decision (avoid the NAT-gateway trap)
For the hackathon: make RDS **publicly accessible** with a security group that allows
only your IP + App Runner egress. Skip putting Lambda in the VPC (which would pull in a
NAT gateway ~$1/day). The Lambda calls the backend HTTP endpoint, not RDS directly,
so it needs no VPC access at all.

## Exit criteria — ✅ PHASE 0 COMPLETE (user confirmed 2026-09-20)
Every service touched by a working "it works" test:
App Runner `/health` 200, Amplify URL loads, `probe_rds` OK, `probe_llm` OK (Groq),
SQS test event logged by the Lambda. Provisioning alone does not count.
LLM pivoted from Bedrock (blocked on this account) to Groq — see CREDENTIALS.md.

## Cost hygiene (so $100 credits survive)
- RDS db.t3.micro + App Runner are hourly/always-on — **stop them when not building**.
- No NAT gateway (see networking decision above).
- After the demo: delete the App Runner service, stop/delete RDS, `sam delete` the stack,
  delete the Amplify app. Bedrock/S3/SQS/Lambda are pay-per-use and near-zero idle.
