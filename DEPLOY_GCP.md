# Deploying to Google Cloud Platform (Cloud Run)

You have two easy ways to deploy. Since you asked for **Cloud Shell**, here are the commands.

## Option 1: Using Google Cloud Shell (Recommended for you)

1.  Open [Google Cloud Shell](https://shell.cloud.google.com).
2.  Run these commands one by one:

```bash
# 1. Clone your repository
git clone https://github.com/BhaskarLayers/freshdesk-bulk-mailer.git
cd freshdesk-bulk-mailer

# 2. Deploy to Cloud Run
# Replace 'YOUR_API_KEY' and 'YOUR_DOMAIN' with your actual values!
gcloud run deploy freshdesk-mailer \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars FRESHDESK_API_KEY="YOUR_API_KEY",FRESHDESK_DOMAIN="YOUR_DOMAIN"
```

3.  When asked to enable APIs (Artifact Registry, Cloud Run), type `y` and press Enter.
4.  Wait for the deployment to finish. It will give you a URL (e.g., `https://freshdesk-mailer-xyz.a.run.app`).

---

## Option 2: Using the Google Cloud Console Website (No Coding)

1.  Go to [console.cloud.google.com/run](https://console.cloud.google.com/run).
2.  Click **Create Service**.
3.  Select **"Continuously deploy from a repository"**.
4.  Connect your GitHub repo (`BhaskarLayers/freshdesk-bulk-mailer`).
5.  Under **Variables & Secrets**, add your `FRESHDESK_API_KEY` and `FRESHDESK_DOMAIN`.
6.  Click **Create**.
