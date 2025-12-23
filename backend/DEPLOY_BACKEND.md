# Deploying Backend to Google Cloud Run

## Prerequisites
- gcloud CLI installed and authenticated (`gcloud init`)
- Billing enabled on the project
- Enable APIs:
  ```bash
  gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
  ```

## Deploy (source-based)
From the `backend/` directory:
```bash
gcloud run deploy freshdesk-bulk-api \
  --source . \
  --region asia-south1 \
  --allow-unauthenticated
```

Cloud Run will build and deploy the container. The service will listen on port 8080 (set in Dockerfile and uvicorn).

## Environment Variables (set in Cloud Run)
- `FRESHDESK_DOMAIN` (e.g., `layersshop-help` – subdomain only)
- `FRESHDESK_API_KEY` (Freshdesk API key, Basic Auth username; password is `X`)

Set them in the Cloud Run console (or via flags `--set-env-vars`).

## Notes
- The app exposes `/health`, `/freshdesk-test`, and `/send-bulk`.
- CORS is permissive by default; tighten `allow_origins` in `main.py` if needed.***


