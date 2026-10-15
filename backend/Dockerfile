FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_PATH=/data/hotels.db

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
RUN pip install .

# Run as an unprivileged user; the database lives on a mounted volume.
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /data \
    && chown app:app /data
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"

# 0.0.0.0 inside the container only. docker-compose.yml does not publish this
# port; the frontend's nginx reaches it over the internal compose network.
CMD ["uvicorn", "hotel_watcher.main:app", "--host", "0.0.0.0", "--port", "8000"]
