# Use Python image (since your backend is Python, not Node)
FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for caching
COPY backend/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Expose port 8080 (Cloud Run default)
ENV PORT=8080
EXPOSE 8080

# Run FastAPI with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
