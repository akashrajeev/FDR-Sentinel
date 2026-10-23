FROM python:3.12-slim-trixie
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
ARG APT_MAX_FUTURE_SECONDS=10
ARG DEBIAN_SNAPSHOT=""
RUN if [ -n "$DEBIAN_SNAPSHOT" ]; then sed -i "s|http://deb.debian.org/debian-security|https://snapshot.debian.org/archive/debian-security/${DEBIAN_SNAPSHOT}/|g; s|http://deb.debian.org/debian|https://snapshot.debian.org/archive/debian/${DEBIAN_SNAPSHOT}/|g" /etc/apt/sources.list.d/debian.sources; fi \
    && apt-get -o APT::Update::Error-Mode=any -o Acquire::Max-FutureTime=${APT_MAX_FUTURE_SECONDS} update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng && rm -rf /var/lib/apt/lists/*
COPY requirements.lock ./
RUN pip install --no-cache-dir --upgrade pip==26.2.2
RUN pip install --no-cache-dir -r requirements.lock
COPY pyproject.toml alembic.ini ./
COPY apps/api apps/api
COPY scripts scripts
COPY tests tests
RUN pip install --no-deps . && pip uninstall --yes pip \
    && rm -rf /usr/local/lib/python3.12/ensurepip \
    && useradd -m -u 10001 sentinel
USER sentinel
CMD ["uvicorn", "sentinel.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
