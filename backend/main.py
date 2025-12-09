import logging
import os
import time
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from a local .env file in the backend directory.
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
# Also try default load_dotenv() for flexibility
load_dotenv()

logger = logging.getLogger("freshdesk")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def mask(text: Optional[str]) -> str:
    if not text:
        return "<empty>"
    if len(text) <= 6:
        return f"{text[0]}***{text[-1]}"
    return f"{text[:3]}***{text[-3:]} (len={len(text)})"


def validate_env() -> None:
    """
    Validate Freshdesk environment variables with strict checks.
    Fails fast if API key is too short (likely truncated or invalid).
    """
    domain = os.getenv("FRESHDESK_DOMAIN")
    api_key = os.getenv("FRESHDESK_API_KEY")

    if not domain or not api_key:
        raise RuntimeError(
            "FRESHDESK_DOMAIN and FRESHDESK_API_KEY must be set in the environment or .env file."
        )

    # CRITICAL: Freshdesk API keys are typically 20+ characters.
    # If key is < 15 chars, it's almost certainly truncated or invalid.
    api_key_len = len(api_key.strip())
    if api_key_len < 15:
        raise RuntimeError(
            f"Invalid Freshdesk API key length ({api_key_len} chars). "
            "Freshdesk API keys are typically 20+ characters. "
            "Please regenerate your API key in Freshdesk: Profile Settings → API Key. "
            "Ensure you copy the ENTIRE key without any truncation."
        )

    logger.info(
        "Freshdesk env loaded: domain=%s, api_key_length=%d, api_key_preview=%s",
        domain,
        api_key_len,
        mask(api_key),
    )


validate_env()

FRESHDESK_DOMAIN = os.getenv("FRESHDESK_DOMAIN")
FRESHDESK_API_KEY = os.getenv("FRESHDESK_API_KEY")

# Build BASE_URL flexibly to handle different domain formats
if FRESHDESK_DOMAIN.startswith("https://"):
    BASE_URL = f"{FRESHDESK_DOMAIN.rstrip('/')}/api/v2"
elif ".freshdesk.com" in FRESHDESK_DOMAIN:
    BASE_URL = f"https://{FRESHDESK_DOMAIN.rstrip('/')}/api/v2"
else:
    BASE_URL = f"https://{FRESHDESK_DOMAIN}.freshdesk.com/api/v2"

# Authentication and headers
AUTH = (FRESHDESK_API_KEY, "X")
HEADERS = {"Content-Type": "application/json"}

app = FastAPI(title="Bulk Freshdesk Mailer", version="0.1.0")


@app.on_event("startup")
async def startup_auth_check():
    """
    Optional startup check: verify Freshdesk authentication.
    Logs warning if auth fails but doesn't block server startup.
    """
    try:
        test_result = test_portal_auth()
        if not test_result.get("ok"):
            logger.error(
                "⚠️  Freshdesk authentication FAILED at startup: %s",
                test_result.get("error", "Unknown error"),
            )
            logger.error(
                "Server started, but ticket creation will fail with 401. "
                "Fix API key in .env and restart."
            )
        else:
            logger.info(
                "✅ Freshdesk authentication verified at startup: %s",
                test_result.get("message", "OK"),
            )
    except Exception as exc:
        logger.warning("Could not verify Freshdesk auth at startup: %s", exc)

# Allow the local frontend to call the API.
# CORS: allow local dev origins; also allow all via regex for preflight robustness.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def freshdesk_base_url() -> str:
    return BASE_URL


def send_ticket(email: str, subject: str, body: str) -> Dict[str, Any]:
    """
    Create a Freshdesk ticket for the given requester email.
    Returns the parsed JSON response or raises an HTTPException on error.
    """
    url = f"{freshdesk_base_url()}/tickets"
    payload = {
        "email": email,
        "subject": subject,
        "description": body,
        "status": 2,  # Open
        "priority": 1,  # Low
        "source": 2,  # Portal
        "type": "Other Issue",  # Required by Freshdesk - using default "Other Issue"
        "custom_fields": {
            "cf_choose_your_inquiry": "Information Shared - Resolved"  # Required custom field
        },
        # Ensure requester receives notification
        "cc_emails": [],  # Explicitly set to ensure proper requester handling
    }

    try:
        response = requests.post(
            url,
            json=payload,
            auth=AUTH,  # Basic auth with API key as username, password = "X"
            headers=HEADERS,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Freshdesk request failed: {exc}")

    if response.status_code == 429:
        # Rate limited; bubble up so caller can decide what to do.
        raise HTTPException(
            status_code=429,
            detail="Freshdesk rate limit reached (429). Please slow down and retry.",
        )

    if not response.ok:
        logger.warning(
            "Freshdesk ticket create failed: status=%s body=%s url=%s",
            response.status_code,
            response.text,
            url,
        )
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Freshdesk error {response.status_code}: {response.text}",
        )

    return response.json()


