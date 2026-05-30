# Copyright (C) 2026 Byers Brands, LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# ---------------------------------------------------------------------------
# Stage 1 — Frontend asset build
# ---------------------------------------------------------------------------
FROM node:20-alpine@sha256:f1718e3a058af04c3b3fd74b2c32ccd2ab39009e530d3b4c34b0c2f7a87c4d37 AS frontend-builder

WORKDIR /build/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force

COPY frontend/ .

RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2 — Python wheel assembly + static collection
# ---------------------------------------------------------------------------
FROM python:3.13-slim@sha256:37b9e4ccfd52d1d2ba0876e06748ae36fd04f588a25bf7e4e0ae5e4a175ed634 AS backend-forge

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

ENV UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:0.6.14@sha256:a7fbcd24dfe2288c5a3577a91e70c247daf3f7d52eace7787e1c5e03416e04cd /uv /bin/uv

WORKDIR /build

COPY pyproject.toml .
RUN uv lock --no-cache && uv sync --no-dev --no-cache

COPY . .

RUN DJANGO_SETTINGS_MODULE=config.settings \
    SECRET_KEY=placeholder-do-not-use \
    DATABASE_URL=sqlite:///build/db.sqlite3 \
    uv run python manage.py collectstatic --noinput --clear

# ---------------------------------------------------------------------------
# Stage 3 — Final runtime image
# ---------------------------------------------------------------------------
FROM python:3.13-slim@sha256:37b9e4ccfd52d1d2ba0876e06748ae36fd04f588a25bf7e4e0ae5e4a175ed634

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    LANCE_DB_PATH=/data/lancedb

COPY --from=ghcr.io/astral-sh/uv:0.6.14@sha256:a7fbcd24dfe2288c5a3577a91e70c247daf3f7d52eace7787e1c5e03416e04cd /uv /bin/uv

RUN addgroup --system --gid 1001 appgroup \
    && adduser --system --uid 1001 --gid 1001 appuser \
    && mkdir -p /data/lancedb /app/static /app/media \
    && chown -R appuser:appgroup /data /app

COPY --from=backend-forge /usr/local/lib/python3.13 /usr/local/lib/python3.13
COPY --from=backend-forge /usr/local/bin /usr/local/bin
COPY --from=backend-forge /build /app
COPY --from=frontend-builder /build/frontend/dist /app/static/frontend
COPY deploy/docker/docker-entrypoint.sh /docker-entrypoint.sh

WORKDIR /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2"]
