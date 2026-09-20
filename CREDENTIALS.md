# Credentials — where each one goes

| # | Credential | Secret? | WHERE it goes | How |
|---|-----------|---------|---------------|-----|
| 1 | AWS Access Key ID + Secret | **YES** | `~/.aws/credentials` (**never** the repo) | `aws configure --profile travelpilot` |
| 2 | Bedrock: region + model id | No (config) | `backend/.env` | copy from `.env.example` |
| 2 | Bedrock: model ACCESS | grant | Bedrock console → Model access | request Claude access |
| 3 | RDS `DATABASE_URL` (DB password you pick) | yes | `backend/.env` (local) / App Runner env (prod) | you choose it when creating RDS |
| 4 | `ORS_API_KEY` | yes | `backend/.env` | optional — ingestion only |

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
