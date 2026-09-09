"""
prep.py — Interview Q&A, LinkedIn outreach, and cold application email.
Tab 5 logic. All functions are independently callable.
"""

from openai import OpenAI
import profile as p
from llm_utils import call_llm, parse_json


# ── Interview Q&A ─────────────────────────────────────────────────────────────

def generate_interview_qa(client: OpenAI, jd_text: str,
                           score_data: dict, alignment: dict) -> list:
    """
    Generate 7 interview Q&A pairs calibrated to this specific JD.
    Mix: 3 behavioural, 2 role-specific, 1 gap-probe, 1 'why us'.

    Returns list of dicts:
      question:      str
      type:          BEHAVIOURAL | ROLE-SPECIFIC | GAP-PROBE | WHY-US
      model_answer:  str  — answer using Harshit's real metrics, STAR-lite structure
      metric_anchor: str  — the canonical metric anchoring the answer
      danger_note:   str  — what NOT to say / where to be careful
    """
    gap_flags    = alignment.get("gap_flags", [])
    emphasise    = alignment.get("emphasise", [])
    role         = score_data.get("inferred_title", "this role")
    company      = score_data.get("inferred_company", "the company")

    prompt = f"""\
Generate 7 interview questions and model answers for Harshit Gupta interviewing for:
{role} at {company}

SCORING CONTEXT: {score_data.get('total', '?')}/100 ({score_data.get('signal', '?')})
EMPHASISE: {', '.join(emphasise)}
GAP FLAGS TO EXPECT PROBING ON: {', '.join(g for g in gap_flags if g) or 'None'}

HARSHIT'S REAL EXPERIENCE:
{p.CAREER_SUMMARY}

CANONICAL METRICS (use exactly — never modify numbers):
{chr(10).join(f'- {v}' for v in p.CANONICAL_METRICS.values())}

JOB DESCRIPTION:
{jd_text[:2500]}

QUESTION MIX — generate exactly:
- 3 × BEHAVIOURAL (Tell me about a time...)
- 2 × ROLE-SPECIFIC (How would you / What is your approach to...)
- 1 × GAP-PROBE (directly probing a gap from the gap flags above)
- 1 × WHY-US (Why this company / role specifically)

MODEL ANSWER RULES:
- STAR-lite: Situation (1 sentence) → Action (2 sentences) → Result (metric)
- Use real metrics from canonical list above
- Max 120 words per answer
- Tone: direct, confident, no corporate fluff

DANGER NOTE: one short sentence on what to avoid saying for that question.

Return ONLY valid JSON array:
[
  {{
    "question":      "...",
    "type":          "BEHAVIOURAL | ROLE-SPECIFIC | GAP-PROBE | WHY-US",
    "model_answer":  "...",
    "metric_anchor": "the specific canonical metric used",
    "danger_note":   "Do not say / avoid..."
  }}
]\
"""
    try:
        raw  = call_llm(client, prompt, temperature=0.4, max_tokens=1800)
        data = parse_json(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []


# ── LinkedIn Outreach ─────────────────────────────────────────────────────────

def generate_linkedin_outreach(client: OpenAI, jd_text: str,
                                score_data: dict) -> dict:
    """
    Generate two LinkedIn message variants.

    Returns dict:
      connection_note: str  — ≤300 chars, for cold connection request
      inmail:          str  — ≤150 words, for direct InMail to hiring manager
    """
    role    = score_data.get("inferred_title", "this role")
    company = score_data.get("inferred_company", "the company")

    prompt = f"""\
Write two LinkedIn messages for Harshit Gupta reaching out about:
{role} at {company}

HIS PROFILE SNAPSHOT:
10 years, Revenue Intelligence & GTM Strategy, WTW (Lead — GB & APAC markets),
£50M+ pipeline influenced, 131+ pursuits governed, 67% triage turnaround reduction.

JOB DESCRIPTION (excerpt):
{jd_text[:1500]}

MESSAGE 1 — CONNECTION NOTE:
- Hard limit: 300 characters (LinkedIn platform limit — count carefully)
- Purpose: cold connection request to hiring manager or relevant contact
- Must mention the specific role
- One concrete hook (a metric or a specific thing about the company/JD)
- No "I saw your job posting and wanted to connect" openers
- No "I am excited about..."
- End with a soft ask, not a hard one

MESSAGE 2 — INMAIL:
- Hard limit: 150 words
- Purpose: direct InMail after connecting, or to recruiter
- Lead with one metric that is relevant to this role
- One sentence on why this specific company
- Close with: a 15-minute call ask, direct and confident

Return ONLY valid JSON:
{{
  "connection_note": "...",
  "inmail":          "..."
}}\
"""
    try:
        raw  = call_llm(client, prompt, temperature=0.4, max_tokens=500)
        data = parse_json(raw)
        return {
            "connection_note": data.get("connection_note", ""),
            "inmail":          data.get("inmail", ""),
        }
    except Exception:
        return {"connection_note": "", "inmail": ""}


# ── Cold Application Email ────────────────────────────────────────────────────

def generate_application_email(client: OpenAI, jd_text: str,
                                score_data: dict, alignment: dict) -> str:
    """
    Generate a cold application email body (~150 words).
    Different from the cover letter: punchy, direct, referral-path style.
    Includes a subject line at the top.

    Returns a plain string.
    """
    role         = score_data.get("inferred_title", "this role")
    company      = score_data.get("inferred_company", "the company")
    lead_metrics = alignment.get("lead_metrics", [])
    positioning  = alignment.get("positioning_note", "")

    prompt = f"""\
Write a cold application email for Harshit Gupta applying to:
{role} at {company}

POSITIONING: {positioning}
LEAD METRICS TO USE (pick 2 most relevant):
{chr(10).join(f'- {m}' for m in lead_metrics)}

JOB DESCRIPTION (excerpt):
{jd_text[:1500]}

FORMAT:
Subject: [subject line here]

[Email body]

RULES:
- Subject line: specific, not generic. Include role name.
- Body: ~120-150 words total
- Para 1 (2 sentences): who you are + one punchy metric relevant to this role
- Para 2 (2 sentences): why this company specifically — one concrete observation about the company/role
- Para 3 (1-2 sentences): what you're sending (resume + cover letter) + direct ask (15-minute call)
- Close: first name only — "Harshit"
- Voice rules: no em-dashes, no "excited / passionate / leverage", no flattery
- Tone: peer to peer, not applicant to gatekeeper

Write only the email. No preamble, no explanation after.\
"""
    try:
        return call_llm(client, prompt, temperature=0.4, max_tokens=400)
    except Exception:
        return ""
