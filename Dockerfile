FROM node:20-bookworm AS ui-build
WORKDIR /ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci --legacy-peer-deps
COPY ui/ ./
RUN npm run build

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OUTPUT_DIR=/app/data/analysis \
    EXPORT_DIR=/app/data/exports \
    PROVIDER=mock

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY . .
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir \
        "scrapy==2.16.0" \
        "scrapy-playwright==0.0.47" \
        "playwright==1.60.0" \
        "pytest==9.1.1" \
        "openpyxl==3.1.5" \
        "openai" \
        "pydantic>=2.0.0,<3.0.0" \
        "fastapi>=0.116.0,<1.0.0" \
        "uvicorn>=0.35.0,<1.0.0" \
        "python-multipart>=0.0.9,<1.0.0"
COPY --from=ui-build /ui/dist /app/ui/dist

RUN mkdir -p /app/data/analysis /app/data/exports

EXPOSE 8000

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
