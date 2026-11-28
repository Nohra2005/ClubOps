FROM scratch AS build-context-check
COPY . /

FROM node:24-bookworm-slim AS frontend
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN --mount=type=secret,id=clubops_build_ca \
    if [ -f /run/secrets/clubops_build_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/clubops_build_ca; fi; \
    npm ci
COPY web/ ./
# Public OAuth ID only. No provider keys or OAuth secrets belong in build args.
ARG VITE_GOOGLE_CLIENT_ID
ARG VITE_DEV_LOGIN=0
ENV VITE_API_MODE=http VITE_API_BASE=/api
RUN if [ "$VITE_DEV_LOGIN" != 1 ]; then test -n "$VITE_GOOGLE_CLIENT_ID"; fi && npm run build

FROM ghcr.io/astral-sh/uv:0.13.5 AS uv
FROM caddy:2.11.7 AS caddy
FROM python:3.12-slim-bookworm AS runtime
WORKDIR /app
COPY --from=uv /uv /usr/local/bin/uv
COPY --from=caddy /usr/bin/caddy /usr/local/bin/caddy
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 \
    CLUBOPS_DATA_DIR=/var/data/clubops CLUBOPS_DEV_LOGIN=0 CLUBOPS_COOKIE_SECURE=1
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
RUN --mount=type=secret,id=clubops_build_ca \
    if [ -f /run/secrets/clubops_build_ca ]; then export SSL_CERT_FILE=/run/secrets/clubops_build_ca; fi; \
    uv sync --locked --no-dev --no-editable --system-certs
COPY scripts/load_rulebook.py scripts/add_member.py scripts/move_knowledge.py ./scripts/
COPY data/rulebook/aub-rules.json ./data/rulebook/aub-rules.json
COPY --from=frontend /build/web/dist ./web/dist/
COPY web/Caddyfile web/start.sh web/serve.sh ./web/
# Accommodate Windows CRLF checkouts without requiring a repository-wide rewrite.
RUN sed -i 's/\r$//' web/*.sh && chmod +x web/*.sh && mkdir -p /var/data/clubops
ARG VITE_GOOGLE_CLIENT_ID
ARG VITE_DEV_LOGIN=0
ENV CLUBOPS_WEB_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID CLUBOPS_WEB_DEV_LOGIN=$VITE_DEV_LOGIN
EXPOSE 10000
CMD ["bash", "/app/web/start.sh"]

FROM runtime AS local
COPY web/start-local.sh ./web/start-local.sh
RUN sed -i 's/\r$//' web/start-local.sh && chmod +x web/start-local.sh && touch /app/.local-development-build
ENV CLUBOPS_DEV_LOGIN=1 CLUBOPS_COOKIE_SECURE=0
CMD ["bash", "/app/web/start-local.sh"]

# The default build is production; a local-login frontend cannot ship in this target.
FROM runtime AS production
RUN test "$CLUBOPS_WEB_DEV_LOGIN" = 0
