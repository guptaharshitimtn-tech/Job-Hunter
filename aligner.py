"""
aligner.py — CV variant routing and alignment advice via Groq (free tier).
"""

import json
import re
from openai import OpenAI
import profile as p


def _keyword_preselect(jd_text: str) -> str | None:
    jd_lower = jd_text.lower()
    scores = {}
    for code, variant in p.CV_VARIANTS.items():
        hits = sum(1 for kw in variant["trigger_keywords"] if kw in jd_lower)
        if hits:
            scores[code] = hits
    if not scores:
        return None
    best_code = max(scores, key=scores.get)
    top_score = scores[best_code]
    if top_score >= 2 and list(scores.values()).count(top_score) == 1:
        return best_code
    return None


def _build_align_prompt(jd_text: str, score_data: dict, preselected: str | None) -> str:
    variants_block = "\n".join(
        f"  [{code}] {v['name']}: {', '.join(v['trigger_keywords'])}"
        for code, v in p.CV_VARIANTS.items()
    )
    metrics_block = "\n".join(f"  - {v}" for v in p.CANONICAL_METRICS.values())
    hint = (
        f"\nKeyword pre-selection suggests variant [{preselected}]. "
        "Confirm or override based on full JD context.\n"
        if preselected else ""
    )

    return f"""\
You are advising Harshit Gupta on how to align his application to this specific job.
{hint}
His total score for this JD: {score_data.get('total', '?')}/100 ({score_data.get('signal', '?')})
Score breakdown: {json.dumps({k: v.get('score') for k, v in score_data.get('dimensions', {}).items()})}

=== CV VARIANTS AVAILABLE ===
{variants_block}

=== CANONICAL METRICS ===
{metrics_block}

=== CAREER CONTEXT ===
{p.CAREER_SUMMARY}

=== JOB DESCRIPTION ===
{jd_text}

=== REQUIRED JSON OUTPUT ===
Respond with ONLY valid JSON. No markdown fences, no preamble.

{{
  "recommended_variant": "<variant code, e.g. 01>",
  "variant_name": "<full variant name>",
  "variant_rationale": "<2 sentences on why this variant fits this JD>",
  "lead_metrics": ["<metric>", "<metric>", "<metric>"],
  "emphasise": ["<what to emphasise>", "<what to emphasise>", "<what to emphasise>"],
  "de_emphasise": ["<what to leave out>", "<what to leave out>"],
  "positioning_note": "<1 paragraph: how Harshit should position himself for this specific role>",
  "gap_flags": ["<honest gap or mismatch, if any>"]
}}\
"""


def get_alignment(client: OpenAI, jd_text: str, score_data: dict) -> dict:
    preselected = _keyword_preselect(jd_text)
    response = client.chat.completions.create(
        model=p.MODEL,
        messages=[
            {"role": "system", "content": p.SYSTEM_PROMPT},
            {"role": "user",   "content": _build_align_prompt(jd_text, score_data, preselected)},
        ],
        temperature=0.3,
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"```$", "", raw, flags=re.MULTILINE)
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": raw}
