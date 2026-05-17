FROM python:3.11-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System dependencies (GDAL, WeasyPrint, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin libgdal-dev libgeos-dev libproj-dev \
    libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0 \
    libcairo2 libffi-dev libssl-dev \
    curl git build-essential \
    && rm -rf /var/lib/apt/lists/*

ENV CPLUS_INCLUDE_PATH=/usr/include/gdal \
    C_INCLUDE_PATH=/usr/include/gdal

WORKDIR /app

COPY requirements.txt .
# Install GDAL Python binding matching the system libgdal version
RUN pip install --upgrade pip && \
    GDAL_VERSION=$(gdal-config --version) && \
    pip install "gdal==${GDAL_VERSION}" && \
    pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/models /app/tmp /app/reports

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
