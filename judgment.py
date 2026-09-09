"""
judgment.py — Cognitive Judgment Layer v2.0
Four components: conflict detection, overconfidence guard, honesty check, strategic commentary.
All functions return plain dicts/lists so they serialise cleanly into st.session_state.
"""

from openai import OpenAI
import profile as p
from llm_utils import call_llm, parse_json

# local aliases to keep function bodies unchanged
def _call(client, prompt, temperature=0.15, max_tokens=900):
    return call_llm(client, prompt, temperature=temperature, max_tokens=max_tokens)

def _parse_json(raw): return parse_json(raw)


# ── Role-Type Classifier ──────────────────────────────────────────────────────

def classify_role_type(client: OpenAI, jd_text: str) -> dict:
    """
    Classify the role type from the JD.
    Returns {"role_type": str, "rationale": str}
    Taxonomy:
      Sales Execution        — quota-carrying, field/inside sales, AE, SDR, BDR
      Sales Enablement       — content, training, playbooks, enablement tools
      Revenue Operations     — RevOps, pipeline governance, CRM ops, deal desk
      Commercial Intelligence — market/competitive intel, research, GTM insights
      Consulting             — advisory, strategy, client-facing consulting
      Other                  — anything that doesn't fit the above
    """
    prompt = f"""\
Classify the following job description into exactly one role type.

Taxonomy (pick the single best fit):
- Sales Execution: quota-carrying sales roles (AE, SDR, BDR, Account Manager with revenue targets)
- Sales Enablement: enablement, training, content, playbooks, sales readiness
- Revenue Operations: RevOps, pipeline governance, CRM operations, deal desk, sales ops
- Commercial Intelligence: market intelligence, competitive research, GTM insights, commercial analytics
- Consulting: advisory, strategy, management consulting, client-facing advisory
- Other: anything that does not clearly fit the above

JOB DESCRIPTION:
{jd_text[:2500]}

Return ONLY valid JSON, no markdown fences:
{{
  "role_type": "one of the six labels above",
  "rationale": "one sentence explaining the classification"
}}\
"""
    try:
        data = _parse_json(_call(client, prompt, temperature=0.1, max_tokens=150))
        valid = {"Sales Execution", "Sales Enablement", "Revenue Operations",
                 "Commercial Intelligence", "Consulting", "Other"}
        if data.get("role_type") not in valid:
            data["role_type"] = "Other"
        return data
    except Exception:
        return {"role_type": "Other", "rationale": "Classification unavailable."}


# ── Drift Detection ───────────────────────────────────────────────────────────

DRIFT_DETECTION_PROMPT = '''\
You are the judgment layer for Harshit Gupta's job search tool.

Stream classification result:
- Primary stream: {primary_stream}
- Drift risk: {drift_risk}
- Drift reason: {drift_reason}
- Role type summary: {role_type_summary}

Stream hierarchy (strongest to weakest):
1. Revenue Intelligence — enterprise, PE-ecosystem, transactions-side
2. GTM Strategy — pursuit frameworks, enterprise commercial motion
3. Sales Enablement — thinner, supporting role in his history
4. Commercial Operations / Research — support function, not a progression

Generate a Drift Warning Block with exactly these fields:
{{
  "drift_label": "Core Fit / Acceptable Stretch / Stream Drift / Hard Drift",
  "drift_summary": "one sentence: what type of role this is vs what Harshit actually does",
  "probability_read": "one sentence: honest callback estimate given drift level",
  "positioning_note": "one sentence: most important framing adjustment if he proceeds",
  "proceed_recommended": true / false
}}

Rules:
- Do not soften if the drift is real.
- Hard Drift = PLG SaaS, pure research delivery, post-trade ops, BPO delivery.
- Stream Drift = Adjacent domain but different context (e.g. B2C vs enterprise).
- Acceptable Stretch = Same domain, slightly different function.
- Core Fit = Direct match to Stream 1 or Stream 2 with enterprise context.\
'''


