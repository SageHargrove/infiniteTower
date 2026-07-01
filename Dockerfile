# syntax=docker/dockerfile:1

# ── Stage 1: build the React frontend ────────────────────────────────────────
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: run the FastAPI backend ─────────────────────────────────────────
FROM python:3.11-slim AS backend

# ComfyUI lives on the host; only the API server goes in the container.
# Set COMFY_URL at runtime to point at your ComfyUI instance, e.g.:
#   docker run -e COMFY_URL=http://host.docker.internal:8188 ...
ENV COMFY_URL=http://host.docker.internal:8188

WORKDIR /app/backend

# Install Python deps first (better layer caching)
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./

# Inject the pre-built frontend so FastAPI can serve it
COPY --from=frontend-builder /app/frontend/dist ../frontend/dist

# Saves directory — mount a volume here to persist game data across restarts:
#   docker run -v /path/to/saves:/app/backend/saves ...
VOLUME ["/app/backend/saves"]

# Static assets (portraits, icons, etc.) — mount if you want them to persist:
#   docker run -v /path/to/static:/app/backend/static ...
VOLUME ["/app/backend/static"]

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
