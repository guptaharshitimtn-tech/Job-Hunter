"""
tailor.py — Resume tailoring, ATS keyword gap analysis, and CV docx builder.
Tab 4 logic: keyword extraction → company research → tailored bullets → downloadable .docx CV.

CV format: A4, Calibri 9.5pt, navy section borders, XYZ ownership bullets.
ATS target: 90+ against the specific JD uploaded.
"""

import io
import re
from openai import OpenAI
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import profile as p
from llm_utils import call_llm, parse_json


# ── Colour palette (matching build_cvs.py) ────────────────────────────────────
_NAVY  = RGBColor(0x1F, 0x4E, 0x79)
_DARK  = RGBColor(0x1A, 0x1A, 0x1A)
_BODY  = RGBColor(0x2D, 0x2D, 0x2D)
_LIGHT = RGBColor(0x59, 0x59, 0x59)


# ── ATS Keyword Extraction ────────────────────────────────────────────────────

def extract_ats_keywords(client: OpenAI, jd_text: str) -> dict:
    """
    Extract ATS keywords from the JD and classify them against Harshit's profile.

    Returns:
      must_have:          list  — hard filters ATS will screen on
      nice_to_have:       list  — secondary keywords worth injecting
      present:            list  — keywords already in Harshit's profile
      missing_critical:   list  — must-have keywords NOT in profile
      missing_secondary:  list  — nice-to-have NOT in profile
      match_pct:          int   — rough ATS match percentage
    """
    profile_text = (p.CAREER_SUMMARY + " " +
                    " ".join(p.CANONICAL_METRICS.values())).lower()

    prompt = f"""\
You are an ATS keyword analyst. Extract the most important keywords from this JD
and classify them as must-have (hard ATS filters) vs nice-to-have.

JOB DESCRIPTION:
{jd_text[:3500]}

HARSHIT'S PROFILE CONTEXT (for reference when classifying presence):
{p.CAREER_SUMMARY[:1500]}

Rules:
- must_have: 6-10 terms. These are role-defining or explicitly required. Include exact phrases \
where possible (e.g. "revenue operations" not just "operations").
- nice_to_have: 5-8 terms. Preferred but not eliminatory.
- Focus on skills, tools, methodologies, domain terms — not generic words like "communication".

Return ONLY valid JSON, no markdown fences:
{{
  "must_have":    ["term", "..."],
  "nice_to_have": ["term", "..."]
}}\
"""
    try:
        raw  = call_llm(client, prompt, temperature=0.1, max_tokens=400)
        data = parse_json(raw)
    except Exception:
        return _empty_ats()

    must_have    = data.get("must_have", [])
    nice_to_have = data.get("nice_to_have", [])
    all_kws      = must_have + nice_to_have

    present           = [kw for kw in all_kws if kw.lower() in profile_text]
    missing_critical  = [kw for kw in must_have    if kw.lower() not in profile_text]
    missing_secondary = [kw for kw in nice_to_have if kw.lower() not in profile_text]
    match_pct         = int(len(present) / max(len(all_kws), 1) * 100)

    return {
        "must_have":         must_have,
        "nice_to_have":      nice_to_have,
        "present":           present,
        "missing_critical":  missing_critical,
        "missing_secondary": missing_secondary,
        "match_pct":         match_pct,
    }


def _empty_ats() -> dict:
    return {k: [] if k != "match_pct" else 0
            for k in ("must_have", "nice_to_have", "present",
                      "missing_critical", "missing_secondary", "match_pct")}


# ── Company Research ──────────────────────────────────────────────────────────

