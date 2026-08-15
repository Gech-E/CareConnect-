FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Worker shares the same codebase as the API
COPY ../api/pyproject.toml ./
RUN pip install --no-cache-dir hatchling \
    && pip install --no-cache-dir .

COPY ../api/ .
COPY . ./worker/

RUN useradd --create-home appuser
USER appuser

CMD ["celery", "-A", "worker.app", "worker", "--loglevel=info", "--concurrency=4"]
