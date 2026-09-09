"""
scorer.py — JD scoring logic via Groq (free tier, OpenAI-compatible).
Returns score data + strategic commentary from the judgment layer.
"""

import json
import re
from openai import OpenAI
import profile as p
from llm_utils import repair_json as _repair_json, parse_json as _parse_json


STREAM_CLASSIFICATION_PROMPT = '''\
You are classifying a job description against Harshit Gupta's four career streams.

His streams, ranked by depth of actual experience:

STREAM 1 — Revenue Intelligence (CORE)
Building systems that connect pipeline data, CRM analytics, deal flow intelligence, and market
research into commercial decision-making infrastructure. His AI Market Intelligence Engine,
Power BI Revenue Dashboard, and RAG pipeline live here. His Kroll M&A deal intelligence work
lives here. 10 years of compounding depth.
Keywords: pipeline governance, deal intelligence, revenue analytics, commercial intelligence,
CRM analytics, market intelligence systems, forecasting infrastructure, win-rate analytics.

STREAM 2 — GTM Strategy (STRONG)
Designing go-to-market motions, pursuit frameworks, account targeting, sector entry strategy.
His Global GTM Triage Framework, 131+ pursuits, 67% lead-to-C-suite conversion live here.
Keywords: GTM framework, pursuit strategy, account targeting, territory planning, sales motion
design, commercial strategy, go-to-market architecture.

STREAM 3 — Sales Enablement (REAL BUT THINNER)
Building tools and content that help salespeople perform better. He has done this in service of
Streams 1 and 2, not as a standalone function.
WARNING SIGNALS: LMS platform management, training delivery at scale, content production,
SDR coaching, onboarding curriculum design.

STREAM 4 — Commercial Operations / Secondary Research (WEAKEST)
Support activities, not leadership domains.
WARNING SIGNALS: primary output is research reports, analyst-level scope regardless of title,
procurement function, operations execution.

TASK: Read the JD and return JSON:
{{
  "primary_stream": "Stream 1 / Stream 2 / Stream 3 / Stream 4",
  "stream_confidence": "High / Medium / Low",
  "is_core_fit": true / false,
  "drift_risk": "None / Moderate / High",
  "drift_reason": "one sentence if drift is Moderate or High, else null",
  "role_type_summary": "one sentence: what this role does day to day"
}}

RULES:
- If role is PLG/SaaS product-led motion, flag drift even if GTM keywords present.
  Harshit's GTM experience is enterprise, not product-led.
- If primary output is research reports or market sizing, classify as Stream 4 regardless
  of seniority title.
- If role requires managing 15+ people or P&L ownership, note as scope gap.
- Do not classify as Stream 1 purely because it mentions Power BI or CRM. The role must be
  building or governing intelligence infrastructure, not just using it.

JD TEXT:
{jd_text}\
'''


def classify_stream(client: OpenAI, jd_text: str) -> dict:
    """
    Classify the JD into one of Harshit's four career streams.
    Returns dict with keys: primary_stream, stream_confidence, is_core_fit,
    drift_risk, drift_reason, role_type_summary.
    """
    prompt = STREAM_CLASSIFICATION_PROMPT.format(jd_text=jd_text[:3500])
    try:
        response = client.chat.completions.create(
            model=p.MODEL,
            messages=[
                {"role": "system", "content":
                 "You are a career stream classifier. Return only valid JSON, no markdown fences."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=250,
        )
        from llm_utils import parse_json as _pj
        data = _pj(response.choices[0].message.content.strip())
        valid_streams = {"Stream 1", "Stream 2", "Stream 3", "Stream 4"}
        if not isinstance(data, dict) or data.get("primary_stream") not in valid_streams:
            raise ValueError("invalid primary_stream")
        if data.get("drift_risk") not in {"None", "Moderate", "High"}:
            data["drift_risk"] = "None"
        return data
    except Exception:
        return {
            "primary_stream": "Stream 1",
            "stream_confidence": "Low",
            "is_core_fit": False,
            "drift_risk": "None",
            "drift_reason": None,
            "role_type_summary": "Stream classification unavailable.",
        }


def _build_score_prompt(jd_text: str) -> str:
    dim_block = "\n\n".join(
        f"DIMENSION {i+1} — {v['label']} (0-{v['weight']} points)\n{v['rubric']}"
        for i, v in enumerate(p.SCORING_DIMENSIONS.values())
    )
    knockout_block = "\n".join(f"- {r}" for r in p.KNOCKOUT_RULES)

    return f"""\
Score the following job description against Harshit Gupta's profile using the exact framework below.

=== SCORING FRAMEWORK ===
{dim_block}

=== KNOCKOUT CRITERIA (any one = automatic SKIP, regardless of score) ===
{knockout_block}

=== SIGNAL THRESHOLDS ===
INVEST: 75-100 | BORDERLINE: 55-74 | SKIP: 0-54

=== JOB DESCRIPTION ===
{jd_text}

=== REQUIRED JSON OUTPUT ===
Respond with ONLY valid JSON. No markdown fences, no explanation outside the JSON.

{{
  "dimensions": {{
    "experience_quantum":     {{"score": <0-20>, "note": "<one sentence rationale>"}},
    "industry_alignment":     {{"score": <0-20>, "note": "<one sentence rationale>"}},
    "seniority_fit":          {{"score": <0-20>, "note": "<one sentence rationale>"}},
    "technical_skills_match": {{"score": <0-20>, "note": "<one sentence rationale>"}},
    "domain_depth":           {{"score": <0-20>, "note": "<one sentence rationale>"}}
  }},
  "total": <sum of five scores, 0-100>,
  "signal": "<INVEST|BORDERLINE|SKIP>",
  "knockout": <true|false>,
  "knockout_reason": "<string if knockout=true, else null>",
  "verdict": "<2-3 honest sentences on whether to pursue this role and why>",
  "inferred_title": "<job title from JD>",
  "inferred_company": "<company name from JD, or Unknown>"
}}\
"""


def score_jd(client: OpenAI, jd_text: str) -> dict:
    response = client.chat.completions.create(
        model=p.MODEL,
        messages=[
            {"role": "system", "content": p.SYSTEM_PROMPT},
            {"role": "user",   "content": _build_score_prompt(jd_text)},
        ],
        temperature=0.2,
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"```$",          "", raw, flags=re.MULTILINE)
    raw = raw.strip()

    try:
        data = _parse_json(raw)
    except Exception:
        return {"error": raw}

    if data.get("knockout"):
        data["signal"] = "SKIP"

    dims = data.get("dimensions", {})
    computed_total = sum(v.get("score", 0) for v in dims.values())
    if abs(computed_total - data.get("total", 0)) > 2:
        data["total"] = computed_total
        if not data.get("knockout"):
            t = computed_total
            data["signal"] = "INVEST" if t >= 75 else "BORDERLINE" if t >= 55 else "SKIP"

    return data
