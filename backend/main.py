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
    if not domain:
        return "http://localhost"
    if domain.startswith("https://"):
        return f"{domain.rstrip('/')}/api/v2"
    if ".freshdesk.com" in domain:
        return f"https://{domain.rstrip('/')}/api/v2"
    return f"https://{domain}.freshdesk.com/api/v2"

# Global vars (Safe Initialization)
FRESHDESK_DOMAIN = os.getenv("FRESHDESK_DOMAIN", "")
FRESHDESK_API_KEY = os.getenv("FRESHDESK_API_KEY", "")
BASE_URL = build_base_url(FRESHDESK_DOMAIN)
AUTH = (FRESHDESK_API_KEY, "X")
HEADERS = {"Content-Type": "application/json"}

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
# Routes
# ---------------------------------------------------

@app.get("/")
def root():
    """Health check for Cloud Run."""
    return {"status": "ok", "service": "freshdesk-mailer"}

@app.get("/health")
def health_check():
    return {"status": "ok", "env_domain": mask(FRESHDESK_DOMAIN)}

@app.get("/ticket-fields")
def ticket_fields():
    resp = freshdesk_get("ticket_fields")
    if not resp.ok:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    data = resp.json()
    simplified = []
    for f in data:
        simplified.append({
            "name": f.get("name"),
            "label": f.get("label"),
            "choices": f.get("choices"),
            "required_for_agents": f.get("required_for_agents"),
            "type": f.get("type"),
        })
    return simplified
@app.post("/send-bulk")
async def send_bulk_email(
    file: UploadFile = File(...),
    subject_template: str = Form(...),
    body_template: str = Form(...),
    email_column: str = Form("email"),
    disposition: str = Form(""),
    custom_fields_json: str = Form(""),
):
    if not FRESHDESK_API_KEY or len(FRESHDESK_API_KEY) < 10:
        raise HTTPException(status_code=500, detail="Server misconfiguration: Invalid API Key")

    logger.info(
        "Received file=%s, subject_tmpl=%s, body_tmpl_len=%d, email_col=%s",
        file.filename,
        subject_template,
        len(body_template),
        email_column,
    )

    contents = await file.read()
    filename = file.filename or ""

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(BytesIO(contents))
        else:
            df = pd.read_excel(BytesIO(contents))
    except Exception as e:
        logger.error("Error parsing file: %s", e)
        raise HTTPException(status_code=400, detail=f"Invalid file format: {e}")

    df.columns = [c.strip() for c in df.columns]

    if email_column not in df.columns:
        raise HTTPException(
            status_code=400,
            detail=f"Column '{email_column}' not found. Available: {list(df.columns)}",
        )

    results = []
    
    # Identify custom fields (columns that are NOT email)
    # We ignore specific system fields if needed
    ignored_fields = {"company", "company_id", email_column}
    
    for idx, row in df.iterrows():
        recipient_email = str(row[email_column]).strip()
        
        # Build custom_fields dict for this row
        # Only include columns that actually exist in the row
        row_custom_fields = {}
        for col in df.columns:
            if col not in ignored_fields:
                val = row[col]
                if pd.notna(val) and str(val).strip() != "":
                     # Freshdesk expects specific formats, but we send as string/number
                     # Ensure we don't send nulls
                     row_custom_fields[col] = val
        # Merge dynamic custom fields from form
        extra_fields: Dict[str, Any] = {}
        if custom_fields_json:
            try:
                parsed = json.loads(custom_fields_json)
                if isinstance(parsed, dict):
                    extra_fields = parsed
            except Exception as e:
                logger.warning(f"Invalid custom_fields_json: {e}")
        # Attach disposition if provided
        if disposition:
            extra_fields["cf_choose_your_inquiry"] = disposition
        # Merge with precedence to extra_fields
        row_custom_fields = {**row_custom_fields, **extra_fields}

        # Simple template substitution
        # This replaces {name} with row['name'], etc.
        # We use a safe substitution that doesn't crash on missing keys
        row_dict = row.to_dict()
        # Convert all to string for safe formatting
        safe_row = {k: str(v) for k, v in row_dict.items()}
        
        try:
            final_subject = subject_template.format(**safe_row)
            final_body = body_template.format(**safe_row)
        except KeyError as e:
            # If template has {missing_col}, it might fail
            # We'll just leave it or fail? Let's fail safe
            final_subject = subject_template
            final_body = body_template
            logger.warning(f"Template key error: {e}")

        try:
            # -------------------------------------------------
            # SEND TO FRESHDESK
            # -------------------------------------------------
            send_ticket(
                email=recipient_email,
                subject=final_subject,
                body=final_body,
                custom_fields=row_custom_fields
            )
            results.append({"email": recipient_email, "status": "sent"})
        except Exception as e:
            logger.error("Failed for %s: %s", recipient_email, e)
            results.append({"email": recipient_email, "status": "error", "error": str(e)})

        # Rate limit (avoid 429)
        time.sleep(0.5)

    return {"processed": len(results), "details": results}
