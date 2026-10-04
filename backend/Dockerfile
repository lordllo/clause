FROM python:3.12-slim
WORKDIR /app/backend
COPY backend/pyproject.toml .
COPY backend/requirements.lock.txt .
COPY backend/app ./app
COPY samples /app/samples
COPY fixtures /app/fixtures
RUN pip install --no-cache-dir -r requirements.lock.txt && pip install --no-cache-dir --no-deps .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
