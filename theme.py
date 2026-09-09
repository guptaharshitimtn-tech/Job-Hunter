"""
theme.py — Visual layer for the Job Hunter app.
Holds the global CSS, hero banner, and small HTML component helpers.
Keeping all presentation here keeps app.py focused on logic.
"""

import html as _html

# ── Global stylesheet ─────────────────────────────────────────────────────────
GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');

:root{
  --bg-0:#070a14; --bg-1:#0b0f1e; --bg-2:#141a2e;
  --stroke:rgba(129,140,248,0.20);
  --stroke-soft:rgba(255,255,255,0.07);
  --txt:#e6e9f2; --muted:#8b93a7;
  --accent:#818cf8; --accent2:#22d3ee; --accent3:#c084fc;
  --glass:rgba(255,255,255,0.035);
}

/* ── App canvas ── */
.stApp{
  background:
    radial-gradient(920px 520px at 10% -8%, rgba(129,140,248,0.17), transparent 60%),
    radial-gradient(820px 480px at 96% -2%, rgba(34,211,238,0.13), transparent 56%),
    radial-gradient(700px 600px at 80% 110%, rgba(192,132,252,0.10), transparent 60%),
    linear-gradient(180deg,#070a14 0%, #0a0e1c 100%);
  color:var(--txt);
}
[data-testid="stHeader"]{ background:transparent; }
#MainMenu, footer{ visibility:hidden; }
.block-container{ padding-top:2.2rem; max-width:1180px; }

html,body,[class*="css"]{ font-family:'Inter',-apple-system,sans-serif; }
h1,h2,h3,h4{ font-family:'Space Grotesk','Inter',sans-serif !important;
  letter-spacing:-0.02em; color:var(--txt); }
.stCaption,[data-testid="stCaptionContainer"]{ color:var(--muted) !important; }

/* ── Hero banner ── */
.hero{
  position:relative; border-radius:22px; padding:30px 34px; margin-bottom:22px;
  background:linear-gradient(135deg, rgba(129,140,248,0.16), rgba(34,211,238,0.07) 55%, rgba(192,132,252,0.12));
  border:1px solid var(--stroke);
  box-shadow:0 24px 60px -32px rgba(99,102,241,0.55), inset 0 1px 0 rgba(255,255,255,0.05);
  overflow:hidden;
}
.hero::after{
  content:""; position:absolute; right:-60px; top:-60px; width:240px; height:240px;
  background:radial-gradient(circle, rgba(34,211,238,0.30), transparent 70%); filter:blur(6px);
}
.hero-badge{
  display:inline-block; font-size:0.68rem; font-weight:700; letter-spacing:0.18em;
  text-transform:uppercase; color:var(--accent2);
  background:rgba(34,211,238,0.10); border:1px solid rgba(34,211,238,0.30);
  padding:5px 12px; border-radius:999px; margin-bottom:14px;
}
.hero-title{
  font-family:'Space Grotesk',sans-serif; font-size:2.55rem; font-weight:700;
  line-height:1.05; margin:0;
  background:linear-gradient(110deg,#ffffff 10%, #a5b4fc 45%, #67e8f9 90%);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}
.hero-sub{ color:var(--muted); font-size:0.98rem; margin-top:8px; max-width:640px; }
.hero-meta{ margin-top:16px; display:flex; gap:8px; flex-wrap:wrap; }
.hero-pill{
  font-size:0.74rem; font-weight:600; color:var(--txt);
  background:var(--glass); border:1px solid var(--stroke-soft);
  padding:5px 11px; border-radius:8px;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"]{
  gap:5px; background:rgba(255,255,255,0.03); padding:6px;
  border-radius:15px; border:1px solid var(--stroke-soft);
}
.stTabs [data-baseweb="tab"]{
  border-radius:11px; padding:9px 15px; color:var(--muted);
  background:transparent; font-weight:600; font-size:0.88rem;
}
.stTabs [data-baseweb="tab"]:hover{ color:var(--txt); background:rgba(255,255,255,0.04); }
.stTabs [aria-selected="true"]{
  background:linear-gradient(135deg, rgba(129,140,248,0.95), rgba(34,211,238,0.80));
  color:#070a14 !important;
  box-shadow:0 8px 22px -8px rgba(129,140,248,0.7);
}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"]{ background:transparent; }

/* ── Buttons ── */
.stButton > button, .stDownloadButton > button{
  border-radius:12px; font-weight:600; font-size:0.9rem;
  border:1px solid var(--stroke); background:rgba(255,255,255,0.045);
  color:var(--txt); transition:all .18s ease; padding:0.5rem 1rem;
}
.stButton > button:hover, .stDownloadButton > button:hover{
  border-color:var(--accent); transform:translateY(-1px); color:var(--txt);
  box-shadow:0 10px 26px -12px rgba(129,140,248,0.85);
}
.stButton > button[kind="primary"],
.stButton > button[data-testid*="primary"],
.stDownloadButton > button[kind="primary"],
.stDownloadButton > button[data-testid*="primary"]{
  background:linear-gradient(135deg,#818cf8 0%, #22d3ee 100%);
  color:#070a14 !important; border:none; font-weight:700;
  box-shadow:0 10px 28px -10px rgba(34,211,238,0.65);
}
.stButton > button[kind="primary"]:hover,
.stDownloadButton > button[kind="primary"]:hover{
  filter:brightness(1.08); transform:translateY(-1px);
}

/* ── Inputs ── */
[data-baseweb="textarea"], [data-baseweb="input"], [data-baseweb="select"] > div{
  border-radius:12px !important; border-color:var(--stroke-soft) !important;
  background:rgba(255,255,255,0.025) !important;
}
[data-baseweb="textarea"]:focus-within, [data-baseweb="input"]:focus-within,
[data-baseweb="select"] > div:focus-within{
  border-color:var(--accent) !important;
  box-shadow:0 0 0 3px rgba(129,140,248,0.16) !important;
}
textarea, input{ color:var(--txt) !important; }
[data-baseweb="tag"]{
  background:linear-gradient(135deg, rgba(129,140,248,0.85), rgba(34,211,238,0.7)) !important;
  border:none !important; border-radius:7px !important; color:#070a14 !important;
}

/* ── Metric cards ── */
[data-testid="stMetric"]{
  background:var(--glass); border:1px solid var(--stroke-soft);
  border-radius:15px; padding:14px 16px;
  transition:border-color .18s ease, transform .18s ease;
}
[data-testid="stMetric"]:hover{ border-color:var(--stroke); transform:translateY(-2px); }
[data-testid="stMetricValue"]{
  font-family:'Space Grotesk',sans-serif !important; font-weight:700;
}
[data-testid="stMetricLabel"]{ color:var(--muted) !important; }

/* ── Progress ── */
.stProgress > div > div > div > div{
  background:linear-gradient(90deg,#22d3ee,#818cf8,#c084fc) !important;
}
.stProgress > div > div > div{ background:rgba(255,255,255,0.06) !important; }

/* ── Expanders ── */
[data-testid="stExpander"]{
  border:1px solid var(--stroke-soft) !important; border-radius:14px !important;
  background:rgba(255,255,255,0.022); overflow:hidden;
}
[data-testid="stExpander"] summary:hover{ color:var(--accent); }

/* ── Alerts / dividers / dataframe ── */
[data-testid="stAlert"]{ border-radius:13px; }
hr{ border-color:var(--stroke-soft) !important; }
[data-testid="stDataFrame"]{ border-radius:13px; overflow:hidden; border:1px solid var(--stroke-soft); }

/* ── Sidebar ── */
[data-testid="stSidebar"]{
  background:linear-gradient(180deg,#090d1a,#0b0f1e);
  border-right:1px solid var(--stroke-soft);
}

/* ── Section heading helper ── */
.section-kicker{
  font-size:0.72rem; font-weight:700; letter-spacing:0.14em; text-transform:uppercase;
  color:var(--accent); margin:4px 0 2px;
}

/* ── Location chips ── */
.loc-wrap{ display:flex; gap:7px; flex-wrap:wrap; margin:6px 0 2px; }
.loc-chip{
  display:inline-flex; align-items:center; gap:5px;
  font-size:0.78rem; font-weight:600; color:#67e8f9;
  background:rgba(34,211,238,0.08); border:1px solid rgba(34,211,238,0.28);
  padding:4px 10px; border-radius:999px;
}
.loc-chip.empty{ color:var(--muted); background:var(--glass); border-color:var(--stroke-soft); }
</style>
"""


def hero_html() -> str:
    """Top-of-page hero banner."""
    return """
<div class="hero">
  <div class="hero-badge">Revenue Intelligence &nbsp;&middot;&nbsp; GTM Strategy</div>
  <div class="hero-title">Job Hunter</div>
  <div class="hero-sub">AI-graded role intelligence for Harshit Gupta. Score a JD across five
  dimensions, align the right CV variant, tailor bullets, and track every application end to end.</div>
  <div class="hero-meta">
    <span class="hero-pill">5-Dimension Scoring</span>
    <span class="hero-pill">Judgment Layer</span>
    <span class="hero-pill">ATS-Tailored CV</span>
    <span class="hero-pill">Pan-India Coverage</span>
  </div>
</div>
"""


def location_chips_html(locations: list[str]) -> str:
    """Render selected target locations as pill chips."""
    locs = [l for l in (locations or []) if l]
    if not locs:
        return '<div class="loc-wrap"><span class="loc-chip empty">No location set</span></div>'
    chips = "".join(
        f'<span class="loc-chip">&#128205; {_html.escape(str(l))}</span>' for l in locs
    )
    return f'<div class="loc-wrap">{chips}</div>'


def kicker(text: str) -> str:
    """Small uppercase section label."""
    return f'<p class="section-kicker">{_html.escape(text)}</p>'
