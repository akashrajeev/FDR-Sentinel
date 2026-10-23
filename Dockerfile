FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
ARG APT_MAX_FUTURE_SECONDS=10
RUN apt-get -o Acquire::Max-FutureTime=${APT_MAX_FUTURE_SECONDS} update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng && rm -rf /var/lib/apt/lists/*
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY pyproject.toml alembic.ini ./
COPY apps/api apps/api
COPY scripts scripts
COPY tests tests
RUN pip install --no-deps . && useradd -m -u 10001 sentinel
USER sentinel
CMD ["uvicorn", "sentinel.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
