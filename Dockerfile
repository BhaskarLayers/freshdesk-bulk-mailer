# Use Python image
FROM python:3.11-slim

# Set working directory to /app
WORKDIR /app

# Copy requirements first for caching
COPY backend/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code directly into /app
COPY backend/ .

# Explicitly expose port 8080
ENV PORT=8080
EXPOSE 8080

# Run FastAPI with Uvicorn
# We use host 0.0.0.0 to ensure it listens on all interfaces (required for Docker/Cloud Run)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
