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
FROM node:20-alpine AS frontend-builder

WORKDIR /build/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci && npm cache clean --force

COPY frontend/ .

RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2 — Python wheel assembly + static collection
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS backend-forge

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock .
RUN uv sync --no-dev --frozen

COPY . .

RUN DJANGO_SETTINGS_MODULE=config.settings \
    SECRET_KEY=placeholder-do-not-use \
    DATABASE_URL=sqlite:///app/db.sqlite3 \
    OIDC_RP_CLIENT_ID=builder \
    OIDC_RP_CALLBACK_URL=builder \
    /app/.venv/bin/python manage.py collectstatic --noinput --clear

# ---------------------------------------------------------------------------
# Stage 3 — Final runtime image
# ---------------------------------------------------------------------------
FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH=/app/.venv/bin:$PATH \
    HOME=/app \
    LANCE_DB_PATH=/data/lancedb

COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /bin/uv

RUN addgroup --system --gid 1001 appgroup \
    && adduser --system --uid 1001 --gid 1001 appuser \
    && mkdir -p /data/lancedb /app/static /app/staticfiles /app/media \
    && chown -R appuser:appgroup /data /app/static /app/staticfiles /app/media

COPY --from=backend-forge /app /app
COPY --from=frontend-builder /build/static/frontend /app/static/frontend
COPY docker-entrypoint.sh /docker-entrypoint.sh

RUN rm -f /app/db.sqlite3 \
    && chown -R appuser:appgroup /app /app/static /app/staticfiles /app/media

WORKDIR /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["/app/.venv/bin/gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2"]
