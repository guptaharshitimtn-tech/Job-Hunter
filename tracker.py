"""
tracker.py — Application tracker integration.
Appends a new application entry to the Excel job tracker spreadsheet.
"""

import os
from datetime import date
import openpyxl
import profile as p


def add_tracker_entry(
    company: str,
    role_title: str,
    role_family: str,
    location: str,
    platform: str,
    cv_variant: str,
    priority: str = "Medium",
    notes: str = "",
    referral: str = "No",
    contact_name: str = "",
    contact_email: str = "",
    tracker_path: str = None,
) -> tuple:
    """
    Append a new application row to the Application Tracker sheet.
    Returns (success: bool, message: str).

    Tracker column layout (21 columns):
    #, Date Applied, Company, Role Title, Role Family, Location, Platform,
    CV Variant, Status, Response Received?, Response Date, Response Type,
    Interview Stage, Interview Date, Follow-up Sent?, Follow-up Date,
    Feedback / Notes, Referral Used?, Contact Name, Contact Email, Priority
    """
    path = tracker_path or p.TRACKER_PATH
    if not os.path.exists(path):
        return False, f"Tracker file not found at: {path}"

    try:
        wb = openpyxl.load_workbook(path)
        if "Application Tracker" not in wb.sheetnames:
            return False, "Sheet 'Application Tracker' not found in workbook."

        ws = wb["Application Tracker"]

        # Find the last row with a Date Applied value (col 2); data starts at row 3
        last_data_row = 2
        for row in range(ws.max_row, 2, -1):
            if ws.cell(row, 2).value:
                last_data_row = row
                break

        next_row = last_data_row + 1
        last_num = ws.cell(last_data_row, 1).value or 0
        new_num  = int(last_num) + 1 if str(last_num).isdigit() else last_num + 1 if isinstance(last_num, int) else 1
        today    = date.today().strftime("%d-%b-%y")

        row_values = [
            new_num,          # Col 1:  #
            today,            # Col 2:  Date Applied
            company,          # Col 3:  Company
            role_title,       # Col 4:  Role Title
            role_family,      # Col 5:  Role Family
            location,         # Col 6:  Location
            platform,         # Col 7:  Platform
            cv_variant,       # Col 8:  CV Variant
            "Awaiting Response",  # Col 9:  Status
            "No",             # Col 10: Response Received?
            None,             # Col 11: Response Date
            None,             # Col 12: Response Type
            None,             # Col 13: Interview Stage
            None,             # Col 14: Interview Date
            "No",             # Col 15: Follow-up Sent?
            None,             # Col 16: Follow-up Date
            notes or None,    # Col 17: Feedback / Notes
            referral,         # Col 18: Referral Used?
            contact_name or None,   # Col 19: Contact Name
            contact_email or None,  # Col 20: Contact Email
            priority,         # Col 21: Priority
        ]

        for col_idx, value in enumerate(row_values, start=1):
            ws.cell(row=next_row, column=col_idx, value=value)

        wb.save(path)
        return True, f"Entry #{new_num} logged — {company}: {role_title}"

    except PermissionError:
        return False, (
            "Cannot write to tracker — the Excel file is open in another application. "
            "Close the file and try again."
        )
    except Exception as exc:
        return False, f"Failed to update tracker: {exc}"


# ── Gmail Integration ─────────────────────────────────────────────────────────

GMAIL_PARSE_PROMPT = '''\
Parse this email and return JSON. If a field cannot be determined, return null.
{{
  "company": "company name",
  "role_title": "exact job title",
  "application_date": "YYYY-MM-DD or null",
  "response_date": "YYYY-MM-DD",
  "response_type": "ATS Confirmation / Rejection / Interview Invite / Recruiter Outreach / Position Filled / Awaiting Response",
  "status": "ATS Confirmed / Rejected / Interview Scheduled / Awaiting Response / Rejected - Position Filled",
  "location": "job location or null",
  "channel": "LinkedIn / Indeed / Company Portal / Referral / etc or null",
  "notes": "one sentence summary",
  "is_application_related": true / false
}}

RULES:
- Job alert digests (multiple jobs listed) -> is_application_related: false
- Recruiter cold outreach, no specific application -> Recruiter Outreach
- ATS auto-confirmation -> ATS Confirmation
- Rejection email -> Rejection
- Do not infer fields not present in the email

EMAIL:
Subject: {subject}
From: {sender}
Date: {date}
Body: {body}\
'''

