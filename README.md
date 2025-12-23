# Bulk Freshdesk Mailer

Simple internal tool to send personalised emails (via Freshdesk ticket creation) in bulk using a CSV/XLSX upload.

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- Freshdesk domain + API key (Growth plan)

## Backend (FastAPI)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Set environment (create `.env` from the example):

```
cp env.example .env
FRESHDESK_DOMAIN=your_subdomain_here   # e.g. acme if your URL is https://acme.freshdesk.com
FRESHDESK_API_KEY=your_api_key_here    # from Profile Settings -> API Key (use as Basic Auth username with X as password)
```

Run the API:

```bash
uvicorn main:app --reload --port 8000
```

Endpoints:
- `POST /send-bulk` — multipart form with `file`, `subject_template`, `body_template`, `email_column` (default `email`)
- `GET /health`

## Frontend (Vite + React + TS)

```bash
cd frontend
npm install
npm run dev
```

Default dev server: http://localhost:5173

## Using the app

1. Start backend (`uvicorn`) and frontend (`npm run dev`).
2. Open the frontend, upload your CSV/XLSX.
3. Confirm the email column name (e.g., `email`).
4. Enter subject/body templates using placeholders like `{name}` or `{company}` that match column names.
5. Click **Start sending**. The app will render per-row templates, create tickets via Freshdesk, and show per-row status (sent/skipped/error).

Notes:
- Freshdesk notifications for new tickets must be enabled so customers receive the email.
- Basic throttling (0.5s) is included to avoid hitting rate limits; adjust in `backend/main.py` if needed.
- API key stays only on the backend; the frontend never sees it.

## Troubleshooting: 401 Invalid Credentials Error

If you see `Freshdesk error 401: {"code":"invalid_credentials","message":"You have to be logged in to perform this action."}`, this is an **authentication issue**, not a code problem.

### Why 401 Occurs

HTTP 401 means Freshdesk is rejecting the API key being sent. Common causes:

1. **Truncated API Key**: Key copied incorrectly (missing characters at start/end)
2. **Wrong Portal**: API key from a different Freshdesk account/portal
3. **Wrong Role**: API key from a Requester account (must be Agent/Admin)
4. **Stale Key**: API key was regenerated but `.env` wasn't updated
5. **Domain Mismatch**: `FRESHDESK_DOMAIN` doesn't match the portal where the key was generated

### Developer Checklist: Verify API Key Authenticity

**Step 1: Verify API Key Length**
- Freshdesk API keys are typically **32+ characters** long
- Backend will fail at startup if key length < 30 characters
- Check startup logs: `api_key_length=XX` should be 30+

**Step 2: Test API Key Directly (Bypass Backend)**

Run this curl command **before** testing the backend:

```bash
curl -v -u 'YOUR_FRESHDESK_API_KEY:X' \
  -H "Content-Type: application/json" \
  -X GET https://layersshop-help.freshdesk.com/api/v2/tickets?per_page=1
```

**Expected Result:**
- ✅ **HTTP 200**: API key is valid. Backend should work.
- ❌ **HTTP 401**: API key is invalid. Regenerate in Freshdesk and retry.

**If curl returns 401:**
1. Go to Freshdesk: **Profile Settings → API Key**
2. Ensure you're logged into the **correct portal** (layersshop-help.freshdesk.com)
3. Ensure your role is **Agent** or **Admin** (not Requester)
4. Click **Reset API Key** to generate a new one
5. Copy the **ENTIRE** key (no truncation)
6. Update `backend/.env` with the full key
7. Restart backend: `uvicorn main:app --host 0.0.0.0 --port 8000`
8. Re-run the curl test until it returns 200

**Step 3: Test Backend Authentication**

Once curl succeeds, test the backend:

```bash
curl -i http://localhost:8000/freshdesk-test
```

**Expected Result:**
```json
{
  "ok": true,
  "status_code": 200,
  "message": "Authentication successful. Connected to: [Account Name]"
}
```

If this returns 401, the backend isn't loading the correct key from `.env`. Check:
- `.env` file exists in `backend/` directory
- Key has no quotes, no spaces, no trailing newlines
- Backend was restarted after updating `.env`

### Why Ticket Fields Are Unrelated

**401 errors occur BEFORE any ticket payload is sent.** The authentication happens at the HTTP level:
- Freshdesk rejects the request at the authentication layer
- Ticket fields (subject, description, status, etc.) are never evaluated
- This is why changing ticket fields won't fix 401 errors

### Quick Fix Summary

1. ✅ Verify API key length ≥ 30 characters
2. ✅ Test with curl: `curl -v -u 'KEY:X' https://layersshop-help.freshdesk.com/api/v2/tickets?per_page=1`
3. ✅ If curl fails → Regenerate API key in Freshdesk
4. ✅ Update `backend/.env` with full key (no quotes/spaces)
5. ✅ Restart backend
6. ✅ Test `/freshdesk-test` endpoint
7. ✅ Once `/freshdesk-test` returns 200, bulk send will work

