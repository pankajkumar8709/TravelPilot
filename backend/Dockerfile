# Backend container for AWS App Runner (Phase 0 / Phase 2 deploy).
FROM python:3.12-slim

WORKDIR /app

# System deps for psycopg2 build wheel are already covered by the binary wheel;
# keep the image slim.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# App Runner sets PORT; default 8000 locally.
ENV PORT=8000
EXPOSE 8000

# On boot: create tables (idempotent). Seeding is a one-off you run separately.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