def research_company(client: OpenAI, company_name: str, jd_text: str) -> dict:
    """
    Extract structured intelligence about the company from the JD text.
    Used to tailor CV summary and bullet framing to the specific company context.

    Returns:
      company_type:           str  — type of organisation
      commercial_model:       str  — how they generate revenue
      gtm_challenge:          str  — what commercial problem this role solves
      key_priorities:         list — top operational priorities from the JD
      positioning_angle:      str  — strongest angle for Harshit's profile
      keywords_to_emphasise:  list — JD-specific terms to thread through the CV
    """
    prompt = f"""\
You are a strategic research assistant. Based on the job description and company name below,
extract structured intelligence that Harshit Gupta would use to tailor his CV precisely.

COMPANY NAME: {company_name}

JOB DESCRIPTION:
{jd_text[:3000]}

Extract and infer the following. If not explicitly stated, infer from company type and JD signals:

1. COMPANY_TYPE: e.g. "Global Insurance Broker", "SaaS FinTech", "PE-backed Advisory", "GCC/BPO", "B2B SaaS"
2. COMMERCIAL_MODEL: How they generate revenue — e.g. client mandates, SaaS subscriptions, advisory fees
3. GTM_CHALLENGE: What GTM / commercial problem this specific role is designed to solve
4. KEY_PRIORITIES: Top 2-3 operational priorities implied by the JD
5. POSITIONING_ANGLE: The one strongest angle for Harshit to lead with for this company
6. KEYWORDS_TO_EMPHASISE: 4-6 JD-specific terms that must appear naturally in the CV

Return ONLY valid JSON:
{{
  "company_type": "...",
  "commercial_model": "...",
  "gtm_challenge": "...",
  "key_priorities": ["...", "...", "..."],
  "positioning_angle": "...",
  "keywords_to_emphasise": ["...", "...", "...", "..."]
}}\
"""
    try:
        raw = call_llm(client, prompt, temperature=0.2, max_tokens=600)
        return parse_json(raw)
    except Exception:
        return {}


# ── Tailored Bullet Generator ─────────────────────────────────────────────────

