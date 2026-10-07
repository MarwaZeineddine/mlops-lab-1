# Stage 1: builder
FROM python:3.14-slim AS builder
ENV UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv UV_HTTP_TIMEOUT=600 UV_HTTP_RETRIES=10
RUN pip install --no-cache-dir uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Stage 2: runtime
FROM python:3.14-slim
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY src ./src
EXPOSE 8000
ENTRYPOINT ["uvicorn", "src.food11.serve:app", "--host", "0.0.0.0", "--port", "8000"]