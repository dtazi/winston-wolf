# Winston Wolf tracking server — open pixel + click redirector.
# Built with uv to match the repo's tooling.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --frozen --no-dev

ENV WW_DATA_DIR=/data
EXPOSE 8000

CMD ["/app/.venv/bin/ww-tracking", "serve", "--host", "0.0.0.0", "--port", "8000"]