def detect_drift(client: OpenAI, stream_result: dict) -> dict:
    """
    Generate a Drift Warning Block from stream classification output.
    Only called when drift_risk is Moderate or High.
    Returns a dict with keys: drift_label, drift_summary, probability_read,
    positioning_note, proceed_recommended.
    """
    prompt = DRIFT_DETECTION_PROMPT.format(
        primary_stream=stream_result.get("primary_stream", "Unknown"),
        drift_risk=stream_result.get("drift_risk", "Unknown"),
        drift_reason=stream_result.get("drift_reason") or "Not specified",
        role_type_summary=stream_result.get("role_type_summary") or "Not specified",
    )
    try:
        response = client.chat.completions.create(
            model=p.MODEL,
            messages=[
                {"role": "system", "content":
                 "You are a judgment layer. Return only valid JSON, no markdown fences."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.15,
            max_tokens=300,
        )
        data = _parse_json(response.choices[0].message.content.strip())
        valid_labels = {"Core Fit", "Acceptable Stretch", "Stream Drift", "Hard Drift"}
        if not isinstance(data, dict) or data.get("drift_label") not in valid_labels:
            raise ValueError("invalid drift_label")
        return data
    except Exception:
        return {
            "drift_label": "Stream Drift" if stream_result.get("drift_risk") == "Moderate" else "Hard Drift",
            "drift_summary": stream_result.get("drift_reason") or "Stream classification unavailable.",
            "probability_read": "Callback probability is reduced given the stream mismatch.",
            "positioning_note": "Lead with your enterprise revenue intelligence work, not the adjacent overlap.",
            "proceed_recommended": stream_result.get("drift_risk") == "Moderate",
        }


# ── Component 1: Conflict Detection ──────────────────────────────────────────

def detect_conflict(client: OpenAI, score_data: dict, jd_text: str) -> dict:
    """
    Returns a GapConflictBlock dict:
      specific_gaps:     list[str]
      likely_knockout:   str
      conditional_note:  str
      should_block:      bool  (True = SKIP, False = BORDERLINE)
    """
    signal = score_data.get("signal", "SKIP")
    total  = score_data.get("total", 0)
    dims   = score_data.get("dimensions", {})

    dim_lines = "\n".join(
        f"- {p.SCORING_DIMENSIONS.get(k, {}).get('label', k)}: "
        f"{v.get('score', 0)}/20 — {v.get('note', '')}"
        for k, v in dims.items()
    )

    prompt = f"""\
Harshit Gupta's JD score is {total}/100 (signal: {signal}).

Dimension scores:
{dim_lines}

JOB DESCRIPTION:
{jd_text[:3500]}

Analyse the specific gaps honestly. Do not soften the assessment.
Return ONLY valid JSON, no markdown fences:

{{
  "specific_gaps": [
    "Dimension name: X/20 — specific gap with JD evidence",
    "..."
  ],
  "likely_knockout": "The single most likely screening filter that removes Harshit from this pipeline",
  "conditional_note": "One sentence: the one factor (referral, niche match, internal sponsor) that would meaningfully shift probability",
  "should_block": {str(signal == "SKIP").lower()}
}}\
"""
    try:
        data = _parse_json(_call(client, prompt, temperature=0.1))
        data["should_block"] = (signal == "SKIP")
        return data
    except Exception:
        return {
            "specific_gaps": [
                f"Total score {total}/100 ({signal}) — see dimension breakdown in Hunt & Score tab"
            ],
            "likely_knockout": score_data.get(
                "verdict", "Score below typical screening threshold."
            ),
            "conditional_note": (
                "A referral or warm intro changes this calculus meaningfully."
            ),
            "should_block": signal == "SKIP",
        }


# ── Component 2: Overconfidence Guard ────────────────────────────────────────

def overconfidence_check(client: OpenAI, alignment: dict, jd_text: str) -> list:
    """
    Returns list of OverconfidenceFlag dicts:
      recommendation:    str
      conflict:          str
      suggested_reframe: str
    Empty list = no flags.
    """
    emphasise    = alignment.get("emphasise", [])
    variant_name = alignment.get("variant_name", "")
    positioning  = alignment.get("positioning_note", "")

    prompt = f"""\
Review these alignment recommendations for overconfidence against the JD.

RECOMMENDED CV VARIANT: {variant_name}
POSITIONING NOTE: {positioning}

RECOMMENDED TO EMPHASISE:
{chr(10).join(f'- {e}' for e in emphasise)}

JOB DESCRIPTION:
{jd_text[:3500]}

HARSHIT'S ACTUAL BACKGROUND:
{p.CAREER_SUMMARY}

Flag any recommendation that:
1. May invite questions Harshit cannot answer deeply — specifically: ML lifecycle management,
   cloud architecture, data engineering, P&L ownership, managing teams >10, enterprise SaaS sales.
2. Claims a primary fit where the actual fit is adjacent or secondary.
3. Would overextend beyond what he can defend in a 20-minute screening call.

Return ONLY a valid JSON array. Empty array [] if no flags found.
[
  {{
    "recommendation": "the specific recommendation being flagged",
    "conflict": "why this creates overconfidence risk — be specific about the JD requirement",
    "suggested_reframe": "a more accurate framing that remains compelling but is fully defensible"
  }}
]\
"""
    try:
        data = _parse_json(_call(client, prompt, temperature=0.15))
        return data if isinstance(data, list) else []
    except Exception:
        return []


# ── Component 3: Honesty Check ────────────────────────────────────────────────

def honesty_check(client: OpenAI, alignment: dict, jd_text: str) -> list:
    """
    Pre-generation check for claims that won't survive a screening call.
    Returns list of SoftClaim dicts:
      claim:   str
      concern: str
      reframe: str
    Empty list = no soft claims.
    """
    lead_metrics = alignment.get("lead_metrics", [])
    emphasise    = alignment.get("emphasise", [])
    positioning  = alignment.get("positioning_note", "")

    prompt = f"""\
Before writing a cover letter for Harshit Gupta, identify claims likely to appear
based on the alignment plan below that could be challenged in a 20-minute screening call.

PLANNED LETTER EMPHASIS:
- Lead metrics: {", ".join(lead_metrics)}
- Emphasise:    {", ".join(emphasise)}
- Positioning:  {positioning}

JOB DESCRIPTION:
{jd_text[:3500]}

HARSHIT'S ACTUAL BACKGROUND:
{p.CAREER_SUMMARY}

Identify claims where:
- His experience is adjacent but not direct for this specific role
- The framing overextends beyond what he can defend in conversation
- A screening call would probe and find the gap

Return ONLY a valid JSON array. Empty array [] if no soft claims found.
[
  {{
    "claim": "The specific claim that would appear in the cover letter",
    "concern": "Why this might not survive a detailed screening probe",
    "reframe": "A more accurate framing that is still compelling and fully defensible"
  }}
]\
"""
    try:
        data = _parse_json(_call(client, prompt, temperature=0.15))
        return data if isinstance(data, list) else []
    except Exception:
        return []


# ── Component 4: Strategic Commentary ────────────────────────────────────────

def strategic_commentary(client: OpenAI, score_data: dict, jd_text: str) -> str:
    """
    2-3 sentence honest strategic note on effort-to-probability ratio.
    Returns a plain string.
    """
    signal  = score_data.get("signal", "SKIP")
    total   = score_data.get("total", 0)
    verdict = score_data.get("verdict", "")
    dims    = score_data.get("dimensions", {})

    # Two weakest dimensions
    dim_scores = sorted(
        [(k, v.get("score", 0), v.get("note", "")) for k, v in dims.items()],
        key=lambda x: x[1],
    )
    weak_lines = "\n".join(
        f"- {p.SCORING_DIMENSIONS.get(k, {}).get('label', k)}: {s}/20 — {n}"
        for k, s, n in dim_scores[:2]
    )

    prompt = f"""\
Write a Strategic Commentary for Harshit Gupta about this role.

Score: {total}/100 ({signal})
Verdict: {verdict}

Two weakest dimensions:
{weak_lines}

JOB DESCRIPTION (first 2000 chars):
{jd_text[:2000]}

Rules — ALL non-negotiable:
- Exactly 2-3 sentences. No filler, no padding.
- Not encouraging, not discouraging. Just honest.
- Reference the specific gap(s) that matter most for THIS exact role.
- Include a conditional in the form: 'If [specific factor — referral / sector experience / tool match], the probability shifts meaningfully.'
- Do NOT start with 'This role' or 'Harshit'. Start with the role's primary requirement.
- Tone: senior advisor to a peer, not a coach to a client.

Write only the 2-3 sentences. No label, no header, no preamble.\
"""
    try:
        return _call(client, prompt, temperature=0.3, max_tokens=220)
    except Exception:
        return f"{verdict} (Score: {total}/100, {signal})"


# ── LinkedIn Post Generator ───────────────────────────────────────────────────

def generate_linkedin_post(client: OpenAI, jd_text: str,
                            score_data: dict, role_type: dict) -> dict:
    """
    Generate a LinkedIn post inspired by the market signal in this JD.
    Returns {"angle": str, "post": str}.
    Fires on every score including SKIP — skip-grade roles often carry
    the most interesting contrarian or market signal content.
    """
    total  = score_data.get("total", 0)
    signal = score_data.get("signal", "SKIP")
    dims   = score_data.get("dimensions", {})
    rt     = role_type.get("role_type", "Other")

    dim_lines = "\n".join(
        f"- {p.SCORING_DIMENSIONS.get(k, {}).get('label', k)}: "
        f"{v.get('score', 0)}/20 — {v.get('note', '')}"
        for k, v in dims.items()
    )

    system = """\
You are writing a LinkedIn post for Harshit Gupta — a Revenue Intelligence and GTM Strategy \
professional with 10 years of experience. He is a systems-builder: he builds revenue intelligence \
engines, GTM operating frameworks, and AI-assisted insight pipelines. His voice is analytical, \
direct, and grounded. He never uses hashtag spam, never opens with "Excited to share", never uses \
performative humility.

You are given: a job description, its fit score (/100), the role type classification, and dimension \
score breakdown.

Your task: identify the single most interesting market insight, professional observation, or \
contrarian take that this JD unlocks — something only a practitioner in this space would notice. \
Then write a LinkedIn post around it.

Choose the best angle from this list:
- market_signal: Something about how this industry/function is evolving commercially
- skill_gap: What companies get wrong when they spec this type of role
- tool_insight: Why a specific capability in this JD is becoming table stakes
- contrarian: Everyone's hiring for X — but does X actually move revenue?
- framework: How a practitioner should think about the problem this role solves

Output format — JSON only, no preamble:
{"angle": "", "post": ""}\
"""

    prompt = f"""\
JOB DESCRIPTION:
{jd_text[:3000]}

FIT SCORE: {total}/100 ({signal})
ROLE TYPE: {rt}

DIMENSION SCORES:
{dim_lines}

Write the LinkedIn post now. The post must be 150-200 words. No hashtag spam. \
No opening with "Excited to share". Lead with the insight, not with the person.\
"""

    try:
        response = client.chat.completions.create(
            model=p.MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.4,
            max_tokens=400,
        )
        data = _parse_json(response.choices[0].message.content.strip())
        valid_angles = {"market_signal", "skill_gap", "tool_insight",
                        "contrarian", "framework"}
        if not isinstance(data, dict) or data.get("angle") not in valid_angles:
            raise ValueError("bad angle")
        return data
    except Exception:
        return {"angle": "market_signal", "post": ""}
