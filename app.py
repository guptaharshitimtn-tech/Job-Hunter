"""
app.py — Harshit's Job Hunting Tool v2.0
Five tabs: Hunt & Score | Align | Apply | Resume Tailor | Prep
With Cognitive Judgment Layer throughout.
"""

import os
import re
from openai import OpenAI
import streamlit as st
try:
    from dotenv import load_dotenv
except ImportError:  # dotenv not needed on Streamlit Cloud
    def load_dotenv(): pass

import profile as p
import scorer as sc
import aligner as al
import cover_letter as cl
import judgment as jdg
import tailor as tl
import prep as pr
import tracker as tk
import theme as th

# ── Bootstrap ─────────────────────────────────────────────────────────────────
load_dotenv()

st.set_page_config(
    page_title="Job Hunter · Harshit Gupta",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Visual layer: premium dark theme + hero banner ───────────────────────────
st.markdown(th.GLOBAL_CSS, unsafe_allow_html=True)
st.markdown(th.hero_html(), unsafe_allow_html=True)

# ── Session state initialisation ──────────────────────────────────────────────
_state_defaults = {
    # ── Core ──────────────────────────────────────────────────────────────────
    "jd_text":               None,
    "job_locations":         ["Bengaluru"],
    "score_result":          None,
    "strategic_commentary":  None,
    # ── Tab 2 — Align ─────────────────────────────────────────────────────────
    "gap_conflict":          None,
    "alignment":             None,
    "overconfidence_flags":  None,
    "override_acknowledged": False,
    # ── Tab 3 — Apply ─────────────────────────────────────────────────────────
    "honesty_check_done":    False,
    "soft_claims":           None,
    "cover_letter_mode":     None,
    "cover_letter_text":     None,
    # ── Tab 4 — Tailor ────────────────────────────────────────────────────────
    "ats_keywords":          None,
    "company_research":      None,
    "tailored_bullets":      None,
    "cv_summary":            None,
    "cv_docx_bytes":         None,
    # ── Tab 5 — Prep ─────────────────────────────────────────────────────────
    "interview_qa":          None,
    "linkedin_outreach":     None,
    "application_email":     None,
    # ── Role-Type Classifier ──────────────────────────────────────────────────
    "role_type":             None,
    "sales_exec_override":   False,
    # ── Tracker ───────────────────────────────────────────────────────────────
    "tracker_log_result":    None,   # None = not attempted, True = success, str = error
    # ── Tab 6 — LinkedIn Post ─────────────────────────────────────────────────
    "linkedin_post":         None,
    # ── Stream / Drift (v3) ───────────────────────────────────────────────────
    "stream_result":          None,
    "drift_block":            None,
    "drift_acknowledged":     False,
    # ── Tab 7 — Track ────────────────────────────────────────────────────────
    "tracker_last_synced":    None,
    "unlogged_applications":  None,
}
for k, v in _state_defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Sidebar: API key ──────────────────────────────────────────────────────────
_env_key     = os.getenv("GROQ_API_KEY", "").strip()
_placeholder = "paste-your-groq-key-here"
# Streamlit Cloud: key and demo flag come from st.secrets
try:
    _env_key = str(st.secrets.get("GROQ_API_KEY", _env_key)).strip()
    DEMO_MODE = str(st.secrets.get("DEMO_MODE", "false")).lower() == "true"
except Exception:
    DEMO_MODE = False

if DEMO_MODE:
    _api_key = _env_key
    with st.sidebar:
        st.markdown("**Demo build**")
        st.caption("Scoring, alignment, and interview prep tabs are live. "
                   "Tracker and Gmail sync are local-only and hidden here.")
else:
  with st.sidebar:
      st.markdown("**Groq API Key**")
      st.caption("Free at [console.groq.com](https://console.groq.com) — no card needed.")
      _sidebar_key = st.text_input(
          "Groq API Key",
          value=_env_key if (_env_key and _env_key != _placeholder) else "",
          type="password",
          label_visibility="collapsed",
          help="Get a free key: console.groq.com → API Keys → Create",
      )
      _api_key = _sidebar_key.strip() or (_env_key if _env_key != _placeholder else "")

      if _api_key:
          if st.button("Test key", use_container_width=True):
              try:
                  OpenAI(api_key=_api_key, base_url=p.GROQ_BASE_URL).models.list()
                  st.success("Key is valid.")
              except Exception as e:
                  st.error(f"Key rejected: {e}")
      else:
          st.warning("Paste your Groq key above.")

      st.divider()
      # Session state inspector (dev aid)
      with st.expander("Session state", expanded=False):
          st.write({
              "signal":    st.session_state.score_result.get("signal") if st.session_state.score_result else None,
              "override":  st.session_state.override_acknowledged,
              "hc_done":   st.session_state.honesty_check_done,
              "cl_mode":   st.session_state.cover_letter_mode,
          })


def get_client(api_key: str) -> OpenAI | None:
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url=p.GROQ_BASE_URL)


client = get_client(_api_key)


# ── UI helpers ────────────────────────────────────────────────────────────────
SIGNAL_CONFIG = {
    "INVEST":     {"emoji": "🟢", "colour": "#16a34a", "bg": "#f0fdf4"},
    "BORDERLINE": {"emoji": "🟡", "colour": "#ca8a04", "bg": "#fefce8"},
    "SKIP":       {"emoji": "🔴", "colour": "#dc2626", "bg": "#fef2f2"},
}


def signal_badge(signal: str) -> str:
    cfg = SIGNAL_CONFIG.get(signal, {"emoji": "⚪", "colour": "#6b7280", "bg": "#f9fafb"})
    return (
        f'<span style="background:{cfg["bg"]};color:{cfg["colour"]};'
        f'font-weight:700;padding:4px 12px;border-radius:6px;'
        f'border:1px solid {cfg["colour"]};">'
        f'{cfg["emoji"]} {signal}</span>'
    )


def score_bar(score: int, max_val: int = 20) -> str:
    pct = int((score / max_val) * 100)
    colour = "#16a34a" if pct >= 75 else "#ca8a04" if pct >= 50 else "#dc2626"
    return (
        f'<div style="background:#e5e7eb;border-radius:4px;height:8px;width:100%;">'
        f'<div style="background:{colour};width:{pct}%;height:8px;border-radius:4px;"></div>'
        f'</div>'
    )


def no_client_warning():
    st.error(
        "No Groq API key found.\n\n"
        "1. Go to [console.groq.com](https://console.groq.com) → **API Keys** → **Create API Key**\n"
        "2. Paste it in the sidebar, or add `GROQ_API_KEY=...` to `.env`."
    )


def api_error(e: Exception):
    st.error(f"API error: {e}")


def _reset_downstream(from_stage: str):
    """Clear session state from a given stage forward."""
    if from_stage == "jd":
        for k in ("score_result", "strategic_commentary", "gap_conflict",
                  "alignment", "overconfidence_flags", "override_acknowledged",
                  "honesty_check_done", "soft_claims", "cover_letter_mode",
                  "cover_letter_text", "ats_keywords", "company_research",
                  "tailored_bullets", "cv_summary", "cv_docx_bytes",
                  "interview_qa", "linkedin_outreach", "application_email",
                  "role_type", "sales_exec_override", "tracker_log_result",
                  "linkedin_post",
                  "stream_result", "drift_block", "drift_acknowledged"):
            st.session_state[k] = _state_defaults[k]
    elif from_stage == "align":
        for k in ("overconfidence_flags", "honesty_check_done", "soft_claims",
                  "cover_letter_mode", "cover_letter_text",
                  "tailored_bullets", "interview_qa",
                  "linkedin_outreach", "application_email"):
            st.session_state[k] = _state_defaults[k]


