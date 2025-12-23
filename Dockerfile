# --- Stage 1: Build Frontend ---
FROM node:18-alpine as frontend-build

WORKDIR /app/frontend

# Copy package files first for caching
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy source and build
COPY frontend/ ./
# Set API base URL to empty string for relative paths (same-origin)
ENV VITE_API_BASE_URL=""
RUN npm run build

# --- Stage 2: Build Backend & Serve ---
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if needed (e.g. for pandas/numpy if wheels missing)
# RUN apt-get update && apt-get install -y gcc

# Copy requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Copy built frontend assets from Stage 1 to backend/static
# This puts 'index.html' and 'assets/' inside /app/static
COPY --from=frontend-build /app/frontend/dist ./static

# Expose port (Cloud Run defaults to 8080)
ENV PORT=8080
EXPOSE 8080

# Run FastAPI with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
