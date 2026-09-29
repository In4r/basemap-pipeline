FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for common geospatial libs (uncomment as needed once real
# dependencies like rasterio/gdal are added to pyproject.toml):
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     gdal-bin libgdal-dev && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install .

COPY tests ./tests

ENTRYPOINT ["generate-basemap"]
CMD ["--help"]
