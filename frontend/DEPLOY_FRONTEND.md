# Deploying Frontend to Netlify (Vite)

## Prerequisites
- Node.js and npm installed
- Backend deployed (Cloud Run URL available)

## Build locally
```bash
cd frontend
npm install
npm run build
```

## Netlify (Git-based)
1) Push the repo to GitHub.
2) In Netlify: **New site from Git** → pick the repo.
3) Build command: `npm run build`
4) Publish directory: `dist`
5) Environment variable:
   - `VITE_API_BASE_URL=https://<your-cloud-run-url>`
6) Deploy.

## Netlify (CLI)
```bash
npm install -g netlify-cli
cd frontend
netlify init   # follow prompts
netlify deploy --prod --dir=dist
```

Set env var in Netlify dashboard or `netlify env:set`:
- `VITE_API_BASE_URL=https://<your-cloud-run-url>`

## Notes
- The frontend reads the API base URL from `VITE_API_BASE_URL` and calls `${VITE_API_BASE_URL}/send-bulk`.
- Ensure the backend allows the Netlify domain in CORS (backend currently permits all).***