def generate_tailored_bullets(client: OpenAI, jd_text: str,
                               alignment: dict, ats: dict,
                               company_research: dict = None) -> list:
    """
    Generate 9 XYZ-format tailored resume bullets grounded in Harshit's real experience.

    XYZ structure (mandatory for 90+ ATS score):
      bold_part  = X — challenge / context / scale that sets up why this mattered.
                       Ends with a colon or em-dash.
      rest_part  = Y + Z — what was architected/built/governed (ownership verbs)
                           + quantified outcome from canonical metrics.

    Returns list of dicts:
      role:        str  — WTW | Kroll | TCS
      keyword_hit: str  — ATS keyword this bullet targets
      bold_part:   str  — X portion (rendered bold in CV)
      rest_part:   str  — Y + Z portion (regular weight)
      stretch:     bool
    """
    positioning    = alignment.get("positioning_note", "")
    company_angle  = (company_research or {}).get("positioning_angle", "")
    priorities     = (company_research or {}).get("key_priorities", [])
    extra_keywords = (company_research or {}).get("keywords_to_emphasise", [])

    # Build full keyword list to embed
    critical  = ats.get("missing_critical", [])
    secondary = ats.get("missing_secondary", [])

    prompt = f"""\
You are writing high-impact, ATS-optimised resume bullets for Harshit Gupta's tailored CV.
Target: 90+ ATS score against the specific JD provided.

=== ROLE CONTEXT ===
Variant: {alignment.get('variant_name', 'Senior Manager, Revenue Operations & GTM Strategy')}
Positioning: {positioning}
Company angle: {company_angle}
Company priorities: {', '.join(priorities) if priorities else 'not specified'}

=== ATS KEYWORDS — EMBED EVERY CRITICAL ONE (at least once, naturally) ===
Critical gaps (MUST appear): {', '.join(critical) if critical else 'None'}
Secondary gaps (SHOULD appear): {', '.join(secondary) if secondary else 'None'}
JD emphasis terms: {', '.join(extra_keywords) if extra_keywords else 'None'}

=== CANONICAL METRICS — USE EXACTLY AS WRITTEN, NEVER MODIFY ===
{chr(10).join(f'- {v}' for v in p.CANONICAL_METRICS.values())}

=== HARSHIT'S ACTUAL EXPERIENCE — ALL BULLETS MUST BE GROUNDED HERE ===
{p.CAREER_SUMMARY}

=== REFERENCE BULLETS (reframe in XYZ — do not copy verbatim) ===
WTW:
{chr(10).join(f'  {b}' for b in p.STANDARD_BULLETS['WTW'])}
Kroll:
{chr(10).join(f'  {b}' for b in p.STANDARD_BULLETS['Kroll'])}
TCS:
{chr(10).join(f'  {b}' for b in p.STANDARD_BULLETS['TCS'])}

=== JOB DESCRIPTION ===
{jd_text[:2500]}

=== XYZ BULLET FORMAT — MANDATORY ===
Every bullet has two parts:

bold_part (X): Sets up the challenge, scale, or context.
  - Ends with a colon or em-dash.
  - Examples:
      "Governed £50M+ pipeline across 131+ commercial pursuits: "
      "Research cycles of 15 days were unsustainable at pursuit scale — "
      "Designed and deployed three interlocking revenue intelligence systems: "
      "With no structured intake model governing commercial demand — "

rest_part (Y+Z): What was architected/built/governed + quantified result.
  - MUST use OWNERSHIP VERBS: Architected, Designed, Governed, Built, Deployed, Led, Drove, Structured
  - MUST include at least one canonical metric (exact figures)
  - 2-4 sentences. No word cap — quality and completeness over brevity.

=== HARD RULES ===
1. Never invent or modify metrics — only reframe canonical figures
2. Harshit ARCHITECTED these systems — never "supported", "assisted", "collaborated"
3. Every critical keyword must appear at least once across the 9 bullets
4. Every bullet must target at least one ATS keyword from the gaps list
5. Seniority: frame as Senior Manager / Lead architect decisions, never analyst tasks
6. BANNED: "results-driven", "passionate", "excited", "leverage", "synergies", "proven track record"
7. No em-dashes WITHIN rest_part sentences — use commas or restructure
8. Generate exactly: 5 WTW bullets + 2 Kroll bullets + 2 TCS bullets

=== OUTPUT FORMAT ===
Return ONLY a valid JSON array — no markdown fences, no commentary:
[
  {{
    "role":        "WTW",
    "keyword_hit": "the specific ATS keyword this bullet targets",
    "bold_part":   "X — challenge/context/scale, ends with colon or dash + space",
    "rest_part":   "Y (architected/built/governed) + Z (quantified outcome)",
    "stretch":     false
  }}
]\
"""
    try:
        raw  = call_llm(client, prompt, temperature=0.25, max_tokens=2500)
        data = parse_json(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []


# ── CV Professional Summary ───────────────────────────────────────────────────

def generate_cv_summary(client: OpenAI, jd_text: str,
                         alignment: dict, score_data: dict,
                         company_research: dict = None) -> str:
    """
    Generate a 3-4 sentence professional summary tailored to this specific JD and company.
    Embeds JD-specific keywords for ATS matching.
    """
    role          = score_data.get("inferred_title", "the role")
    company       = score_data.get("inferred_company", "the company")
    positioning   = alignment.get("positioning_note", "")
    lead_metrics  = alignment.get("lead_metrics", [])
    company_angle = (company_research or {}).get("positioning_angle", "")
    keywords      = (company_research or {}).get("keywords_to_emphasise", [])
    gtm_challenge = (company_research or {}).get("gtm_challenge", "")

    prompt = f"""\
Write a professional CV summary for Harshit Gupta, precisely tailored to this specific role.

Target role: {role}
Target company: {company}
Company's GTM challenge this role solves: {gtm_challenge}
Positioning angle for this company: {company_angle}
Alignment positioning: {positioning}
Lead metrics to anchor: {', '.join(lead_metrics) if lead_metrics else 'use canonical metrics'}
JD-specific keywords to embed naturally: {', '.join(keywords) if keywords else 'None'}

HARSHIT'S PROFILE:
{p.CAREER_SUMMARY}

CANONICAL METRICS (embed at least 2):
{chr(10).join(f'- {v}' for v in p.CANONICAL_METRICS.values())}

RULES:
- 3-4 sentences. No filler. No padding.
- Sentence 1: Who he is + years of experience + primary domain — lead with the most relevant angle
- Sentence 2: The specific system or infrastructure he built most relevant to this JD
- Sentence 3: At least 2 canonical metrics woven in naturally
- Sentence 4 (optional): What specifically he brings to this company's context
- Voice: third person ("Revenue Intelligence professional..." not "I am...")
- NO em-dashes. No AI tells. No "results-driven", "proven track record", "passionate", "excited"
- Do NOT open with the company name or role title
- Embed at least 2 JD-specific keywords naturally — do not force them awkwardly
- Reads like a senior professional's profile paragraph, not a job application

Write ONLY the summary paragraph. No label, no preamble.\
"""
    try:
        return call_llm(client, prompt, temperature=0.2, max_tokens=300)
    except Exception:
        return (
            "Revenue Intelligence and GTM Strategy professional with 10 years designing commercial "
            "intelligence systems, pipeline governance frameworks, and AI-powered research infrastructure "
            "across GB and APAC markets. At Willis Towers Watson, architected three interlocking revenue "
            "intelligence systems — an AI market intelligence engine (Python/TF-IDF), a Revenue Intelligence "
            "Power BI Dashboard (Advanced DAX), and a RAG pipeline for stalled deal detection — collectively "
            "driving a 32% improvement in commercial decision velocity across 131+ governed pursuits "
            "influencing £50M+ annualised pipeline. Team of 6 led across two markets; Google Business "
            "Intelligence Professional certified."
        )


# ── Low-level XML helpers (matching build_cvs.py exactly) ────────────────────

def _get_pPr(para):
    pPr = para._p.find(qn("w:pPr"))
    if pPr is None:
        pPr = OxmlElement("w:pPr")
        para._p.insert(0, pPr)
    return pPr


def _set_para_border(para, side="bottom", color="1F4E79", size=12, space=4):
    pPr  = _get_pPr(para)
    pBdr = pPr.find(qn("w:pBdr"))
    if pBdr is None:
        pBdr = OxmlElement("w:pBdr")
        pPr.append(pBdr)
    el = OxmlElement(f"w:{side}")
    el.set(qn("w:val"),   "single")
    el.set(qn("w:sz"),    str(size))
    el.set(qn("w:space"), str(space))
    el.set(qn("w:color"), color)
    pBdr.append(el)


def _set_para_spacing(para, before=0, after=0, line=None):
    pPr = _get_pPr(para)
    spc = pPr.find(qn("w:spacing"))
    if spc is None:
        spc = OxmlElement("w:spacing")
        pPr.append(spc)
    spc.set(qn("w:before"), str(before))
    spc.set(qn("w:after"),  str(after))
    if line:
        spc.set(qn("w:line"),     str(line))
        spc.set(qn("w:lineRule"), "auto")


def _set_para_indent(para, left=0, hanging=0):
    pPr = _get_pPr(para)
    ind = pPr.find(qn("w:ind"))
    if ind is None:
        ind = OxmlElement("w:ind")
        pPr.append(ind)
    if left:    ind.set(qn("w:left"),    str(left))
    if hanging: ind.set(qn("w:hanging"), str(hanging))


def _run(para, text, bold=False, italic=False, size_pt=9.5,
         color=None, font="Calibri"):
    run = para.add_run(text)
    run.bold           = bold
    run.italic         = italic
    run.font.name      = font
    run.font.size      = Pt(size_pt)
    run.font.color.rgb = color or _BODY
    return run


# ── Paragraph / section builders ─────────────────────────────────────────────

def _add_section_header(doc: Document, text: str) -> None:
    """All-caps bold header with navy bottom rule."""
    para = doc.add_paragraph()
    _set_para_spacing(para, before=160, after=60)
    _set_para_border(para, "bottom", "1F4E79", size=10, space=3)
    _run(para, text.upper(), bold=True, size_pt=10, color=_NAVY)


def _add_job_header(doc: Document, role: str, company: str,
                    dates: str, location: str) -> None:
    p1 = doc.add_paragraph()
    _set_para_spacing(p1, before=120, after=0)
    _run(p1, role, bold=True, size_pt=10, color=_DARK)

    p2 = doc.add_paragraph()
    _set_para_spacing(p2, before=0, after=50)
    _run(p2, company, bold=True, size_pt=9.5, color=_NAVY)
    _run(p2, "   |   ", size_pt=9.5, color=_LIGHT)
    _run(p2, dates, size_pt=9.5, color=_LIGHT)
    _run(p2, "   |   ", size_pt=9.5, color=_LIGHT)
    _run(p2, location, size_pt=9.5, color=_LIGHT)


def _add_promo_note(doc: Document, text: str) -> None:
    para = doc.add_paragraph()
    _set_para_spacing(para, before=0, after=50)
    _run(para, text, italic=True, size_pt=9, color=_LIGHT)


def _add_bullet_xyz(doc: Document, bold_part: str, rest_part: str) -> None:
    """XYZ bullet: bold X (challenge/context) + regular Y+Z (action + result)."""
    para = doc.add_paragraph(style="List Bullet")
    _set_para_spacing(para, before=30, after=30, line=240)
    _set_para_indent(para, left=280, hanging=220)
    pPr   = _get_pPr(para)
    numPr = pPr.find(qn("w:numPr"))
    if numPr is not None:
        pPr.remove(numPr)
    _run(para, "\u2022  ", size_pt=9.5, color=_NAVY)
    _run(para, bold_part, bold=True, size_pt=9.5, color=_DARK)
    _run(para, rest_part, size_pt=9.5, color=_BODY)


def _add_plain_bullet(doc: Document, text: str) -> None:
    para = doc.add_paragraph(style="List Bullet")
    _set_para_spacing(para, before=30, after=30, line=240)
    _set_para_indent(para, left=280, hanging=220)
    pPr   = _get_pPr(para)
    numPr = pPr.find(qn("w:numPr"))
    if numPr is not None:
        pPr.remove(numPr)
    _run(para, "\u2022  ", size_pt=9.5, color=_NAVY)
    _run(para, text, size_pt=9.5, color=_BODY)


def _add_para(doc: Document, text: str, size_pt: float = 9.5,
              color=None, bold: bool = False, before: int = 60,
              after: int = 60, italic: bool = False) -> None:
    para = doc.add_paragraph()
    _set_para_spacing(para, before=before, after=after)
    _run(para, text, bold=bold, italic=italic, size_pt=size_pt,
         color=color or _BODY)


def _add_project(doc: Document, title: str, tags: str, body: str) -> None:
    p1 = doc.add_paragraph()
    _set_para_spacing(p1, before=100, after=20)
    _run(p1, title, bold=True, size_pt=9.5, color=_DARK)

    p2 = doc.add_paragraph()
    _set_para_spacing(p2, before=0, after=40)
    _run(p2, tags, italic=True, size_pt=8.5, color=_LIGHT)

    p3 = doc.add_paragraph()
    _set_para_spacing(p3, before=0, after=60)
    _run(p3, body, size_pt=9.5, color=_BODY)


# ── Bullet assembly ───────────────────────────────────────────────────────────

def _bullets_for_role(role_key: str, tailored: list,
                      min_count: int = 4) -> list:
    """
    Build bullet list for a role.
    Returns list of (bold_part | None, rest_part) tuples.
    Tailored XYZ bullets first; standard fill-ins after if needed.
    """
    seen   = set()
    result = []

    for b in tailored:
        bold_part = (b.get("bold_part") or "").strip()
        rest_part = (b.get("rest_part") or "").strip()

        # Legacy 'tailored' field fallback
        if not bold_part:
            plain = (b.get("tailored") or "").strip()
            if plain:
                key = plain[:25].lower()
                if key not in seen:
                    seen.add(key)
                    result.append((None, plain))
            continue

        key = bold_part[:25].lower()
        if key not in seen:
            seen.add(key)
            result.append((bold_part, rest_part))

    # Fill from standard bullets up to min_count + 3
    for sb in p.STANDARD_BULLETS.get(role_key, []):
        if len(result) >= min_count + 3:
            break
        key = sb[:25].lower()
        if key not in seen:
            seen.add(key)
            result.append((None, sb))

    return result


# ── Role title suffix per variant ─────────────────────────────────────────────

_ROLE_SUFFIX = {
    "01": "Revenue Operations & Commercial Intelligence",
    "02": "GTM Strategy & Commercial Intelligence",
    "03": "Sales Enablement & Knowledge Operations",
    "04": "Commercial Operations & Revenue Excellence",
    "05": "Revenue Operations & Deal Desk",
    "06": "Analytics & Business Intelligence",
    "default": "Revenue Intelligence & GTM Strategy",
}


# ── Main CV builder ───────────────────────────────────────────────────────────

def build_cv_docx(cv_summary: str, tailored_bullets: list,
                  alignment: dict, score_data: dict,
                  company_research: dict = None) -> bytes:
    """
    Assemble a consultancy-standard, ATS-safe CV as a .docx file.

    Format:
    - A4, Calibri 9.5pt, 1.8 cm side margins
    - Navy section headers with bottom border
    - XYZ ownership bullets: bold challenge → regular action + result
    - Correct education: B.Tech Biotechnology, IMT Nagpur 2016
    - Certifications: AI-900, Google BI Prof (In Progress), PL-300 (In Progress)

    Returns raw bytes for st.download_button.
    """
    doc = Document()

    # ── Page setup: A4 ───────────────────────────────────────────────────────
    for section in doc.sections:
        section.page_width    = Cm(21.0)
        section.page_height   = Cm(29.7)
        section.top_margin    = Cm(1.6)
        section.bottom_margin = Cm(1.6)
        section.left_margin   = Cm(1.8)
        section.right_margin  = Cm(1.8)

    style           = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(9.5)
    style.font.color.rgb = _BODY

    # Remove default empty paragraph
    for para in doc.paragraphs:
        para._element.getparent().remove(para._element)

    # Resolve variant
    vk = (alignment.get("recommended_variant") or "default").strip()
    if vk not in p.CV_SUBTITLES:
        vk = "default"

    role_suffix = _ROLE_SUFFIX.get(vk, _ROLE_SUFFIX["default"])

    # ── HEADER ────────────────────────────────────────────────────────────────
    name_p = doc.add_paragraph()
    name_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_para_spacing(name_p, before=0, after=40)
    _run(name_p, p.CONTACT["name"].upper(), bold=True, size_pt=22, color=_NAVY)

    sub_p = doc.add_paragraph()
    sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_para_spacing(sub_p, before=0, after=40)
    _run(sub_p, p.CV_SUBTITLES.get(vk, p.CV_SUBTITLES["default"]),
         size_pt=10, color=_LIGHT)

    # Contact line + navy underline
    ct_p = doc.add_paragraph()
    ct_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_para_spacing(ct_p, before=0, after=80)
    _set_para_border(ct_p, "bottom", "1F4E79", size=12, space=4)
    _run(ct_p,
         f"{p.CONTACT['phone']}  \u00b7  {p.CONTACT['email']}  \u00b7  "
         f"{p.CONTACT['linkedin']}  \u00b7  {p.CONTACT['location']}",
         size_pt=9, color=_LIGHT)

    # Metrics bar — single bold line, grey underline
    metrics_bar  = p.METRICS_BAR.get(vk, p.METRICS_BAR["default"])
    metrics_text = "   |   ".join(
        f"{val} {lbl.replace(chr(10), ' ')}" for val, lbl in metrics_bar
    )
    met_p = doc.add_paragraph()
    met_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_para_spacing(met_p, before=60, after=80)
    _set_para_border(met_p, "bottom", "BBBBBB", size=6, space=4)
    _run(met_p, metrics_text, bold=True, size_pt=9, color=_NAVY)

    # ── PROFESSIONAL SUMMARY ──────────────────────────────────────────────────
    _add_section_header(doc, "Professional Summary")
    _add_para(doc, cv_summary, before=60, after=60)

    # ── PROFESSIONAL EXPERIENCE ───────────────────────────────────────────────
    _add_section_header(doc, "Professional Experience")

    by_role: dict = {}
    for b in (tailored_bullets or []):
        key = (b.get("role") or "WTW").strip()
        by_role.setdefault(key, []).append(b)

    # --- WTW ---
    _add_job_header(doc,
        f"Lead, Client & Industry Insights \u2014 {role_suffix}",
        "Willis Towers Watson (WTW)",
        "2022 \u2013 March 2026",
        "Bengaluru  |  GB & APAC Markets")
    _add_promo_note(doc,
        "Promoted from Senior Analyst to Lead (Feb 2025) \u2014 expanded ownership of "
        f"{role_suffix.lower()} infrastructure, team leadership, and cross-regional delivery governance.")

    for bold_part, rest_part in _bullets_for_role("WTW", by_role.get("WTW", []), min_count=5):
        if bold_part is None:
            _add_plain_bullet(doc, rest_part)
        else:
            _add_bullet_xyz(doc, bold_part, rest_part)

    # --- Kroll ---
    _add_job_header(doc,
        "Senior Knowledge Analyst \u2014 Deal Intelligence & M&A Advisory",
        "Kroll Advisory",
        "2021 \u2013 2022",
        "Mumbai  |  APAC & EMEA Markets")

    for bold_part, rest_part in _bullets_for_role("Kroll", by_role.get("Kroll", []), min_count=2):
        if bold_part is None:
            _add_plain_bullet(doc, rest_part)
        else:
            _add_bullet_xyz(doc, bold_part, rest_part)

    # --- TCS ---
    _add_job_header(doc,
        "Market Analyst \u2014 Commercial Intelligence & Business Analytics",
        "Tata Consultancy Services (TCS)",
        "2016 \u2013 2021",
        "Mumbai  |  BFSI & Manufacturing Verticals")

    for bold_part, rest_part in _bullets_for_role("TCS", by_role.get("TCS", []), min_count=2):
        if bold_part is None:
            _add_plain_bullet(doc, rest_part)
        else:
            _add_bullet_xyz(doc, bold_part, rest_part)

    # ── SIGNATURE PROJECTS ────────────────────────────────────────────────────
    _add_section_header(doc, "Signature Systems & Projects")
    for proj in p.SIGNATURE_PROJECTS.get(vk, p.SIGNATURE_PROJECTS["default"]):
        _add_project(doc, proj["title"], proj["tags"], proj["body"])

    # ── CORE COMPETENCIES ─────────────────────────────────────────────────────
    _add_section_header(doc, "Core Competencies")
    for category, items in p.CORE_COMPETENCIES.get(vk, p.CORE_COMPETENCIES["default"]):
        comp_p = doc.add_paragraph()
        _set_para_spacing(comp_p, before=40, after=20)
        _run(comp_p, f"{category}: ", bold=True, size_pt=9.5, color=_DARK)
        _run(comp_p, items, size_pt=9.5, color=_BODY)

    # ── EDUCATION & CERTIFICATIONS ────────────────────────────────────────────
    _add_section_header(doc, "Education & Certifications")

    edu1 = doc.add_paragraph()
    _set_para_spacing(edu1, before=60, after=30)
    _run(edu1, "B.Tech, Biotechnology", bold=True, size_pt=9.5, color=_DARK)
    _run(edu1, "   \u00b7   Institute of Management Technology, Nagpur   \u00b7   2016",
         size_pt=9.5, color=_LIGHT)

    cert1 = doc.add_paragraph()
    _set_para_spacing(cert1, before=0, after=30)
    _run(cert1, "Google Business Intelligence Professional",
         bold=True, size_pt=9.5, color=_DARK)
    _run(cert1, "   \u00b7   Google / Coursera   \u00b7   In Progress",
         size_pt=9.5, color=_LIGHT)

    cert2 = doc.add_paragraph()
    _set_para_spacing(cert2, before=0, after=30)
    _run(cert2, "Microsoft Certified: Azure AI Fundamentals (AI-900)",
         bold=True, size_pt=9.5, color=_DARK)
    _run(cert2, "   \u00b7   Microsoft", size_pt=9.5, color=_LIGHT)

    cert3 = doc.add_paragraph()
    _set_para_spacing(cert3, before=0, after=60)
    _run(cert3, "Microsoft Power BI Data Analyst Associate (PL-300)",
         bold=True, size_pt=9.5, color=_DARK)
    _run(cert3, "   \u00b7   In Progress", size_pt=9.5, color=_LIGHT)

    # ── TOOLS & PLATFORMS ─────────────────────────────────────────────────────
    _add_section_header(doc, "Tools & Platforms")

    tools = [
        ("Intelligence Platforms",
         "S&P Capital IQ  \u00b7  PitchBook  \u00b7  Bloomberg  \u00b7  Factiva  \u00b7  "
         "D&B Hoovers  \u00b7  FactSet"),
        ("Analytics & AI",
         "Power BI (Advanced DAX)  \u00b7  Python (Pandas, Scikit-learn, TF-IDF/NLP)  \u00b7  "
         "Claude, GPT-4, Copilot"),
        ("CRM & Commercial",
         "Dynamics 365  \u00b7  Salesforce  \u00b7  HubSpot  \u00b7  Excel (Advanced)  \u00b7  "
         "PowerPoint"),
    ]
    for i, (label, items) in enumerate(tools):
        tp = doc.add_paragraph()
        _set_para_spacing(tp, before=(40 if i == 0 else 0), after=20)
        _run(tp, f"{label}: ", bold=True, size_pt=9.5, color=_DARK)
        _run(tp, items, size_pt=9.5, color=_BODY)

    # ── FOOTER ────────────────────────────────────────────────────────────────
    ft = doc.add_paragraph()
    ft.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_para_spacing(ft, before=120, after=0)
    _run(ft,
         "Bengaluru, India  \u00b7  Immediate availability  \u00b7  "
         "Open to on-site and hybrid  \u00b7  References on request",
         italic=True, size_pt=8.5, color=_LIGHT)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
