# API image. Training happens in the local micromamba env (Apple GPU); this image serves.
#   docker compose up --build              -> runtime
#   docker compose run --rm test           -> runs pytest + ruff in the `test` stage

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PITWALL_DATA_DIR=/data \
    PITWALL_MODELS_DIR=/models
# LightGBM needs the OpenMP runtime
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# Install dependencies first (cached layer), then the package itself.
COPY pyproject.toml ./
RUN mkdir -p src/pitwall && touch src/pitwall/__init__.py && pip install . && pip uninstall -y pitwall
COPY src ./src
RUN pip install --no-deps .

FROM base AS test
RUN pip install "pytest>=8" "ruff>=0.6"
COPY tests ./tests
COPY scripts ./scripts
CMD ["sh", "-c", "ruff check src tests && pytest"]

FROM base AS runtime
RUN useradd --create-home --uid 1000 pitwall && mkdir -p /data /models && chown pitwall /data /models
USER pitwall
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"
CMD ["uvicorn", "pitwall.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
