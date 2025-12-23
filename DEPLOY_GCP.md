# Deploying to Google Cloud Platform (Cloud Run)

This guide assumes you have the Google Cloud SDK (`gcloud`) installed and a GCP project set up.

## Prerequisites

1.  **Google Cloud Project**: Create one at [console.cloud.google.com](https://console.cloud.google.com).
2.  **Billing Enabled**: Cloud Run requires billing (though it has a generous free tier).
3.  **APIs Enabled**: Enable "Cloud Run API" and "Artifact Registry API".

## Steps to Deploy

### 1. Login to Google Cloud
Open your terminal and run:
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### 2. Configure Docker Auth (Optional but recommended)
```bash
gcloud auth configure-docker
```

### 3. Build and Deploy (One-Command Method)
You can use `gcloud run deploy` to build and deploy from source automatically.

Run this command from the root `BulkEmailSender` directory:

```bash
gcloud run deploy bulk-freshdesk-mailer \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars FRESHDESK_DOMAIN="your-domain",FRESHDESK_API_KEY="your-api-key"
```

**Replace:**
*   `your-domain`: Your Freshdesk domain (e.g., `layersshop-help.freshdesk.com`).
*   `your-api-key`: Your actual Freshdesk API key.

### 4. Access Your App
Once deployment finishes, `gcloud` will output a Service URL (e.g., `https://bulk-freshdesk-mailer-xyz-uc.a.run.app`).
Click that link to see your live application!

---

## Alternative: Build Docker Image Locally & Push

If you prefer to build the image locally first:

1.  **Build:**
    ```bash
    docker build -t gcr.io/YOUR_PROJECT_ID/bulk-mailer .
    ```

2.  **Push:**
    ```bash
    docker push gcr.io/YOUR_PROJECT_ID/bulk-mailer
    ```

3.  **Deploy:**
    ```bash
    gcloud run deploy bulk-mailer \
      --image gcr.io/YOUR_PROJECT_ID/bulk-mailer \
      --platform managed \
      --region us-central1 \
      --allow-unauthenticated \
      --set-env-vars FRESHDESK_DOMAIN="...",FRESHDESK_API_KEY="..."
    ```

## GitHub Integration (CI/CD)

1.  Push this code to a GitHub repository.
2.  Go to the [Cloud Run Console](https://console.cloud.google.com/run).
3.  Click "Create Service".
4.  Select "Continuously deploy new revisions from a source repository".
5.  Connect your GitHub repo and select the branch.
6.  Cloud Build will automatically deploy your app whenever you push changes!