GMAIL_QUERIES = [
    # ATS confirmations — broad single-keyword subject hits
    "subject:application after:{seven_days_ago}",
    # Rejections
    "subject:regret after:{seven_days_ago}",
    # More rejection patterns
    "subject:unfortunately after:{seven_days_ago}",
    # Interview / next steps
    "subject:interview after:{seven_days_ago}",
    # Recruiter / shortlist
    "subject:shortlisted after:{seven_days_ago}",
    # Generic application follow-up
    "subject:\"your application\" after:{seven_days_ago}",
    # Applied confirmation
    "subject:\"applied\" after:{seven_days_ago}",
    # Next steps / offer
    "subject:\"next steps\" after:{seven_days_ago}",
    # Position filled
    "subject:\"position has been filled\" after:{seven_days_ago}",
]


def _cv_routing(role_title: str, notes: str) -> str:
    """Keyword-match role title + notes to a CV variant name."""
    text = f"{role_title} {notes}".lower()
    stream1_kw = ["revenue", "pipeline", "intelligence", "analytics", "bi",
                  "commercial analytics", "market intelligence", "deal intelligence"]
    stream2_kw = ["gtm", "strategy", "commercial", "go-to-market", "pursuit",
                  "business development"]
    stream3_kw = ["enablement", "sales enablement", "content", "playbook",
                  "training", "field readiness"]
    stream4_kw = ["research", "market research", "analyst", "intelligence analyst",
                  "secondary research"]
    consulting_kw = ["consulting", "advisory", "cdd", "due diligence",
                     "engagement manager"]

    if any(k in text for k in consulting_kw):
        return "Commercial Operations Director"
    if any(k in text for k in stream4_kw):
        return "Market Intel"
    if any(k in text for k in stream3_kw):
        return "Sales Enablement"
    if any(k in text for k in stream2_kw):
        return "GTM/BD"
    if any(k in text for k in stream1_kw):
        return "RevOps GTM"
    return "RevOps GTM"


def _auto_priority(response_type: str) -> str:
    """Map response_type to priority string."""
    mapping = {
        "Interview Invite":    "High",
        "Interview Scheduled": "High",
        "ATS Confirmation":    "Medium",
        "ATS Confirmed":       "Medium",
        "Recruiter Outreach":  "Medium",
        "Rejection":           "Low",
        "Position Filled":     "Low",
    }
    return mapping.get(response_type, "Medium")


def _check_duplicate(ws, company: str, role_title: str):
    """
    Return the row number of an existing entry matching company + role_title
    (case-insensitive), or None if not found.
    Data starts at row 3 (row 1 = header labels, row 2 = column names).
    """
    company_lower     = company.lower().strip()
    role_title_lower  = role_title.lower().strip()
    for row in range(3, ws.max_row + 1):
        cell_company = ws.cell(row, 3).value
        cell_role    = ws.cell(row, 4).value
        if (cell_company and cell_role and
                str(cell_company).lower().strip() == company_lower and
                str(cell_role).lower().strip() == role_title_lower):
            return row
    return None