def _jd_with_location(jd_text: str) -> str:
    """Append the selected India-wide target locations as scoring context."""
    locs = [l for l in (st.session_state.get("job_locations") or []) if l]
    if not locs:
        return jd_text
    return (
        f"{jd_text}\n\n"
        f"[Candidate target locations across India: {', '.join(locs)}. "
        f"Treat the role as location-viable if it is based in, remote to, or hybrid "
        f"with any of these locations.]"
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — HUNT & SCORE
# ══════════════════════════════════════════════════════════════════════════════

_tab_labels = ["🔍 Hunt & Score", "📐 Align", "✉️ Apply",
               "🎯 Resume Tailor", "🎤 Prep", "💼 LinkedIn Post", "📊 Track"]
if DEMO_MODE:
    tab1, tab2, tab3, tab4, tab5 = st.tabs(_tab_labels[:5])
    st.markdown('<style>.st-key-hidden_tabs{display:none !important;}</style>',
                unsafe_allow_html=True)
    _hidden = st.container(key="hidden_tabs")
    tab6 = tab7 = _hidden
else:
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(_tab_labels)

with tab1:
    st.title("Hunt & Score")
    st.caption(
        "Paste a JD. Get a 5-dimension score, signal, and an honest strategic read "
        "on whether this role is worth the effort."
    )

    if not client:
        no_client_warning()
        st.stop()

    # ── Target location across India ──────────────────────────────────────────
    st.markdown(th.kicker("Target Location · Pan-India"), unsafe_allow_html=True)
    loc_c1, loc_c2 = st.columns([3, 2])
    with loc_c1:
        _sel_cities = st.multiselect(
            "Cities you'd take this role in",
            options=p.JOB_LOCATIONS,
            default=[c for c in st.session_state.job_locations if c in p.JOB_LOCATIONS]
                    or ["Bengaluru"],
            help="Bengaluru, Mumbai, Hyderabad and more. Feeds the score, the tracker, and outreach.",
            key="loc_multiselect",
        )
    with loc_c2:
        _custom_loc = st.text_input(
            "Other cities (comma-separated)",
            placeholder="e.g. Jaipur, Kochi, Coimbatore",
            key="loc_custom",
        )
    _locations = list(_sel_cities)
    if _custom_loc.strip():
        _locations += [c.strip() for c in _custom_loc.split(",") if c.strip()]
    st.session_state.job_locations = _locations
    st.markdown(th.location_chips_html(_locations), unsafe_allow_html=True)

    st.markdown(th.kicker("Job Description"), unsafe_allow_html=True)
    jd_input = st.text_area(
        "Paste the full job description",
        height=300,
        placeholder=(
            "Include title, company, responsibilities, requirements, and preferred qualifications. "
            "The more complete, the more accurate the score."
        ),
        label_visibility="collapsed",
        key="jd_input_widget",
    )

    score_btn = st.button(
        "⚡ Score this JD",
        type="primary",
        disabled=not jd_input or not jd_input.strip(),
    )

    if score_btn and jd_input.strip():
        _reset_downstream("jd")
        st.session_state.jd_text = jd_input.strip()

        with st.spinner("Classifying role type..."):
            try:
                rt = jdg.classify_role_type(client, st.session_state.jd_text)
                st.session_state.role_type = rt
            except Exception:
                st.session_state.role_type = {"role_type": "Other", "rationale": "Classification unavailable."}

        with st.spinner("Classifying career stream..."):
            try:
                sr = sc.classify_stream(client, st.session_state.jd_text)
                st.session_state.stream_result = sr
                if sr.get("drift_risk") in ("Moderate", "High"):
                    drift = jdg.detect_drift(client, sr)
                    st.session_state.drift_block = drift
                    st.session_state.drift_acknowledged = False
                else:
                    st.session_state.drift_block = None
                    st.session_state.drift_acknowledged = False
            except Exception:
                st.session_state.stream_result = None
                st.session_state.drift_block   = None

        if st.session_state.role_type.get("role_type") != "Sales Execution":
            with st.spinner("Scoring against your profile..."):
                try:
                    result = sc.score_jd(client, _jd_with_location(st.session_state.jd_text))
                    st.session_state.score_result = result
                except Exception as e:
                    api_error(e)
                    st.stop()

            if st.session_state.score_result and "error" not in st.session_state.score_result:
                with st.spinner("Generating strategic commentary..."):
                    try:
                        commentary = jdg.strategic_commentary(
                            client,
                            st.session_state.score_result,
                            st.session_state.jd_text,
                        )
                        st.session_state.strategic_commentary = commentary
                    except Exception:
                        st.session_state.strategic_commentary = None

                with st.spinner("Generating LinkedIn post..."):
                    try:
                        st.session_state.linkedin_post = jdg.generate_linkedin_post(
                            client,
                            st.session_state.jd_text,
                            st.session_state.score_result,
                            st.session_state.role_type or {},
                        )
                    except Exception:
                        st.session_state.linkedin_post = None

    # ── Sales Execution override: score on explicit confirmation ──────────────
    if (st.session_state.role_type and
            st.session_state.role_type.get("role_type") == "Sales Execution" and
            st.session_state.sales_exec_override and
            not st.session_state.score_result):
        with st.spinner("Scoring against your profile (override active)..."):
            try:
                result = sc.score_jd(client, _jd_with_location(st.session_state.jd_text))
                st.session_state.score_result = result
            except Exception as e:
                api_error(e)
                st.stop()
        if st.session_state.score_result and "error" not in st.session_state.score_result:
            with st.spinner("Generating strategic commentary..."):
                try:
                    commentary = jdg.strategic_commentary(
                        client,
                        st.session_state.score_result,
                        st.session_state.jd_text,
                    )
                    st.session_state.strategic_commentary = commentary
                except Exception:
                    st.session_state.strategic_commentary = None

            with st.spinner("Generating LinkedIn post..."):
                try:
                    st.session_state.linkedin_post = jdg.generate_linkedin_post(
                        client,
                        st.session_state.jd_text,
                        st.session_state.score_result,
                        st.session_state.role_type or {},
                    )
                except Exception:
                    st.session_state.linkedin_post = None

    # ── Role-Type Block ───────────────────────────────────────────────────────
    if st.session_state.role_type:
        rt      = st.session_state.role_type.get("role_type", "Other")
        rt_note = st.session_state.role_type.get("rationale", "")

        if rt == "Sales Execution":
            st.error(
                f"**Role-Type Block: Sales Execution**\n\n"
                f"{rt_note}\n\n"
                "This role requires quota-carrying sales execution — outside Harshit's core domain "
                "(Revenue Intelligence, RevOps, GTM Strategy). Scoring is blocked by default."
            )
            if not st.session_state.sales_exec_override:
                if st.button("Override — score anyway (I understand the mismatch)", type="secondary"):
                    st.session_state.sales_exec_override = True
                    st.rerun()
            else:
                st.warning(
                    "⚠️ Role type mismatch: this JD was classified as Sales Execution — outside "
                    "Harshit's core domain. The score below reflects dimensional fit but the "
                    "fundamental role type is misaligned."
                )
        else:
            st.info(f"**Role Type:** {rt} — {rt_note}")

    # ── Stream Classification Info ────────────────────────────────────────────
    if st.session_state.stream_result:
        sr = st.session_state.stream_result
        drift_risk = sr.get("drift_risk", "None")
        stream_label = sr.get("primary_stream", "—")
        conf = sr.get("stream_confidence", "—")
        role_type_summary = sr.get("role_type_summary", "")

        if drift_risk == "None":
            st.success(
                f"**Stream:** {stream_label} ({conf} confidence) — "
                f"{role_type_summary}"
            )
        else:
            db = st.session_state.drift_block or {}
            drift_label = db.get("drift_label", drift_risk + " Drift")
            drift_colour = "#dc2626" if drift_risk == "High" else "#ca8a04"
            drift_bg     = "#fef2f2" if drift_risk == "High" else "#fefce8"
            st.markdown(
                f'<div style="background:{drift_bg};border:1px solid {drift_colour};'
                f'padding:12px 16px;border-radius:8px;margin-bottom:8px">'
                f'<strong style="color:{drift_colour}">⚠️ Stream Drift — {drift_label}</strong><br>'
                f'<span>{db.get("drift_summary","")}</span><br>'
                f'<em style="font-size:0.9rem">{db.get("probability_read","")}</em>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Results ───────────────────────────────────────────────────────────────
    if st.session_state.score_result:
        result = st.session_state.score_result

        if "error" in result:
            st.error("Failed to parse score response. Raw output:")
            st.code(result["error"])
        else:
            signal  = result.get("signal", "SKIP")
            total   = result.get("total", 0)
            title   = result.get("inferred_title", "Role")
            company = result.get("inferred_company", "Company")

            st.divider()
            h_col, sig_col = st.columns([3, 1])
            h_col.markdown(f"### {title} · {company}")
            sig_col.markdown(signal_badge(signal), unsafe_allow_html=True)
            h_col.markdown(
                th.location_chips_html(st.session_state.job_locations),
                unsafe_allow_html=True,
            )

            if result.get("knockout"):
                st.error(f"**Knockout flag:** {result.get('knockout_reason', 'Auto-SKIP criteria met.')}")

            st.markdown(
                f"<h1 style='text-align:center;margin:8px 0'>{total}"
                f"<span style='font-size:1.2rem;color:#6b7280'>/100</span></h1>",
                unsafe_allow_html=True,
            )
            st.progress(total / 100)
            st.info(result.get("verdict", ""))

            # 5-dimension breakdown
            st.divider()
            st.subheader("5-Dimension Breakdown")
            dims = result.get("dimensions", {})
            cols = st.columns(5)
            for i, (dim_key, dim_meta) in enumerate(p.SCORING_DIMENSIONS.items()):
                dim_data = dims.get(dim_key, {})
                score    = dim_data.get("score", 0)
                note     = dim_data.get("note", "")
                with cols[i]:
                    st.metric(dim_meta["label"], f"{score}/20")
                    st.markdown(score_bar(score), unsafe_allow_html=True)
                    st.caption(note)

            # Strategic Commentary Block
            if st.session_state.strategic_commentary:
                st.divider()
                st.markdown(
                    '<p style="font-size:0.75rem;font-weight:600;color:#6b7280;'
                    'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px">'
                    'Strategic Commentary</p>',
                    unsafe_allow_html=True,
                )
                cfg = SIGNAL_CONFIG.get(signal, {"colour": "#6b7280", "bg": "#f9fafb"})
                st.markdown(
                    f'<div style="background:{cfg["bg"]};border-left:3px solid {cfg["colour"]};'
                    f'padding:12px 16px;border-radius:0 6px 6px 0;font-style:italic;">'
                    f'{st.session_state.strategic_commentary}</div>',
                    unsafe_allow_html=True,
                )

            # Next step
            st.divider()
            if signal == "INVEST":
                st.markdown(
                    '<div style="background:#f0fdf4;border:2px solid #16a34a;border-radius:8px;'
                    'padding:14px 18px;">'
                    '<strong style="color:#16a34a;font-size:1.05rem">🎯 INVEST — Application pipeline ready</strong><br>'
                    '<span style="color:#374151">Strong dimensional match. Work through the pipeline in order:</span><br>'
                    '<span style="color:#374151">→ <strong>Align</strong> tab: CV variant + emphasis strategy'
                    '&nbsp;&nbsp;→ <strong>Apply</strong> tab: cover letter'
                    '&nbsp;&nbsp;→ <strong>Resume Tailor</strong> tab: ATS-optimised CV download + log to tracker'
                    '&nbsp;&nbsp;→ <strong>Prep</strong> tab: interview Q&A + outreach</span>'
                    '</div>',
                    unsafe_allow_html=True,
                )
            elif signal == "BORDERLINE":
                st.warning("Partial match. The judgment layer will activate in **Align** before proceeding.")
            else:
                st.error("Weak match. Override is available in **Align**, but read the gap analysis first.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ALIGN
# ══════════════════════════════════════════════════════════════════════════════

with tab2:
    st.title("Align")
    st.caption(
        "CV variant recommendation, metrics to lead with, and what to emphasise. "
        "For BORDERLINE/SKIP roles, the judgment layer runs first."
    )

    if not client:
        no_client_warning()
        st.stop()

    if not st.session_state.jd_text or not st.session_state.score_result:
        st.info("Score a JD in the **Hunt & Score** tab first.")
        st.stop()

    scores = st.session_state.score_result
    signal = scores.get("signal", "SKIP")

    st.markdown(
        f"**{scores.get('inferred_title', 'Role')}** · "
        f"{scores.get('inferred_company', 'Company')} · "
        + signal_badge(signal),
        unsafe_allow_html=True,
    )
    st.divider()

    # ── Drift Gate ────────────────────────────────────────────────────────────
    if st.session_state.drift_block and not st.session_state.drift_acknowledged:
        db = st.session_state.drift_block
        drift_label = db.get("drift_label", "Stream Drift")
        is_hard = drift_label == "Hard Drift"
        drift_colour = "#dc2626" if is_hard else "#ca8a04"
        drift_bg     = "#fef2f2" if is_hard else "#fefce8"
        st.markdown(
            f'<div style="background:{drift_bg};border:1px solid {drift_colour};'
            f'padding:14px 18px;border-radius:8px;margin-bottom:12px">',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'**Drift Warning — {drift_label}**\n\n'
            f'{db.get("drift_summary","")}\n\n'
            f'*{db.get("probability_read","")}*\n\n'
            f'**If proceeding:** {db.get("positioning_note","")}'
        )
        st.markdown('</div>', unsafe_allow_html=True)
        st.divider()

        btn_label = (
            "Hard Drift — proceed with caution (I accept the positioning constraints)"
            if is_hard else
            "I understand the stream drift. Proceed to alignment."
        )
        if st.button(btn_label, type="primary" if not is_hard else "secondary",
                     key="drift_ack_btn"):
            st.session_state.drift_acknowledged = True
            st.rerun()
        st.stop()

    # ── Judgment block for BORDERLINE / SKIP ─────────────────────────────────
    if signal in ("BORDERLINE", "SKIP") and not st.session_state.override_acknowledged:

        # Run conflict detection if not yet done
        if not st.session_state.gap_conflict:
            with st.spinner("Running conflict detection..."):
                try:
                    gap = jdg.detect_conflict(
                        client,
                        scores,
                        st.session_state.jd_text,
                    )
                    st.session_state.gap_conflict = gap
                except Exception as e:
                    api_error(e)
                    st.stop()

        gap = st.session_state.gap_conflict
        cfg = SIGNAL_CONFIG.get(signal, {"colour": "#6b7280", "bg": "#f9fafb"})

        st.markdown(
            f'<div style="background:{cfg["bg"]};border:1px solid {cfg["colour"]};'
            f'padding:16px;border-radius:8px;margin-bottom:16px">',
            unsafe_allow_html=True,
        )

        if signal == "SKIP":
            st.error("**Gap Conflict — SKIP Signal**")
        else:
            st.warning("**Gap Conflict — BORDERLINE Signal**")

        st.markdown("**Specific gaps driving this score:**")
        for g in gap.get("specific_gaps", []):
            st.markdown(f"- {g}")

        st.markdown(f"**Most likely screening knockout:** {gap.get('likely_knockout', '—')}")
        st.markdown(f"*{gap.get('conditional_note', '')}*")
        st.markdown('</div>', unsafe_allow_html=True)

        st.divider()

        warn_text = (
            "⚠️ This role scored **SKIP**. Applying is unlikely to yield a callback without a referral or warm intro. "
            "Override is available, but the gaps above are real."
            if signal == "SKIP"
            else
            "This role scored **BORDERLINE**. The gaps above are the honest constraints. "
            "Proceed only if you have a tailoring angle or referral that addresses them."
        )
        st.warning(warn_text)

        if st.button(
            "I understand the gaps. Generate alignment anyway.",
            type="primary",
            key="override_btn",
        ):
            st.session_state.override_acknowledged = True
            _reset_downstream("align")
            st.rerun()

        st.stop()   # Don't render alignment until override clicked

    # ── Alignment generation ──────────────────────────────────────────────────
    align_btn = st.button(
        "📐 Get Alignment Advice",
        type="primary",
        disabled=bool(st.session_state.alignment),
    )

    if align_btn:
        _reset_downstream("align")
        with st.spinner("Analysing alignment..."):
            try:
                alignment = al.get_alignment(client, st.session_state.jd_text, scores)
                st.session_state.alignment = alignment
            except Exception as e:
                api_error(e)
                st.stop()

    if not st.session_state.alignment:
        st.stop()

    aln = st.session_state.alignment

    if "error" in aln:
        st.error("Failed to parse alignment response. Raw output:")
        st.code(aln["error"])
        st.stop()

    # ── Overconfidence check ──────────────────────────────────────────────────
    if st.session_state.overconfidence_flags is None:
        with st.spinner("Running overconfidence guard..."):
            try:
                flags = jdg.overconfidence_check(
                    client,
                    aln,
                    st.session_state.jd_text,
                )
                st.session_state.overconfidence_flags = flags
            except Exception:
                st.session_state.overconfidence_flags = []

    flags = st.session_state.overconfidence_flags
    if flags:
        st.divider()
        st.markdown(
            '<p style="font-size:0.75rem;font-weight:600;color:#92400e;'
            'text-transform:uppercase;letter-spacing:0.08em">Overconfidence Guard</p>',
            unsafe_allow_html=True,
        )
        for f in flags:
            with st.expander(f"⚠️ {f.get('recommendation', 'Flag')}", expanded=True):
                st.write(f"**Risk:** {f.get('conflict', '')}")
                st.success(f"**Suggested reframe:** {f.get('suggested_reframe', '')}")

    # ── Alignment output ──────────────────────────────────────────────────────
    st.divider()
    variant_code = aln.get("recommended_variant", "01")
    variant_name = aln.get("variant_name", p.CV_VARIANTS.get(variant_code, {}).get("name", ""))
    st.subheader(f"CV Variant: [{variant_code}] {variant_name}")
    st.write(aln.get("variant_rationale", ""))
    st.divider()

    col_em, col_de = st.columns(2)
    with col_em:
        st.subheader("Lead with these metrics")
        for m in aln.get("lead_metrics", []):
            st.markdown(f"✅ **{m}**")
        st.subheader("Emphasise")
        for e in aln.get("emphasise", []):
            st.markdown(f"→ {e}")

    with col_de:
        st.subheader("De-emphasise / Leave out")
        for d in aln.get("de_emphasise", []):
            st.markdown(f"⬇️ {d}")
        gaps = [g for g in aln.get("gap_flags", []) if g]
        if gaps:
            st.subheader("Gap flags")
            for g in gaps:
                st.markdown(f"⚠️ {g}")

    st.divider()
    st.subheader("Positioning Note")
    st.write(aln.get("positioning_note", ""))

    if signal in ("INVEST", "BORDERLINE") or st.session_state.override_acknowledged:
        st.info("Ready to generate your cover letter? Switch to the **Apply** tab.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — APPLY
# ══════════════════════════════════════════════════════════════════════════════

with tab3:
    st.title("Apply")
    st.caption(
        "Generates a tailored cover letter in Harshit's voice. "
        "Honesty check runs first to flag claims that won't survive a screening call."
    )

    if not client:
        no_client_warning()
        st.stop()

    if not st.session_state.jd_text or not st.session_state.score_result:
        st.info("Score a JD in the **Hunt & Score** tab first.")
        st.stop()

    scores = st.session_state.score_result
    aln    = st.session_state.alignment
    signal = scores.get("signal", "SKIP")

    st.markdown(
        f"**{scores.get('inferred_title', 'Role')}** · "
        f"{scores.get('inferred_company', 'Company')} · "
        + signal_badge(signal),
        unsafe_allow_html=True,
    )

    if not aln:
        st.info("Run **Align** first — the cover letter uses your alignment recommendations.")
        st.stop()

    # Block if SKIP and no override
    if signal == "SKIP" and not st.session_state.override_acknowledged:
        st.error(
            f"**Cover letter generation is blocked.**\n\n"
            f"This role scored SKIP ({scores.get('total', 0)}/100). "
            "Go to the **Align** tab, read the gap analysis, and click "
            "'I understand the gaps. Generate alignment anyway.' to unlock this tab."
        )
        st.stop()

    st.divider()
    col_cv, col_met = st.columns(2)
    col_cv.markdown(f"**CV Variant:** [{aln.get('recommended_variant', '?')}] {aln.get('variant_name', '')}")
    col_met.markdown("**Lead metrics:** " + " · ".join(aln.get("lead_metrics", [])))
    st.divider()

    # ── Honesty Check ─────────────────────────────────────────────────────────
    if not st.session_state.honesty_check_done:
        with st.spinner("Running honesty check..."):
            try:
                soft_claims = jdg.honesty_check(client, aln, st.session_state.jd_text)
                st.session_state.soft_claims      = soft_claims
                st.session_state.honesty_check_done = True
            except Exception:
                st.session_state.soft_claims        = []
                st.session_state.honesty_check_done = True

    soft_claims = st.session_state.soft_claims or []

    if soft_claims and st.session_state.cover_letter_mode is None:
        st.markdown(
            '<p style="font-size:0.75rem;font-weight:600;color:#7c3aed;'
            'text-transform:uppercase;letter-spacing:0.08em">Honesty Check</p>',
            unsafe_allow_html=True,
        )
        for sc_item in soft_claims:
            with st.expander(f"⚠️ Soft claim: \"{sc_item.get('claim', '')}\"", expanded=True):
                st.write(f"**Concern:** {sc_item.get('concern', '')}")
                st.success(f"**Suggested reframe:** {sc_item.get('reframe', '')}")

        st.divider()
        col_keep, col_soften = st.columns(2)
        if col_keep.button("Keep as written", use_container_width=True):
            st.session_state.cover_letter_mode = "keep"
            st.rerun()
        if col_soften.button("Soften claims", type="primary", use_container_width=True):
            st.session_state.cover_letter_mode = "soften"
            st.rerun()
        st.stop()   # Wait for user choice

    elif not soft_claims and st.session_state.cover_letter_mode is None:
        st.success("Honesty check passed — no soft claims detected.")
        st.session_state.cover_letter_mode = "keep"

    # ── Cover letter generation ───────────────────────────────────────────────
    mode = st.session_state.cover_letter_mode

    if mode and not st.session_state.cover_letter_text:
        claims_to_soften = soft_claims if mode == "soften" else None
        with st.spinner("Drafting your cover letter..."):
            try:
                letter = cl.generate_cover_letter(
                    client,
                    st.session_state.jd_text,
                    scores,
                    aln,
                    override_acknowledged=st.session_state.override_acknowledged,
                    soft_claims_to_soften=claims_to_soften,
                )
                st.session_state.cover_letter_text = letter
            except cl.SkipRoleError as e:
                st.error(str(e))
                st.stop()
            except Exception as e:
                api_error(e)
                st.stop()

    if st.session_state.cover_letter_text:
        letter     = st.session_state.cover_letter_text
        word_count = len(letter.split())

        if mode == "soften" and soft_claims:
            st.info(f"Claims softened ({len(soft_claims)} reframed).")

        if 250 <= word_count <= 320:
            st.success(f"Word count: {word_count} — within target (250-320).")
        else:
            st.warning(f"Word count: **{word_count}** (target: 250-320). Regenerate if significantly off.")

        st.text_area("Cover Letter", value=letter, height=420, key="cl_output")

        # Voice rules checklist
        st.divider()
        st.subheader("Voice Rules Checklist")
        st.caption("Verify before sending.")
        checks = [
            ("No em-dashes (—)",                   "—" not in letter),
            ("No banned words (excited/passionate/leverage/synergies/dynamic)",
             all(w not in letter.lower() for w in ["excited", "passionate", "leverage", "synergies", "dynamic"])),
            ("No symmetrical phrasing",
             "not only" not in letter.lower() and "both " not in letter.lower()),
            ("No flattery opener",
             not any(letter.lower().startswith(x) for x in ["i was thrilled", "i am thrilled", "i was excited"])),
            ("Does not end with 'I look forward'",  "i look forward" not in letter.lower()),
            (f"Word count 250-320 (actual: {word_count})",  250 <= word_count <= 320),
        ]
        for label, passed in checks:
            st.markdown(f"{'✅' if passed else '❌'} {label}")

        st.divider()
        if st.button("🔄 Regenerate", help="Clears the current letter and reruns generation."):
            st.session_state.cover_letter_text = None
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — RESUME TAILOR
# ══════════════════════════════════════════════════════════════════════════════

with tab4:
    st.title("Resume Tailor")
    st.caption(
        "ATS keyword gap analysis + tailored bullet rewrites grounded in your real experience. "
        "Run Align first — the bullet generator uses your alignment recommendations."
    )

    if not client:
        no_client_warning()
        st.stop()

    if not st.session_state.jd_text or not st.session_state.score_result:
        st.info("Score a JD in **Hunt & Score** first.")
        st.stop()

    scores  = st.session_state.score_result
    signal  = scores.get("signal", "SKIP")

    st.markdown(
        f"**{scores.get('inferred_title','Role')}** · "
        f"{scores.get('inferred_company','Company')} · "
        + signal_badge(signal),
        unsafe_allow_html=True,
    )
    st.divider()

    # ── Section 1: ATS Keyword Gap ────────────────────────────────────────────
    st.subheader("ATS Keyword Gap")

    if not st.session_state.ats_keywords:
        if st.button("🔍 Analyse ATS Keywords", type="primary"):
            with st.spinner("Extracting and classifying ATS keywords..."):
                try:
                    ats = tl.extract_ats_keywords(client, st.session_state.jd_text)
                    st.session_state.ats_keywords = ats
                    st.rerun()
                except Exception as e:
                    api_error(e)

    if st.session_state.ats_keywords:
        ats = st.session_state.ats_keywords
        match_pct = ats.get("match_pct", 0)
        match_colour = "#16a34a" if match_pct >= 70 else "#ca8a04" if match_pct >= 45 else "#dc2626"

        # Match meter
        st.markdown(
            f"<h2 style='text-align:center;margin:4px 0'>"
            f"<span style='color:{match_colour}'>{match_pct}%</span>"
            f"<span style='font-size:1rem;color:#6b7280'> keyword match</span></h2>",
            unsafe_allow_html=True,
        )
        st.progress(match_pct / 100)
        st.divider()

        col_present, col_missing = st.columns(2)

        with col_present:
            st.markdown("**Present in your profile**")
            for kw in ats.get("present", []):
                st.markdown(f"✅ {kw}")

        with col_missing:
            if ats.get("missing_critical"):
                st.markdown("**Missing — Critical (must-have)**")
                for kw in ats.get("missing_critical", []):
                    st.markdown(f"🔴 {kw}")
            if ats.get("missing_secondary"):
                st.markdown("**Missing — Nice-to-have**")
                for kw in ats.get("missing_secondary", []):
                    st.markdown(f"🟡 {kw}")

        st.divider()

        # ── Section 2: Company Research ───────────────────────────────────────
        st.subheader("Company Research")
        st.caption(
            "Analyses the JD to extract the company's GTM challenge, commercial model, "
            "and the strongest positioning angle — used to tailor bullets and summary precisely."
        )

        if not st.session_state.company_research:
            if st.button("🏢 Research Company", type="primary"):
                company_name = scores.get("inferred_company", "the company")
                with st.spinner(f"Researching {company_name} from JD signals..."):
                    try:
                        cr = tl.research_company(
                            client,
                            company_name,
                            st.session_state.jd_text,
                        )
                        st.session_state.company_research = cr
                        st.rerun()
                    except Exception as e:
                        api_error(e)

        if st.session_state.company_research:
            cr = st.session_state.company_research
            with st.expander("Company Intelligence", expanded=True):
                if cr.get("company_type"):
                    st.markdown(f"**Type:** {cr['company_type']}")
                if cr.get("commercial_model"):
                    st.markdown(f"**Commercial model:** {cr['commercial_model']}")
                if cr.get("gtm_challenge"):
                    st.markdown(f"**GTM challenge this role solves:** {cr['gtm_challenge']}")
                if cr.get("key_priorities"):
                    st.markdown("**Key priorities:**")
                    for pri in cr["key_priorities"]:
                        st.markdown(f"  · {pri}")
                if cr.get("positioning_angle"):
                    st.markdown(
                        f"**Strongest positioning angle:**  \n"
                        f"_{cr['positioning_angle']}_"
                    )
                if cr.get("keywords_to_emphasise"):
                    st.markdown(
                        "**Keywords to embed:** "
                        + "  ·  ".join(f"`{k}`" for k in cr["keywords_to_emphasise"])
                    )
            if st.button("🔄 Re-research company"):
                st.session_state.company_research  = None
                st.session_state.tailored_bullets  = None
                st.session_state.cv_summary        = None
                st.session_state.cv_docx_bytes     = None
                st.rerun()

        st.divider()

        # ── Section 3: Tailored Bullets ───────────────────────────────────────
        st.subheader("Tailored XYZ Resume Bullets")
        st.caption(
            "XYZ format: **bold X** (challenge/context/scale) + regular Y (what was architected) "
            "+ Z (quantified result). Every critical ATS keyword embedded. "
            "Grounded in real experience only — no fabrication."
        )

        if not st.session_state.alignment:
            st.warning("Run **Align** (Tab 2) first — the bullet generator uses your alignment recommendations.")
        else:
            if not st.session_state.tailored_bullets:
                if st.button("✍️ Generate XYZ Bullets", type="primary"):
                    with st.spinner("Writing XYZ ownership bullets targeting ATS keywords..."):
                        try:
                            bullets = tl.generate_tailored_bullets(
                                client,
                                st.session_state.jd_text,
                                st.session_state.alignment,
                                ats,
                                company_research=st.session_state.company_research,
                            )
                            st.session_state.tailored_bullets = bullets
                            st.rerun()
                        except Exception as e:
                            api_error(e)

            if st.session_state.tailored_bullets:
                bullets = st.session_state.tailored_bullets
                st.caption(
                    f"**{len(bullets)} bullets generated.** "
                    "Rewrites of your existing experience — not fabrications. "
                    "⚠️ verify = slight stretch, check before submitting."
                )
                for i, b in enumerate(bullets):
                    stretch_flag = " ⚠️ verify" if b.get("stretch") else ""
                    label = f"[{b.get('role','?')}] {b.get('keyword_hit','?')}{stretch_flag}"
                    with st.expander(label, expanded=(i < 3)):
                        bold_part = b.get("bold_part", "")
                        rest_part = b.get("rest_part", "")
                        if bold_part:
                            # Show XYZ preview
                            st.markdown(
                                f"**{bold_part}**{rest_part}",
                                unsafe_allow_html=False,
                            )
                            st.text_area(
                                "Bold part (X — paste as bold in your CV)",
                                value=bold_part,
                                height=60,
                                key=f"bold_{i}",
                            )
                            st.text_area(
                                "Rest (Y+Z — paste as regular weight)",
                                value=rest_part,
                                height=80,
                                key=f"rest_{i}",
                            )
                        else:
                            # Legacy fallback
                            st.text_area(
                                "Bullet",
                                value=b.get("tailored", ""),
                                height=80,
                                key=f"bullet_{i}",
                            )

                st.divider()
                if st.button("🔄 Regenerate bullets"):
                    st.session_state.tailored_bullets = None
                    st.session_state.cv_summary       = None
                    st.session_state.cv_docx_bytes    = None
                    st.rerun()

        # ── Download Tailored CV ───────────────────────────────────────────────
        st.divider()
        st.subheader("Download Tailored CV")
        st.caption(
            "A4, Calibri 9.5pt, consultancy format. XYZ bullets embedded. "
            "ATS-safe: no text boxes, no columns, standard section names."
        )

        can_download = bool(st.session_state.alignment)
        if not can_download:
            st.warning("Run **Align** first to enable CV download.")
        else:
            if not st.session_state.cv_summary:
                if st.button("🏗️ Build Tailored CV (.docx)", type="primary"):
                    with st.spinner("Generating JD-specific professional summary..."):
                        try:
                            summary = tl.generate_cv_summary(
                                client,
                                st.session_state.jd_text,
                                st.session_state.alignment,
                                scores,
                                company_research=st.session_state.company_research,
                            )
                            st.session_state.cv_summary = summary
                        except Exception as e:
                            api_error(e)
                            st.stop()

                    with st.spinner("Assembling CV document..."):
                        try:
                            docx_bytes = tl.build_cv_docx(
                                cv_summary       = st.session_state.cv_summary,
                                tailored_bullets = st.session_state.tailored_bullets or [],
                                alignment        = st.session_state.alignment,
                                score_data       = scores,
                                company_research = st.session_state.company_research,
                            )
                            st.session_state.cv_docx_bytes = docx_bytes
                            st.rerun()
                        except Exception as e:
                            api_error(e)

            if st.session_state.cv_docx_bytes:
                company_slug = re.sub(r"[^a-zA-Z0-9]", "_",
                    scores.get("inferred_company", "Company"))
                variant_code = (st.session_state.alignment or {}).get(
                    "recommended_variant", "01")
                filename = f"Harshit_Gupta_CV{variant_code}_{company_slug}.docx"

                st.download_button(
                    label="Download CV (.docx)",
                    data=st.session_state.cv_docx_bytes,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary",
                    use_container_width=True,
                )
                st.caption(
                    f"Filename: `{filename}` — CV variant "
                    f"[{variant_code}] with {len(st.session_state.tailored_bullets or [])} "
                    f"tailored bullets + standard experience bullets."
                )
                if st.button("Rebuild CV"):
                    st.session_state.cv_summary       = None
                    st.session_state.cv_docx_bytes    = None
                    st.session_state.tracker_log_result = None
                    st.rerun()

                # ── Log to Application Tracker ────────────────────────────
                st.divider()
                st.subheader("Log to Application Tracker")
                st.caption(
                    "Adds an entry to your local Excel tracker. "
                    f"File: `{p.TRACKER_PATH}`"
                )

                if st.session_state.tracker_log_result is True:
                    st.success("Application logged to tracker.")
                elif isinstance(st.session_state.tracker_log_result, str):
                    st.error(st.session_state.tracker_log_result)

                if st.session_state.tracker_log_result is not True:
                    _rt   = st.session_state.role_type or {}
                    _sc   = st.session_state.score_result or {}
                    _aln  = st.session_state.alignment   or {}

                    tlog_c1, tlog_c2, tlog_c3 = st.columns(3)
                    with tlog_c1:
                        tlog_platform = st.selectbox(
                            "Platform",
                            ["LinkedIn", "Company Portal", "Naukri", "Foundit/Monster",
                             "Instahyre", "Referral", "Direct", "Other"],
                            key="tlog_platform",
                        )
                        tlog_priority = st.selectbox(
                            "Priority",
                            ["High", "Medium", "Low"],
                            index=1,
                            key="tlog_priority",
                        )
                    with tlog_c2:
                        tlog_location = st.text_input(
                            "Location",
                            value=" / ".join(st.session_state.job_locations) or "India",
                            key="tlog_location",
                        )
                        tlog_referral = st.selectbox(
                            "Referral Used?",
                            ["No", "Yes"],
                            key="tlog_referral",
                        )
                    with tlog_c3:
                        tlog_contact_name = st.text_input(
                            "Contact Name (if referral)",
                            key="tlog_contact_name",
                        )
                        tlog_contact_email = st.text_input(
                            "Contact Email (if referral)",
                            key="tlog_contact_email",
                        )

                    tlog_notes = st.text_input(
                        "Notes (optional)",
                        placeholder="e.g. Applied via referral from X, or JD closed on portal",
                        key="tlog_notes",
                    )

                    if st.button("📊 Log Application to Tracker", type="primary",
                                 use_container_width=True):
                        ok, msg = tk.add_tracker_entry(
                            company       = _sc.get("inferred_company", "Unknown"),
                            role_title    = _sc.get("inferred_title",   "Unknown"),
                            role_family   = _rt.get("role_type",        "Other"),
                            location      = tlog_location,
                            platform      = tlog_platform,
                            cv_variant    = _aln.get("variant_name",    variant_code),
                            priority      = tlog_priority,
                            notes         = tlog_notes,
                            referral      = tlog_referral,
                            contact_name  = tlog_contact_name,
                            contact_email = tlog_contact_email,
                        )
                        st.session_state.tracker_log_result = True if ok else msg
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — PREP
# ══════════════════════════════════════════════════════════════════════════════

with tab5:
    st.title("Prep")
    st.caption(
        "Interview Q&A calibrated to this exact JD, "
        "a LinkedIn connection note, and a cold application email."
    )

    if not client:
        no_client_warning()
        st.stop()

    if not st.session_state.jd_text or not st.session_state.score_result:
        st.info("Score a JD in **Hunt & Score** first.")
        st.stop()

    scores = st.session_state.score_result
    aln    = st.session_state.alignment
    signal = scores.get("signal", "SKIP")

    st.markdown(
        f"**{scores.get('inferred_title','Role')}** · "
        f"{scores.get('inferred_company','Company')} · "
        + signal_badge(signal),
        unsafe_allow_html=True,
    )
    st.divider()

    # ── Section 1: Interview Q&A ──────────────────────────────────────────────
    st.subheader("Interview Q&A")

    if not st.session_state.interview_qa:
        if not aln:
            st.warning("Run **Align** first for more accurate questions (uses your gap flags and emphasis).")
        btn_label = "Generate Interview Q&A" if aln else "Generate Interview Q&A (without alignment)"
        if st.button(f"Generate Interview Q&A", type="primary", key="qa_btn"):
            with st.spinner("Building questions calibrated to this JD..."):
                try:
                    qa = pr.generate_interview_qa(
                        client,
                        st.session_state.jd_text,
                        scores,
                        aln or {},
                    )
                    st.session_state.interview_qa = qa
                    st.rerun()
                except Exception as e:
                    api_error(e)

    if st.session_state.interview_qa:
        TYPE_ICONS = {
            "BEHAVIOURAL":  "🧠",
            "ROLE-SPECIFIC": "🎯",
            "GAP-PROBE":    "⚠️",
            "WHY-US":       "💡",
        }
        for i, qa in enumerate(st.session_state.interview_qa):
            q_type = qa.get("type", "BEHAVIOURAL")
            icon   = TYPE_ICONS.get(q_type, "❓")
            with st.expander(f"{icon} [{q_type}] {qa.get('question','')}", expanded=False):
                st.markdown("**Model Answer**")
                st.write(qa.get("model_answer", ""))
                col_m, col_d = st.columns(2)
                col_m.caption(f"Metric anchor: {qa.get('metric_anchor','—')}")
                col_d.caption(f"Danger: {qa.get('danger_note','—')}")

        st.divider()
        if st.button("🔄 Regenerate Q&A"):
            st.session_state.interview_qa = None
            st.rerun()

    st.divider()

    # ── Section 2: LinkedIn Outreach ──────────────────────────────────────────
    st.subheader("LinkedIn Outreach")

    if not st.session_state.linkedin_outreach:
        if st.button("Generate LinkedIn Message", type="primary"):
            with st.spinner("Writing LinkedIn messages..."):
                try:
                    outreach = pr.generate_linkedin_outreach(
                        client,
                        st.session_state.jd_text,
                        scores,
                    )
                    st.session_state.linkedin_outreach = outreach
                    st.rerun()
                except Exception as e:
                    api_error(e)

    if st.session_state.linkedin_outreach:
        out = st.session_state.linkedin_outreach

        st.markdown("**Connection Request Note** *(≤300 chars)*")
        note     = out.get("connection_note", "")
        note_len = len(note)
        note_colour = "green" if note_len <= 300 else "red"
        st.text_area("", value=note, height=100, key="linkedin_note_out")
        st.markdown(
            f"<span style='color:{note_colour};font-weight:600'>{note_len}/300 characters</span>",
            unsafe_allow_html=True,
        )
        if note_len > 300:
            st.warning(f"Over limit by {note_len - 300} chars — trim before sending.")

        st.divider()
        st.markdown("**InMail** *(≤150 words)*")
        inmail     = out.get("inmail", "")
        inmail_wc  = len(inmail.split())
        st.text_area("", value=inmail, height=160, key="linkedin_inmail_out")
        st.caption(f"{inmail_wc} words")

        st.divider()
        if st.button("🔄 Regenerate outreach"):
            st.session_state.linkedin_outreach = None
            st.rerun()

    st.divider()

    # ── Section 3: Cold Application Email ────────────────────────────────────
    st.subheader("Cold Application Email")

    if not aln:
        st.warning("Run **Align** first for a better-targeted email.")

    if not st.session_state.application_email:
        if st.button("Generate Application Email", type="primary", disabled=not aln):
            with st.spinner("Drafting cold email..."):
                try:
                    email = pr.generate_application_email(
                        client,
                        st.session_state.jd_text,
                        scores,
                        aln or {},
                    )
                    st.session_state.application_email = email
                    st.rerun()
                except Exception as e:
                    api_error(e)

    if st.session_state.application_email:
        email    = st.session_state.application_email
        email_wc = len(email.split())
        st.text_area("Cold Email (editable)", value=email, height=260, key="app_email_out")
        st.caption(f"~{email_wc} words (target: ~150)")
        st.divider()
        if st.button("🔄 Regenerate email"):
            st.session_state.application_email = None
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — LINKEDIN POST
# ══════════════════════════════════════════════════════════════════════════════

with tab6:
    st.title("LinkedIn Post")
    st.caption(
        "A practitioner-grade post surfacing the market signal inside this JD. "
        "Auto-generated after scoring — edit freely before copying."
    )

    if not client:
        no_client_warning()
        st.stop()

    if not st.session_state.score_result:
        st.info("Score a JD in **Hunt & Score** first — the post generates automatically.")
        st.stop()

    scores  = st.session_state.score_result
    signal  = scores.get("signal", "SKIP")
    total   = scores.get("total", 0)
    rt_data = st.session_state.role_type or {}
    rt_label = rt_data.get("role_type", "—")

    # ── Info chips ────────────────────────────────────────────────────────────
    _angle_labels = {
        "market_signal": "Market Signal",
        "skill_gap":     "Skill Gap",
        "tool_insight":  "Tool Insight",
        "contrarian":    "Contrarian Take",
        "framework":     "Framework",
    }
    lp = st.session_state.linkedin_post
    angle_display = _angle_labels.get(lp.get("angle", ""), lp.get("angle", "—")) if lp else "—"

    chip_col1, chip_col2, chip_col3 = st.columns(3)
    chip_col1.metric("Role Type", rt_label)
    chip_col2.metric("Fit Score", f"{total}/100  ({signal})")
    chip_col3.metric("Angle", angle_display)

    st.divider()

    # ── Post area ─────────────────────────────────────────────────────────────
    if lp and lp.get("post"):
        post_text = st.text_area(
            "Post (editable)",
            value=lp.get("post", ""),
            height=300,
            key="linkedin_post_area",
        )
        word_count = len(post_text.split())
        wc_colour = "#16a34a" if 150 <= word_count <= 200 else "#ca8a04"
        st.markdown(
            f"<span style='color:{wc_colour};font-size:0.9rem'>"
            f"{word_count} words (target 150-200)</span>",
            unsafe_allow_html=True,
        )

        st.divider()
        btn_col1, btn_col2 = st.columns(2)

        if btn_col1.button("🔄 Regenerate", use_container_width=True):
            with st.spinner("Generating new post..."):
                try:
                    st.session_state.linkedin_post = jdg.generate_linkedin_post(
                        client,
                        st.session_state.jd_text,
                        scores,
                        rt_data,
                    )
                except Exception as e:
                    api_error(e)
            st.rerun()

        # Clipboard copy via JS
        if btn_col2.button("📋 Copy to Clipboard", use_container_width=True):
            import streamlit.components.v1 as components
            escaped = post_text.replace("`", "\\`").replace("\\", "\\\\")
            components.html(
                f"""<script>
                navigator.clipboard.writeText(`{escaped}`)
                  .then(() => console.log('copied'))
                  .catch(e => console.error(e));
                </script>""",
                height=0,
            )
            st.success("Copied to clipboard.")

    else:
        st.warning("Post generation failed or is still pending. Click Regenerate to try again.")
        if st.button("🔄 Regenerate", type="primary"):
            with st.spinner("Generating post..."):
                try:
                    st.session_state.linkedin_post = jdg.generate_linkedin_post(
                        client,
                        st.session_state.jd_text,
                        scores,
                        rt_data,
                    )
                except Exception as e:
                    api_error(e)
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 — TRACK
# ══════════════════════════════════════════════════════════════════════════════

with tab7:
    st.title("Track")
    st.caption(
        "Auto-sync Gmail application responses into your Excel tracker. "
        "Review pipeline status, unlogged applications, and stream distribution."
    )

    st.divider()

    # ── Section 1: Gmail Sync ─────────────────────────────────────────────────
    st.subheader("Sync Gmail")

    if not client:
        no_client_warning()
        st.stop()

    sync_col1, sync_col2 = st.columns([3, 1])
    with sync_col1:
        days_back = st.slider(
            "Scan emails from the last N days",
            min_value=1, max_value=30, value=7, step=1,
            key="gmail_days_back",
        )
    with sync_col2:
        creds_dir = st.text_input(
            "Credentials folder",
            value=str(os.path.dirname(p.TRACKER_PATH)),
            help="Folder containing credentials.json (from Google Cloud Console)",
            key="gmail_creds_dir",
        )

    if st.session_state.tracker_last_synced:
        st.caption(f"Last synced: {st.session_state.tracker_last_synced}")

    if st.button("📧 Sync Gmail → Tracker", type="primary", use_container_width=True,
                 key="gmail_sync_btn"):
        creds_path = creds_dir.strip() or os.path.dirname(p.TRACKER_PATH)
        creds_file = os.path.join(creds_path, "credentials.json")
        if not os.path.exists(creds_file):
            st.error(
                f"**credentials.json not found** at `{creds_file}`\n\n"
                "To set up Gmail access:\n"
                "1. Go to [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials\n"
                "2. Create an OAuth 2.0 Client ID (Desktop application)\n"
                "3. Download JSON and save as `credentials.json` in the folder above\n"
                "4. Enable the Gmail API for your project"
            )
        else:
            with st.spinner(f"Scanning Gmail for the last {days_back} days..."):
                try:
                    sync_result = tk.update_tracker_from_gmail(
                        client=client,
                        tracker_path=p.TRACKER_PATH,
                        credentials_path=creds_path,
                        days_back=days_back,
                    )
                    from datetime import datetime as _dt
                    st.session_state.tracker_last_synced = _dt.now().strftime("%d %b %Y %H:%M")
                    st.session_state.unlogged_applications = sync_result.get("unlogged", [])
                    st.session_state["_last_sync_result"] = sync_result
                    st.success(
                        f"Sync complete — "
                        f"**{sync_result['added']}** new entries added · "
                        f"**{sync_result['updated']}** rows updated · "
                        f"**{sync_result['scanned']}** emails scanned"
                    )
                    # Debug: per-query hit counts + parse breakdown
                    qhits = sync_result.get("query_hits", [])
                    auto_open = (sync_result["added"] + sync_result["updated"]) == 0
                    with st.expander("🔍 Sync debug", expanded=auto_open):
                        # Per-query counts
                        st.markdown("**Search hits per query:**")
                        for qh in qhits:
                            icon = "✅" if qh["hits"] > 0 else "⬜"
                            err  = f" ⚠️ `{qh.get('error','')}`" if qh.get("error") else ""
                            st.markdown(f"{icon} **{qh['hits']}** — `{qh['query']}`{err}")

                        # Parse outcome breakdown
                        st.divider()
                        st.markdown("**Parse outcomes (of scanned emails):**")
                        st.markdown(
                            f"- 🟢 Added: **{sync_result['added']}** &nbsp; "
                            f"🔄 Updated: **{sync_result['updated']}**\n"
                            f"- ⬜ Not application-related: **{sync_result.get('not_relevant', 0)}**\n"
                            f"- ❌ Parse / body failed: **{sync_result.get('parse_failed', 0)}**\n"
                            f"- ⚠️ No company/role extracted: **{sync_result.get('no_identity', 0)}** → sent to Unlogged\n"
                            f"- 💥 Processing errors: **{sync_result.get('email_errors', 0)}**"
                        )
                        err_samples = sync_result.get("error_samples", [])
                        if err_samples:
                            st.markdown("**Error tracebacks (first 3):**")
                            for es in err_samples:
                                st.code(es, language="python")

                        # Sample parsed payloads
                        samples = sync_result.get("samples", [])
                        if samples:
                            st.divider()
                            st.markdown("**Sample parsed emails (first 3 successes):**")
                            for s in samples:
                                with st.expander(f"📧 {s['subject'][:60]}", expanded=False):
                                    st.caption(f"From: {s['sender']}")
                                    st.json(s["parsed"])
                except FileNotFoundError as exc:
                    st.error(str(exc))
                except RuntimeError as exc:
                    st.error(str(exc))
                except PermissionError:
                    st.error(
                        "Cannot write to tracker — the Excel file is open. "
                        "Close it and try again."
                    )
                except Exception as exc:
                    st.error(f"Sync failed: {exc}")

    st.divider()

    # ── Section 2: Pipeline Status Table ─────────────────────────────────────
    st.subheader("Pipeline Status")

    try:
        if os.path.exists(p.TRACKER_PATH):
            import openpyxl as _ox
            import pandas as _pd
            from datetime import date as _date_cls

            _wb = _ox.load_workbook(p.TRACKER_PATH, read_only=True, data_only=True)
            if "Application Tracker" in _wb.sheetnames:
                _ws = _wb["Application Tracker"]
                _rows = []
                for _row in _ws.iter_rows(min_row=3, values_only=True):
                    if _row[1]:  # Date Applied must exist
                        _rows.append({
                            "Company":       _row[2],
                            "Role":          _row[3],
                            "Date Applied":  str(_row[1]) if _row[1] else "",
                            "Stream":        _row[4] or "—",
                            "Status":        _row[8] or "—",
                            "Priority":      _row[20] or "—",
                            "Response Type": _row[11] or "—",
                        })
                _wb.close()

                if _rows:
                    _df = _pd.DataFrame(_rows)

                    # Filters
                    f_col1, f_col2, f_col3 = st.columns(3)
                    with f_col1:
                        status_filter = st.multiselect(
                            "Filter by Status",
                            options=sorted(_df["Status"].unique().tolist()),
                            key="track_status_filter",
                        )
                    with f_col2:
                        priority_filter = st.multiselect(
                            "Filter by Priority",
                            options=sorted(_df["Priority"].unique().tolist()),
                            key="track_priority_filter",
                        )
                    with f_col3:
                        stream_filter = st.multiselect(
                            "Filter by Stream",
                            options=sorted(_df["Stream"].unique().tolist()),
                            key="track_stream_filter",
                        )

                    _filtered = _df.copy()
                    if status_filter:
                        _filtered = _filtered[_filtered["Status"].isin(status_filter)]
                    if priority_filter:
                        _filtered = _filtered[_filtered["Priority"].isin(priority_filter)]
                    if stream_filter:
                        _filtered = _filtered[_filtered["Stream"].isin(stream_filter)]

                    # Colour-coded display
                    def _row_style(row):
                        if "Interview" in str(row.get("Status", "")):
                            return ["background-color: #d1fae5"] * len(row)
                        if "Reject" in str(row.get("Status", "")):
                            return ["background-color: #fee2e2"] * len(row)
                        return [""] * len(row)

                    st.dataframe(
                        _filtered.style.apply(_row_style, axis=1),
                        use_container_width=True,
                        height=350,
                    )
                    st.caption(
                        "Green = Interview Scheduled · Red = Rejected · "
                        "White = ATS Confirmed / Awaiting"
                    )
                else:
                    st.info("No application entries found in tracker.")
            else:
                st.warning("Sheet 'Application Tracker' not found.")
        else:
            st.warning(f"Tracker file not found at: `{p.TRACKER_PATH}`")
    except Exception as _exc:
        st.error(f"Could not load tracker: {_exc}")

    st.divider()

    # ── Section 3: Unlogged Applications ─────────────────────────────────────
    st.subheader("Unlogged Applications (Pending Review)")

    unlogged = st.session_state.unlogged_applications or []
    if not unlogged:
        st.info("No unlogged applications from last sync.")
    else:
        st.warning(
            f"{len(unlogged)} email(s) detected but not auto-added "
            "(company or role title could not be determined). Review and add manually if needed."
        )
        for i, item in enumerate(unlogged):
            with st.expander(
                f"#{i+1} — {item.get('company','Unknown company')} · {item.get('role_title','Unknown role')}",
                expanded=False,
            ):
                st.json(item)
                if st.button(f"Add to tracker", key=f"unlogged_add_{i}"):
                    company    = item.get("company", "Unknown")
                    role_title = item.get("role_title", "Unknown")
                    if company and role_title and company != "Unknown" and role_title != "Unknown":
                        ok, msg = tk.add_tracker_entry(
                            company       = company,
                            role_title    = role_title,
                            role_family   = None,
                            location      = item.get("location", ""),
                            platform      = item.get("channel", "Other"),
                            cv_variant    = tk._cv_routing(role_title, item.get("notes","") or ""),
                            priority      = tk._auto_priority(item.get("response_type","") or ""),
                            notes         = item.get("notes", ""),
                        )
                        if ok:
                            st.success(msg)
                            unlogged.pop(i)
                            st.session_state.unlogged_applications = unlogged
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("Cannot add — company or role title unknown.")

    st.divider()

    # ── Section 4: Stream Distribution Chart ─────────────────────────────────
    st.subheader("Stream Distribution")

    try:
        if os.path.exists(p.TRACKER_PATH):
            import openpyxl as _ox2
            import pandas as _pd2

            _wb2 = _ox2.load_workbook(p.TRACKER_PATH, read_only=True, data_only=True)
            if "Application Tracker" in _wb2.sheetnames:
                _ws2 = _wb2["Application Tracker"]
                _stream_vals = []
                for _row2 in _ws2.iter_rows(min_row=3, values_only=True):
                    if _row2[1]:
                        _stream_vals.append(str(_row2[4] or "Unknown"))
                _wb2.close()

                if _stream_vals:
                    import collections as _col
                    _counts = dict(_col.Counter(_stream_vals))
                    _df2 = _pd2.DataFrame(
                        {"Stream": list(_counts.keys()), "Applications": list(_counts.values())}
                    ).sort_values("Applications", ascending=False)

                    st.bar_chart(_df2.set_index("Stream"))

                    # Drift warning if Stream 3 or 4 exceeds Stream 1
                    _stream_map = {
                        s: c for s, c in _counts.items()
                        if s not in (None, "None", "Unknown", "—")
                    }
                    _stream1_count = sum(
                        v for k, v in _stream_map.items()
                        if "stream 1" in k.lower() or "revenue intelligence" in k.lower()
                        or "revops" in k.lower()
                    )
                    _stream3_count = sum(
                        v for k, v in _stream_map.items()
                        if "stream 3" in k.lower() or "enablement" in k.lower()
                    )
                    _stream4_count = sum(
                        v for k, v in _stream_map.items()
                        if "stream 4" in k.lower() or "operations" in k.lower()
                        or "research" in k.lower()
                    )
                    if (_stream3_count + _stream4_count) > _stream1_count:
                        st.warning(
                            "**Stream drift detected:** you are applying more to weaker streams "
                            "than your core domain. Review your targeting — Stream 1 "
                            "(Revenue Intelligence) should dominate your pipeline."
                        )
                else:
                    st.info("No data to chart.")
    except Exception as _exc2:
        st.error(f"Could not generate stream chart: {_exc2}")
