FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
COPY requirements.lock.txt .
COPY app ./app
RUN pip install --no-cache-dir -r requirements.lock.txt && pip install --no-cache-dir --no-deps .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