def _get_gmail_service(credentials_dir: str):
    """
    Build and return an authorised Gmail API service.
    Expects credentials.json in credentials_dir.
    Stores/reads token.json in the same directory.
    Opens a local browser on first run for OAuth consent.
    """
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
    creds_file = os.path.join(credentials_dir, "credentials.json")
    token_file  = os.path.join(credentials_dir, "token.json")

    if not os.path.exists(creds_file):
        raise FileNotFoundError(
            f"credentials.json not found at {creds_file}. "
            "Download it from Google Cloud Console → APIs & Services → Credentials. "
            "IMPORTANT: create an OAuth client of type 'Desktop app', not 'Web application'."
        )

    # Validate client type — Web application clients don't support localhost redirects
    import json as _json
    with open(creds_file) as _cf:
        _cdata = _json.load(_cf)
    if "web" in _cdata and "installed" not in _cdata:
        raise ValueError(
            "credentials.json is for a 'Web application' OAuth client. "
            "Gmail sync requires a 'Desktop app' client type. "
            "Go to Google Cloud Console → APIs & Services → Credentials → "
            "Create Credentials → OAuth client ID → Desktop app."
        )

    creds = None
    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
            # Find a free port dynamically to avoid socket conflicts
            import socket as _sock
            def _free_port(start: int = 8085, end: int = 8200) -> int:
                for p in range(start, end):
                    with _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM) as s:
                        if s.connect_ex(("localhost", p)) != 0:
                            return p
                raise RuntimeError("No free port found in range 8085-8200.")
            _port = _free_port()
            creds = flow.run_local_server(port=_port, open_browser=True)
        with open(token_file, "w") as tf:
            tf.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _parse_email_with_llm(client, email_data: dict) -> dict:
    """
    Send email fields to the LLM for structured parsing.
    Returns dict with keys:
      "data"   → parsed payload (or None)
      "reason" → "ok" | "not_relevant" | "parse_failed" | "empty_body"
    """
    import re
    import json

    body = (email_data.get("body", "") or "").strip()
    if not body:
        return {"data": None, "reason": "empty_body"}

    prompt = GMAIL_PARSE_PROMPT.format(
        subject=email_data.get("subject", ""),
        sender=email_data.get("sender", ""),
        date=email_data.get("date", ""),
        body=body[:3000],
    )
    try:
        import profile as _p
        response = client.chat.completions.create(
            model=_p.MODEL,
            messages=[
                {"role": "system", "content": (
                    "You are a structured data extractor. "
                    "Return ONLY a valid JSON object starting with { and ending with }. "
                    "No markdown, no explanation, no text before or after the JSON."
                )},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=500,
        )
        raw = response.choices[0].message.content

        # Extract the first {...} block — robust against any leading/trailing text
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return {"data": None, "reason": "parse_failed: no JSON object found"}
        json_str = match.group(0)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            # Last resort: replace ] with } for Llama's bracket mistake
            from llm_utils import repair_json
            data = json.loads(repair_json(json_str))

        if not isinstance(data, dict):
            return {"data": None, "reason": "parse_failed: not a dict"}
        if not data.get("is_application_related"):
            return {"data": None, "reason": "not_relevant"}
        return {"data": data, "reason": "ok"}
    except Exception as exc:
        return {"data": None, "reason": f"parse_failed: {exc}"}


def update_tracker_from_gmail(
    client,
    tracker_path: str = None,
    credentials_path: str = None,
    days_back: int = 7,
) -> dict:
    """
    Scan Gmail for job-application emails, parse with LLM, and write
    new/updated rows to the Excel tracker.

    Returns {"added": int, "updated": int, "scanned": int, "unlogged": list,
             "query_hits": list[dict]}
    The "unlogged" list contains parsed dicts the caller should confirm before
    adding (e.g. companies not yet in the tracker).
    "query_hits" is a list of {query, hits} for debug display.
    """
    import base64
    from datetime import timedelta

    path             = tracker_path or p.TRACKER_PATH
    credentials_path = credentials_path or os.path.dirname(path)

    result = {"added": 0, "updated": 0, "scanned": 0, "unlogged": [],
              "query_hits": [],
              "not_relevant": 0,   # LLM said is_application_related=false
              "parse_failed": 0,   # body empty or JSON parse error
              "no_identity": 0,    # company/role missing → sent to unlogged
              "email_errors": 0,   # exception in per-email processing
              "samples": []        # first 3 parsed results for debug
              }

    # ── Gmail auth ────────────────────────────────────────────────────────────
    try:
        service = _get_gmail_service(credentials_path)
    except FileNotFoundError as exc:
        raise exc
    except Exception as exc:
        raise RuntimeError(f"Gmail authentication failed: {exc}") from exc

    # ── Build date threshold ───────────────────────────────────────────────────
    cutoff = (date.today() - timedelta(days=days_back)).strftime("%Y/%m/%d")
    queries = [q.replace("{seven_days_ago}", cutoff) for q in GMAIL_QUERIES]

    # ── Fetch message IDs (deduplicated) ──────────────────────────────────────
    seen_ids: set = set()
    message_ids: list = []
    for query in queries:
        try:
            resp = service.users().messages().list(
                userId="me", q=query, maxResults=50
            ).execute()
            hits = resp.get("messages", [])
            result["query_hits"].append({"query": query, "hits": len(hits)})
            for msg in hits:
                if msg["id"] not in seen_ids:
                    seen_ids.add(msg["id"])
                    message_ids.append(msg["id"])
        except Exception as _qe:
            result["query_hits"].append({"query": query, "hits": 0, "error": str(_qe)})
            continue

    result["scanned"] = len(message_ids)

    # ── Open workbook ─────────────────────────────────────────────────────────
    if not os.path.exists(path):
        raise FileNotFoundError(f"Tracker not found at: {path}")

    wb = openpyxl.load_workbook(path)
    if "Application Tracker" not in wb.sheetnames:
        raise ValueError("Sheet 'Application Tracker' not found in workbook.")
    ws = wb["Application Tracker"]

    # ── Process each email ────────────────────────────────────────────────────
    for msg_id in message_ids:
        try:
            msg = service.users().messages().get(
                userId="me", id=msg_id, format="full"
            ).execute()
        except Exception:
            continue

        try:
            # Extract headers
            headers = {h["name"]: h["value"]
                       for h in msg.get("payload", {}).get("headers", [])}
            subject  = headers.get("Subject", "")
            sender   = headers.get("From", "")
            date_hdr = headers.get("Date", "")

            # Extract body — plain text preferred, HTML fallback
            import re as _re
            payload = msg.get("payload", {})

            def _decode_part(part_data: str) -> str:
                if not part_data:
                    return ""
                return base64.urlsafe_b64decode(part_data).decode("utf-8", errors="ignore")

            def _html_to_text(html: str) -> str:
                """Strip HTML tags and collapse whitespace."""
                text = _re.sub(r"<style[^>]*>.*?</style>", " ", html,
                               flags=_re.DOTALL | _re.IGNORECASE)
                text = _re.sub(r"<script[^>]*>.*?</script>", " ", text,
                               flags=_re.DOTALL | _re.IGNORECASE)
                text = _re.sub(r"<[^>]+>", " ", text)
                text = _re.sub(r"&nbsp;", " ", text)
                text = _re.sub(r"&amp;", "&", text)
                text = _re.sub(r"&lt;", "<", text)
                text = _re.sub(r"&gt;", ">", text)
                return _re.sub(r"\s+", " ", text).strip()

            def _extract_body(part, prefer="text/plain"):
                """Walk MIME tree: return plain text, falling back to HTML→text."""
                mime = part.get("mimeType", "")
                if mime == "text/plain":
                    return _decode_part(part.get("body", {}).get("data", ""))
                if mime == "text/html":
                    return _html_to_text(
                        _decode_part(part.get("body", {}).get("data", ""))
                    )
                # multipart/* — recurse; prefer plain over html
                plain, html = "", ""
                for sub in part.get("parts", []):
                    sub_mime = sub.get("mimeType", "")
                    if sub_mime == "text/plain" and not plain:
                        plain = _decode_part(sub.get("body", {}).get("data", ""))
                    elif sub_mime == "text/html" and not html:
                        html = _html_to_text(
                            _decode_part(sub.get("body", {}).get("data", ""))
                        )
                    elif sub_mime.startswith("multipart/"):
                        nested = _extract_body(sub)
                        if nested and not plain:
                            plain = nested
                return plain or html

            body = _extract_body(payload)

            email_data = {"subject": subject, "sender": sender,
                          "date": date_hdr, "body": body}

            # Rate-limit guard — Groq free tier: ~30 req/min
            import time as _time
            _time.sleep(2)

            llm_result = _parse_email_with_llm(client, email_data)
            reason = llm_result.get("reason", "")
            parsed = llm_result.get("data")

            if reason == "not_relevant":
                result["not_relevant"] += 1
                continue
            if not parsed:
                result["parse_failed"] += 1
                continue

            # Capture first 3 successful parses for debug display
            if len(result["samples"]) < 3:
                result["samples"].append({
                    "subject": subject, "sender": sender,
                    "parsed": parsed,
                })

            company    = (parsed.get("company") or "").strip()
            role_title = (parsed.get("role_title") or "").strip()
            if not company or not role_title:
                result["no_identity"] += 1
                result["unlogged"].append(parsed)
                continue

            existing_row = _check_duplicate(ws, company, role_title)

            if existing_row:
                # UPDATE existing row: status (col 9), response received (col 10),
                # response date (col 11), response type (col 12)
                ws.cell(existing_row, 9).value  = parsed.get("status") or ws.cell(existing_row, 9).value
                ws.cell(existing_row, 10).value = "Yes"
                ws.cell(existing_row, 11).value = parsed.get("response_date")
                ws.cell(existing_row, 12).value = parsed.get("response_type")
                result["updated"] += 1
            else:
                # ADD new row
                last_data_row = 2
                for row in range(ws.max_row, 2, -1):
                    if ws.cell(row, 2).value:
                        last_data_row = row
                        break
                next_row = last_data_row + 1
                last_num = ws.cell(last_data_row, 1).value or 0
                new_num  = (int(last_num) + 1
                            if str(last_num).isdigit()
                            else last_num + 1 if isinstance(last_num, int) else 1)

                cv_variant = _cv_routing(role_title, parsed.get("notes") or "")
                priority   = _auto_priority(parsed.get("response_type") or "")

                row_values = [
                    new_num,
                    date.today().strftime("%d-%b-%y"),
                    company,
                    role_title,
                    None,                          # Role Family — unknown from email
                    parsed.get("location"),
                    parsed.get("channel"),
                    cv_variant,
                    parsed.get("status") or "Awaiting Response",
                    "Yes" if parsed.get("response_type") != "ATS Confirmation" else "No",
                    parsed.get("response_date"),
                    parsed.get("response_type"),
                    None, None,                    # Interview Stage, Interview Date
                    "No", None,                    # Follow-up Sent?, Follow-up Date
                    parsed.get("notes"),
                    "No",                          # Referral Used?
                    None, None,                    # Contact Name, Contact Email
                    priority,
                ]
                for col_idx, value in enumerate(row_values, start=1):
                    ws.cell(row=next_row, column=col_idx, value=value)
                result["added"] += 1

        except Exception as _ee:
            result["email_errors"] += 1
            result.setdefault("error_samples", [])
            if len(result["error_samples"]) < 3:
                import traceback as _tb
                result["error_samples"].append(_tb.format_exc())
            continue

    wb.save(path)
    return result
