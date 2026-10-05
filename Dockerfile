FROM node:22-alpine AS web
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend ./
ENV NEXT_TELEMETRY_DISABLED=1 CLAUSE_STATIC_EXPORT=true NEXT_PUBLIC_API_URL=/api
RUN npm run build

FROM python:3.12-slim
WORKDIR /app/backend
COPY backend/requirements.lock.txt backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install --no-cache-dir -r requirements.lock.txt && pip install --no-cache-dir --no-deps .
COPY samples /app/samples
COPY fixtures /app/fixtures
COPY --from=web /build/frontend/out /app/web
ENV STATIC_DIR=/app/web DATA_DIR=/app/backend/data ANALYSIS_PROVIDER=demo DEMO_SEED=true
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app.main:hosted --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