def freshdesk_get(path: str) -> requests.Response:
    url = f"{freshdesk_base_url()}/{path.lstrip('/')}"
    try:
        resp = requests.get(url, auth=AUTH, headers=HEADERS, timeout=15)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Freshdesk request failed: {exc}")

    if not resp.ok:
        logger.warning(
            "Freshdesk GET failed: status=%s body=%s url=%s",
            resp.status_code,
            resp.text,
            url,
        )
    return resp


def test_portal_auth() -> Dict[str, Any]:
    """
    Test API key against Freshdesk portal using /api/v2/account endpoint.
    This endpoint requires authentication and returns account info if auth succeeds.
    Returns dict with ok, status_code, and diagnostic message.
    """
    resp = freshdesk_get("account")
    ok = resp.ok

    if resp.status_code == 401:
        return {
            "ok": False,
            "status_code": 401,
            "error": "API key does not belong to this Freshdesk portal. "
            "Verify: (1) API key is from the correct Freshdesk account, "
            "(2) Domain matches (layersshop-help.freshdesk.com), "
            "(3) Key is for an Agent/Admin role (not Requester).",
            "raw_response": resp.text[:500] if resp.text else "",
        }

    if ok:
        try:
            account_data = resp.json()
            account_name = account_data.get("name", "Unknown")
            return {
                "ok": True,
                "status_code": 200,
                "message": f"Authentication successful. Connected to: {account_name}",
                "account_name": account_name,
            }
        except Exception:
            pass

    return {
        "ok": ok,
        "status_code": resp.status_code,
        "raw_response": resp.text[:500] if resp.text else "",
    }


@app.post("/send-bulk")
async def send_bulk(
    file: UploadFile = File(...),
    subject_template: str = Form(...),
    body_template: str = Form(...),
    email_column: str = Form("email"),
):
    """
    Accept a CSV/XLSX file, render templates per row, and create Freshdesk tickets.
    """
    filename = file.filename or ""
    ext = filename.lower()
    content = await file.read()

    try:
        if ext.endswith(".xlsx") or ext.endswith(".xls"):
            df = pd.read_excel(BytesIO(content))
        elif ext.endswith(".csv"):
            df = pd.read_csv(StringIO(content.decode("utf-8")))
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Please upload .csv, .xlsx or .xls.",
            )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {exc}")

    if email_column not in df.columns:
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Email column '{email_column}' not found.",
                "available_columns": list(df.columns),
            },
        )

    results: List[Dict[str, Any]] = []
    total_rows = len(df)

    for idx, row in df.iterrows():
        row_dict = {
            key: "" if pd.isna(value) else str(value)
            for key, value in row.to_dict().items()
        }

        email = row_dict.get(email_column, "").strip()
        if not email:
            results.append({"row": int(idx), "status": "skipped", "reason": "no email"})
            continue

        try:
            subject = subject_template.format(**row_dict)
            body = body_template.format(**row_dict)
        except KeyError as exc:
            results.append(
                {
                    "row": int(idx),
                    "status": "error",
                    "error": f"Missing placeholder value for: {exc}",
                }
            )
            continue

        try:
            ticket_response = send_ticket(email=email, subject=subject, body=body)
            results.append(
                {
                    "row": int(idx),
                    "status": "sent",
                    "ticket_id": ticket_response.get("id"),
                }
            )
        except HTTPException as exc:
            results.append(
                {
                    "row": int(idx),
                    "status": "error",
                    "error": exc.detail,
                }
            )
            # If rate limited, break early to avoid hammering the API.
            if exc.status_code == 429:
                break

        # Basic throttle to respect Freshdesk rate limits.
        time.sleep(0.5)

    return {"total": total_rows, "results": results}


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/freshdesk-test")
def freshdesk_test():
    """
    Test endpoint to verify Freshdesk authentication and portal connection.
    Uses /api/v2/account which requires valid API key.
    Returns diagnostic info to help debug 401 errors.
    """
    return test_portal_auth()

