"""
cover_letter.py — Cover letter generator via Groq.
Includes honesty check pre-pass and soften-claims regeneration.
Raises SkipRoleError if signal is SKIP and override not acknowledged.
"""

from openai import OpenAI
import profile as p


class SkipRoleError(ValueError):
    """Raised when the role scored SKIP and override not acknowledged."""


def _build_cl_prompt(jd_text: str, score_data: dict, alignment: dict,
                     soft_claims_to_soften: list = None) -> str:
    signal   = score_data.get("signal", "SKIP")
    company  = score_data.get("inferred_company", "the company")
    role     = score_data.get("inferred_title", "this role")
    lead_metrics = "\n".join(f"  - {m}" for m in alignment.get("lead_metrics", []))
    emphasise    = "\n".join(f"  - {e}" for e in alignment.get("emphasise", []))

    soften_block = ""
    if soft_claims_to_soften:
        lines = "\n".join(
            f"  - AVOID: \"{sc['claim']}\" — USE INSTEAD: \"{sc['reframe']}\""
            for sc in soft_claims_to_soften
        )
        soften_block = f"\n=== CLAIMS TO SOFTEN ===\nReplace these exactly as instructed:\n{lines}\n"

    return f"""\
Write a cover letter for Harshit Gupta applying for: {role} at {company}.

=== APPLICATION CONTEXT ===
Signal: {signal} ({score_data.get('total', '?')}/100)
Positioning note: {alignment.get('positioning_note', 'N/A')}

Lead with these metrics (use at least 3):
{lead_metrics}

Emphasise in the letter:
{emphasise}
{soften_block}
=== CAREER CONTEXT ===
{p.CAREER_SUMMARY}

=== JOB DESCRIPTION ===
{jd_text}

=== VOICE RULES (ALL NON-NEGOTIABLE) ===
{p.VOICE_RULES}

=== OUTPUT INSTRUCTIONS ===
Write the cover letter body only — no date, no address block, no "Dear Hiring Manager" header.
Start directly with the first paragraph.
Do not add any preamble, explanation, or notes after the letter.
Count the words: must be 250-320 words. If you overshoot, cut from para 2.
Final sentence must be direct and confident — no "I look forward to hearing from you."\
"""


def generate_cover_letter(
    client: OpenAI,
    jd_text: str,
    score_data: dict,
    alignment: dict,
    override_acknowledged: bool = False,
    soft_claims_to_soften: list = None,
) -> str:
    signal = score_data.get("signal", "SKIP")
    if signal == "SKIP" and not override_acknowledged:
        raise SkipRoleError(
            f"Role scored SKIP ({score_data.get('total', 0)}/100). "
            "Click 'Apply Anyway' in the Align tab to unlock cover letter generation."
        )

    prompt = _build_cl_prompt(jd_text, score_data, alignment, soft_claims_to_soften)
    response = client.chat.completions.create(
        model=p.MODEL,
        messages=[
            {"role": "system", "content": p.SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.4,
        max_tokens=700,
    )
    return response.choices[0].message.content.strip()
