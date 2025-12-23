# Use Python image
FROM python:3.11-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Set working directory to /app
WORKDIR /app

# Copy requirements first for caching
COPY backend/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code directly into /app
# This puts main.py at /app/main.py
COPY backend/ .

# Run FastAPI with Uvicorn
# We use the shell form (no brackets) to ensure $PORT variable expansion works.
# Cloud Run injects the PORT environment variable (default 8080).
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
