# Reviewer UI: FastAPI case API + React/Fluent SPA in one image.
# Build context is the repository root (see azure.yaml service "reviewer").

FROM node:20-bookworm-slim AS web
WORKDIR /web
COPY app/frontend/web/package.json app/frontend/web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY app/frontend/web/ ./
RUN npm run build

FROM python:3.11-slim-bookworm

WORKDIR /app
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    AUTOAUTH_RUNNER=legacy

RUN apt-get update && \
    apt-get -y install --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src /app/src
COPY app /app/app
COPY evals /app/evals
COPY utils/data/cases /app/utils/data/cases
COPY --from=web /web/dist /app/app/frontend/web/dist

EXPOSE 8000

CMD ["uvicorn", "app.backend.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
