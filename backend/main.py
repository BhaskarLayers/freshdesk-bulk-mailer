import logging
import os
import time
import json
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------
# Environment loading (SAFE for Cloud Run)
# ---------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
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
    domain = os.getenv("FRESHDESK_DOMAIN")
    api_key = os.getenv("FRESHDESK_API_KEY")

    if not domain or not api_key:
        raise RuntimeError(
            "FRESHDESK_DOMAIN and FRESHDESK_API_KEY must be set."
        )

    api_key_len = len(api_key.strip())
    if api_key_len < 15:
        raise RuntimeError(
            f"Invalid Freshdesk API key length ({api_key_len})."
        )

    logger.info(
        "Freshdesk env loaded: domain=%s, api_key_length=%d, api_key_preview=%s",
        domain,
        api_key_len,
        mask(api_key),
    )


# ---------------------------------------------------
# FastAPI app
# ---------------------------------------------------

app = FastAPI(title="Bulk Freshdesk Mailer", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------
# Freshdesk helpers
# ---------------------------------------------------

def build_base_url(domain: str) -> str:
    if domain.startswith("https://"):
        return f"{domain.rstrip('/')}/api/v2"
    if ".freshdesk.com" in domain:
        return f"https://{domain.rstrip('/')}/api/v2"
    return f"https://{domain}.freshdesk.com/api/v2"


def freshdesk_get(endpoint: str) -> requests.Response:
    url = f"{BASE_URL}/{endpoint}"
    try:
        resp = requests.get(url, auth=AUTH, headers=HEADERS, timeout=15)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return resp


def send_ticket(
    email: str,
    subject: str,
    body: str,
    custom_fields: Dict[str, Any],
) -> Dict[str, Any]:
    url = f"{BASE_URL}/tickets"
    payload = {
        "email": email,
        "subject": subject,
        "description": body,
        "status": 2,
        "priority": 1,
        "source": 2,
        "type": "Other Issue",
        "custom_fields": custom_fields,
    }

    resp = requests.post(
        url,
        json=payload,
        auth=AUTH,
        headers=HEADERS,
        timeout=30,
    )

    if not resp.ok:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()


# ---------------------------------------------------
# Startup event (CRITICAL FIX)
# ---------------------------------------------------

@app.on_event("startup")
async def startup_checks():
    """
    Cloud Run–safe startup.
    Never crash the app here.
    """
    global FRESHDESK_DOMAIN, FRESHDESK_API_KEY, BASE_URL, AUTH, HEADERS

    try:
        validate_env()
    except Exception as exc:
        logger.error("❌ Environment validation failed: %s", exc)
        return

    FRESHDESK_DOMAIN = os.getenv("FRESHDESK_DOMAIN")
    FRESHDESK_API_KEY = os.getenv("FRESHDESK_API_KEY")

    BASE_URL = build_base_url(FRESHDESK_DOMAIN)
    AUTH = (FRESHDESK_API_KEY, "X")
    HEADERS = {"Content-Type": "application/json"}

    logger.info("✅ Startup completed. Base URL: %s", BASE_URL)


# ---------------------------------------------------
# API endpoints
# ---------------------------------------------------

@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/ticket-fields")
def get_ticket_fields():
    resp = freshdesk_get("ticket_fields")
    if not resp.ok:
        raise HTTPException(resp.status_code, resp.text)
    return resp.json()


@app.post("/send-bulk")
async def send_bulk(
    file: UploadFile = File(...),
    subject_template: str = Form(...),
    body_template: str = Form(...),
    disposition: str = Form(...),
    custom_fields_json: Optional[str] = Form(None),
    email_column: str = Form("email"),
):
    content = await file.read()
    filename = file.filename or ""

    try:
        if filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(BytesIO(content))
        elif filename.endswith(".csv"):
            df = pd.read_csv(StringIO(content.decode("utf-8")))
        else:
            raise HTTPException(400, "Unsupported file type")
    except Exception as exc:
        raise HTTPException(400, f"File parse error: {exc}")

    if email_column not in df.columns:
        raise HTTPException(
            400,
            {
                "message": f"Email column '{email_column}' not found",
                "columns": list(df.columns),
            },
        )

    extra_fields = {}
    if custom_fields_json:
        try:
            extra_fields = json.loads(custom_fields_json)
        except json.JSONDecodeError:
            pass

    final_custom_fields = {
        "cf_choose_your_inquiry": disposition,
        **extra_fields,
    }

    results: List[Dict[str, Any]] = []

    for idx, row in df.iterrows():
        row_dict = {
            k: "" if pd.isna(v) else str(v)
            for k, v in row.to_dict().items()
        }

        email = row_dict.get(email_column, "").strip()
        if not email:
            results.append({"row": int(idx), "status": "skipped"})
            continue

        try:
            subject = subject_template.format(**row_dict)
            body = body_template.format(**row_dict)
            ticket = send_ticket(email, subject, body, final_custom_fields)
            results.append({"row": int(idx), "status": "sent", "ticket_id": ticket.get("id")})
        except Exception as exc:
            results.append({"row": int(idx), "status": "error", "error": str(exc)})

        time.sleep(0.5)

    return {"total": len(df), "results": results}
