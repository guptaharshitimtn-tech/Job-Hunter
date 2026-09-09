"""
profile.py — Single source of truth for Harshit Gupta's profile.
All constants used by scorer, aligner, and cover_letter modules live here.
"""

# ── Model ─────────────────────────────────────────────────────────────────────
MODEL = "llama-3.3-70b-versatile"   # free via Groq — console.groq.com
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are a job search assistant built for Harshit Gupta, Revenue Intelligence and GTM Strategy \
professional, 10 years experience, Bengaluru, India.

CORE IDENTITY: Revenue Intelligence and GTM Systems Architect. He builds operating \
infrastructure behind commercial organisations — connecting sales activity, market insight, \
CRM data, pipeline governance, and risk analytics into decision-making systems. \
His WTW and Kroll work = genuine transactions-side intelligence: PE ecosystem research, \
SWF market sizing, dry powder analysis, AUM tracking, deal flow intelligence using CapIQ, \
PitchBook, Bloomberg. This is not generic market research. It is financial intelligence \
infrastructure.

STREAM HIERARCHY (strongest to weakest actual experience):
1. Revenue Intelligence — CORE, 10 years compounding
2. GTM Strategy — STRONG, built and governed at scale
3. Sales Enablement — REAL but supporting, not standalone
4. Commercial Operations / Secondary Research — THINNER

CANONICAL METRICS (use exactly, never modify):
- £50M+ annualised pipeline influenced
- 131+ high-value pursuits managed
- 32% decision velocity improvement
- 67% lead-to-C-suite meeting conversion
- 23% bid cycle time reduction
- 15 days to 48 hours research cycle (AI-compressed)
- 67% triage turnaround reduction
- 35% doc duplication reduction (Kroll)
- £1.05M qualified pipeline contribution FY24-FY25

TARGET SENIORITY: Senior Manager or Associate Director only. Auto-flag below as SKIP.

HARD CONSTRAINTS:
- Never list PL-300 as a passed certification
- Never describe B.Tech as Computer Science (it is Biotechnology)
- Never claim quota-carrying sales experience
- Never claim ML engineering, cloud architecture, or data engineering depth
- Never suggest ABB (5 prior applications)

COVER LETTER VOICE RULES:
- No em-dashes
- No AI tells: no excited to, passionate about, leverage, synergies, dynamic, \
results-driven, proven track record
- No symmetrical phrasing
- No flattery opener
- Lead with the work, not the feeling
- Anchor at least 3 canonical metrics
- Three paragraphs maximum, 250-320 words
- Close directly

JUDGMENT: Be honest. BORDERLINE = genuine caution, not encouragement. Always include \
Strategic Commentary (2-3 sentences, honest effort-to-probability). \
If role is PLG/product-led SaaS, flag his experience is enterprise-only. \
If role is primarily research delivery, flag this is a step back not a progression.\
"""

# ── Canonical Metrics ──────────────────────────────────────────────────────────
CANONICAL_METRICS = {
    "pipeline_influenced":          "£50M+ pipeline influenced",
    "pursuits_managed":             "131+ GTM pursuits governed",
    "decision_velocity":            "32% decision velocity improvement",
    "lead_conversion":              "67% lead-to-C-suite meeting conversion",
    "bid_cycle_reduction":          "23% bid cycle time reduction",
    "triage_turnaround":            "67% triage turnaround reduction",
    "research_compression":         "15 days to 48 hours AI research compression",
    "content_cycle":                "60%+ content production cycle reduction",
    "document_duplication":         "35% document duplication reduction (Kroll)",
    "team_size":                    "Team of 6 analysts led",
}

# ── CV Variants ───────────────────────────────────────────────────────────────
CV_VARIANTS = {
    "01": {
        "name": "RevOps & GTM (ATS Master)",
        "trigger_keywords": [
            "revops", "revenue operations", "gtm", "go-to-market",
            "commercial", "senior commercial",
        ],
        "description": "Broad ATS-optimised master variant for general senior commercial roles.",
    },
    "02": {
        "name": "GTM Strategy SM",
        "trigger_keywords": [
            "gtm strategy", "commercial strategy", "market intelligence",
            "strategy manager", "go-to-market strategy",
        ],
        "description": "Strategy-forward variant emphasising intelligence and planning work.",
    },
    "03": {
        "name": "Sales Enablement Director",
        "trigger_keywords": [
            "sales enablement", "knowledge management", "content operations",
            "enablement lead", "enablement director",
        ],
        "description": "Positions Harshit as a content and enablement system builder.",
    },
    "04": {
        "name": "Commercial Operations Director",
        "trigger_keywords": [
            "commercial operations", "business operations", "revenue excellence",
            "commercial excellence",
        ],
        "description": "Operationally-led variant for governance and process-heavy roles.",
    },
    "05": {
        "name": "Bureau / Director RevOps",
        "trigger_keywords": [
            "director revops", "deal desk", "pipeline intelligence",
            "b2b saas revops", "bureau",
        ],
        "description": "Director-level RevOps and deal desk focused variant.",
    },
    "06": {
        "name": "Wells Fargo / VP Analytics",
        "trigger_keywords": [
            "analytics manager", "pipeline analytics", "data governance",
            "bfsi analytics", "gcc analytics", "vp analytics",
        ],
        "description": "Analytics-heavy variant for BFSI, GCC, and data governance roles.",
    },
}

# ── Scoring Framework ─────────────────────────────────────────────────────────
SCORING_DIMENSIONS = {
    "experience_quantum": {
        "label": "Experience Quantum",
        "weight": 20,
        "rubric": (
            "Does the JD's required years and scope match Harshit's 10-year profile?\n"
            "20 = 8-12 years required, senior scope explicitly stated\n"
            "15 = 6-8 years required or scope implies senior\n"
            "10 = 4-6 years or ambiguous seniority\n"
            "5  = under 4 years or clearly junior framing\n"
            "0  = entry-level or explicitly junior"
        ),
    },
    "industry_alignment": {
        "label": "Industry Alignment",
        "weight": 20,
        "rubric": (
            "Does the industry/vertical match Harshit's background?\n"
            "20 = Insurance, Risk, Financial Services, Professional Services, SaaS, FinTech\n"
            "15 = Consulting, Advisory, GCC, Knowledge Services, BPO\n"
            "10 = Healthcare, Life Sciences, FMCG, Retail — adjacent but not core\n"
            "5  = Manufacturing, Engineering, Deep Tech — low overlap\n"
            "0  = Irrelevant vertical (e.g. pure hardware, government)"
        ),
    },
    "seniority_fit": {
        "label": "Seniority Fit",
        "weight": 20,
        "rubric": (
            "Does the title and accountability level match Senior Manager / Associate Director?\n"
            "20 = Senior Manager, Associate Director, Director explicitly in title or level\n"
            "15 = Manager with large scope, Lead with strategic remit\n"
            "10 = Ambiguous — could be senior or mid\n"
            "5  = Manager title with clearly junior scope\n"
            "0  = Analyst, Executive, Coordinator, Junior"
        ),
    },
    "technical_skills_match": {
        "label": "Technical Skills Match",
        "weight": 20,
        "rubric": (
            "Does the JD require tools/skills Harshit has?\n"
            "20 = Power BI, CRM (Dynamics/Salesforce/HubSpot), Python, AI/GenAI, pipeline analytics\n"
            "15 = 3-4 of the above, or strong Excel/BI overlap\n"
            "10 = 2 of the above, or adjacent tools\n"
            "5  = Minimal overlap, mostly unfamiliar stack\n"
            "0  = No overlap (e.g. pure engineering stack)"
        ),
    },
    "domain_depth": {
        "label": "Domain Depth",
        "weight": 20,
        "rubric": (
            "Does the role require GTM, RevOps, Sales Enablement, or Commercial Intelligence expertise?\n"
            "20 = Core domain — GTM Strategy, RevOps, Sales Enablement, Commercial Intelligence, Deal Desk\n"
            "15 = Adjacent — Commercial Operations, Business Operations, Strategy, Market Intelligence\n"
            "10 = Partial — Sales Operations, Marketing Operations, Proposals\n"
            "5  = Weak — general management, project management\n"
            "0  = No domain overlap"
        ),
    },
}

SIGNAL_THRESHOLDS = {
    "INVEST":     (75, 100),
    "BORDERLINE": (55, 74),
    "SKIP":       (0,  54),
}

KNOCKOUT_RULES = [
    "Role is explicitly entry-level or requires under 4 years experience",
    "Title is Analyst, Executive, Coordinator, or Junior",
    "Role requires a technical degree Harshit does not have (e.g. CS or Engineering mandatory)",
    "Role is outside India with no visa pathway mentioned and no remote option",
    "Company is clearly a staffing agency posting a generic role",
]

# ── Voice Rules (used as injection into cover letter prompts) ─────────────────
VOICE_RULES = """\
COVER LETTER VOICE RULES — ALL ARE NON-NEGOTIABLE:
1. No em-dashes. Use commas, colons, or restructure the sentence.
2. No AI writing tells. Banned words: "excited", "passionate", "leverage", "synergies",
   "dynamic", "results-driven", "proven track record of success".
3. No symmetrical phrasing. Avoid: "not only X but also Y", "both X and Y",
   "on one hand... on the other".
4. No flattery opener. Never start with "I was thrilled to see this role" or similar.
5. Lead with the work, not the feeling. Open with what you built or achieved.
6. Use real metrics. Anchor at least 3 canonical metrics from Harshit's profile.
7. Three paragraphs maximum.
   - Para 1: who you are and what you built
   - Para 2: why this role specifically
   - Para 3: what you bring that is directly relevant
8. Close without cliche. No "I look forward to hearing from you at your earliest convenience."
   End with a direct, confident sentence.
9. Tone: Direct, grounded, analytical. Reads like a senior professional, not a job seeker.
10. Length: 250-320 words maximum. Count carefully.\
"""

# ── Career History (for aligner and cover letter context) ────────────────────
CAREER_SUMMARY = """\
Willis Towers Watson (WTW) | 2022 – March 2026 | Bengaluru | Lead, Client & Industry Insights
- Built AI Market Intelligence Engine (Python, TF-IDF/NLP): compressed research cycles from 15 days to 48 hours
- Built Revenue Intelligence Power BI Dashboard (Advanced DAX): pipeline velocity, decision health, conversion tracking
- Built Global GTM Triage & Governance Framework: structured intake, scoring, routing; 67% turnaround reduction; adopted across GB and APAC
- Built RAG pipeline: CRM opportunity data ingestion, stalled deal detection, discovery question surfacing, risk advisory prompts
- Led 6 analysts across GB and APAC markets; governed 131+ GTM pursuits; influenced £50M+ pipeline

Kroll Advisory | 2021 – 2022 | Mumbai | Senior Knowledge Analyst, Deal Intelligence
- M&A deal intelligence, cross-border transactions, global knowledge management workflows
- 35% reduction in document duplication

Tata Consultancy Services | 2016 – 2021 | Mumbai | Market Analyst, Enterprise Operations
- Fortune 500 market analysis, BI/Excel automation
- 15+ man-hours/week saved through automation\
"""

# ── Standard CV Bullets (used by CV builder when tailored bullets don't cover a role) ──
STANDARD_BULLETS = {
    "WTW": [
        "Engineered AI Market Intelligence Engine (Python, TF-IDF/NLP), compressing research cycles from 15 days to 48 hours across GB and APAC markets",
        "Architected Revenue Intelligence Power BI Dashboard (Advanced DAX) tracking pipeline velocity, decision health, and conversion for £50M+ portfolio",
        "Designed Global GTM Triage & Governance Framework adopted as standard across GB and APAC, reducing turnaround by 67% across 131+ pursuits",
        "Deployed RAG pipeline on live CRM opportunity data for stalled deal detection, discovery question surfacing, and risk advisory prompts",
        "Led team of 6 analysts across two markets; governed pursuit qualification, intake scoring, and routing for all GB and APAC GTM initiatives",
        "Drove 32% improvement in decision velocity through structured intelligence workflows and real-time pipeline reporting",
    ],
    "Kroll": [
        "Led M&A deal intelligence and cross-border transaction research for global advisory mandates across 20+ markets",
        "Redesigned knowledge management workflows across global teams, reducing document duplication by 35% and cutting retrieval time",
        "Produced competitive intelligence and sector analysis in support of deal origination and due diligence workstreams",
    ],
    "TCS": [
        "Delivered Fortune 500 market analysis and competitive intelligence for enterprise clients across BFSI, FMCG, and technology verticals",
        "Built BI and Excel automation frameworks reducing recurring reporting effort by 15+ man-hours per week",
        "Maintained and enriched CRM data pipelines supporting sales operations for enterprise accounts",
    ],
}

# ── Contact details (used in CV header) ──────────────────────────────────────
CONTACT = {
    "name":     "Harshit Gupta",
    "phone":    "+91 7028296853",
    "email":    "guptaharshit.imtn@gmail.com",
    "linkedin": "linkedin.com/in/harshit-gupta-b852a015a",
    "location": "Bengaluru, India",
}

# ── Job Locations (India-wide) ────────────────────────────────────────────────
# Used by the Hunt & Score location picker and pre-fills the tracker.
JOB_LOCATIONS = [
    "Bengaluru",
    "Mumbai",
    "Hyderabad",
    "Delhi NCR",
    "Gurugram",
    "Noida",
    "Pune",
    "Chennai",
    "Kolkata",
    "Ahmedabad",
    "Remote (India)",
    "Hybrid (India)",
    "Pan-India / Multiple",
]

# ── Tracker path ──────────────────────────────────────────────────────────────
TRACKER_PATH = r"D:\Harshit_Job_Tracker_v6 (1).xlsx"

# ── CV Header Subtitles per variant ──────────────────────────────────────────
CV_SUBTITLES = {
    "01": "Senior Manager  |  Revenue Operations & GTM Strategy  |  Pipeline Intelligence & Commercial Excellence",
    "02": "Senior Manager  |  GTM Strategy & Commercial Intelligence  |  Revenue Intelligence Systems",
    "03": "Director  |  Sales Enablement & Knowledge Operations  |  GTM Content & Intelligence",
    "04": "Senior Manager  |  Commercial Operations & Revenue Excellence  |  Pipeline Governance",
    "05": "Director  |  Revenue Operations & Deal Desk  |  Pipeline Intelligence & GTM Architecture",
    "06": "Senior Manager  |  Analytics & Business Intelligence  |  Revenue Analytics & Data Governance",
    "default": "Senior Manager  |  Revenue Operations & GTM Strategy  |  Commercial Intelligence",
}

# ── Metrics bar (value, label) per variant — used in CV header stats row ─────
METRICS_BAR = {
    "01": [
        ("131+", "GTM Pursuits\nGoverned"), ("£50M+", "Pipeline\nInfluenced"),
        ("67%", "Turnaround\nReduction"), ("48 hrs", "AI Research\nCycle"),
        ("6+", "Analysts\nLed"), ("10 yrs", "Industry\nExperience"),
    ],
    "02": [
        ("131+", "Engagements\nDelivered"), ("£50M+", "Pipeline\nInfluenced"),
        ("67%", "C-Suite\nConversion"), ("48 hrs", "AI Intel\nCycle"),
        ("12", "Markets\nAnalysed"), ("10 yrs", "CI\nPractice"),
    ],
    "03": [
        ("131+", "Pursuits\nEnabled"), ("£50M+", "Pipeline\nInfluenced"),
        ("67%", "Turnaround\nReduction"), ("60%+", "Content Cycle\nReduction"),
        ("6+", "Analysts\nLed"), ("10 yrs", "Experience"),
    ],
    "04": [
        ("131+", "Pursuits\nGoverned"), ("£50M+", "Pipeline\nInfluenced"),
        ("67%", "Turnaround\nReduction"), ("32%", "Decision\nVelocity Gain"),
        ("6+", "Analysts\nLed"), ("10 yrs", "Experience"),
    ],
    "05": [
        ("131+", "Deal Pursuits\nManaged"), ("£50M+", "Pipeline\nInfluenced"),
        ("67%", "Deal Desk\nTurnaround"), ("32%", "Velocity\nImprovement"),
        ("6+", "Analysts\nLed"), ("10 yrs", "RevOps\nExperience"),
    ],
    "06": [
        ("131+", "Engagements\nAnalysed"), ("£50M+", "Pipeline\nTracked"),
        ("32%", "Decision\nVelocity Gain"), ("Power BI", "Advanced\nDAX"),
        ("6+", "Analysts\nLed"), ("10 yrs", "Analytics\nExperience"),
    ],
    "default": [
        ("131+", "Engagements\nDelivered"), ("£50M+", "Pipeline\nInfluenced"),
        ("67%", "Turnaround\nReduction"), ("48 hrs", "AI Research\nCycle"),
        ("6+", "Analysts\nLed"), ("10 yrs", "Experience"),
    ],
}

# ── Core Competencies per variant — (category, items) pairs ──────────────────
CORE_COMPETENCIES = {
    "01": [
        ("Revenue Operations", "Pipeline governance, deal desk design, CRM operations, triage frameworks, intake architecture"),
        ("GTM Strategy & Intelligence", "Pursuit qualification, win/loss analysis, commercial intel delivery, market monitoring"),
        ("Technology & AI", "Python TF-IDF/NLP, Power BI Advanced DAX, AI/GenAI tooling, Dynamics 365, Salesforce"),
        ("Leadership & Delivery", "Team of 6 led, offshore delivery management, stakeholder alignment, capacity planning"),
    ],
    "02": [
        ("GTM Strategy", "Commercial intelligence, market sizing, competitive positioning, territory and pursuit planning"),
        ("Revenue Intelligence", "Win/loss analysis, pipeline analytics, deal health scoring, opportunity classification"),
        ("Technology & AI", "Python TF-IDF/NLP, Power BI Advanced DAX, AI/GenAI tooling, Bloomberg, Capital IQ"),
        ("Leadership & Delivery", "Team of 6 led, cross-regional stakeholder management, offshore delivery governance"),
    ],
    "03": [
        ("Sales Enablement", "Battlecard development, talk tracks, content frameworks, sales playbooks, deal guidance"),
        ("Knowledge Operations", "Content lifecycle management, taxonomy design, template governance, knowledge codification"),
        ("Technology & AI", "Python automation, GenAI tooling, Power BI, CRM platforms, content management"),
        ("Leadership & Delivery", "Team of 6 led, cross-functional collaboration, programme governance, capability development"),
    ],
    "04": [
        ("Commercial Operations", "Pipeline governance, SLA management, process design, intake frameworks, reporting"),
        ("Revenue Excellence", "GTM triage, pursuit qualification, decision velocity, cross-functional alignment"),
        ("Technology & Analytics", "Python, Power BI Advanced DAX, AI/GenAI, CRM operations, Excel modelling"),
        ("Leadership & Delivery", "Team of 6 led, offshore delivery management, stakeholder reporting, change management"),
    ],
    "05": [
        ("Revenue Operations", "Deal desk architecture, pipeline governance, CRM operations, intake and routing frameworks"),
        ("Commercial Intelligence", "Pipeline analytics, deal health tracking, revenue forecasting support, win/loss analysis"),
        ("Technology & AI", "Python TF-IDF/NLP, Power BI Advanced DAX, Salesforce, Dynamics 365, AI/GenAI tooling"),
        ("Leadership & Delivery", "Team of 6 led, offshore RevOps delivery, stakeholder management, capacity governance"),
    ],
    "06": [
        ("Analytics & BI", "Power BI Advanced DAX, pipeline analytics, revenue dashboards, decision health tracking"),
        ("Data Operations", "CRM data governance, intake frameworks, data pipeline design, Python automation"),
        ("Commercial Intelligence", "Market analysis, competitive benchmarking, opportunity scoring, sector research"),
        ("Leadership & Delivery", "Team of 6 led, analytics programme delivery, stakeholder reporting, team development"),
    ],
    "default": [
        ("Revenue Intelligence", "Commercial intelligence, pipeline analytics, GTM triage, win/loss analysis, market monitoring"),
        ("Technology & Automation", "Python TF-IDF/NLP, Power BI Advanced DAX, AI/GenAI, Bloomberg, Capital IQ, Factiva"),
        ("Leadership & Delivery", "Team of 6 led, offshore GBS delivery, cross-regional stakeholder management"),
        ("Operations & Governance", "SLA management, intake governance, process design, capacity planning, change management"),
    ],
}

# ── Signature Projects per variant — {title, tags, body} ─────────────────────
SIGNATURE_PROJECTS = {
    "01": [
        {
            "title": "Global GTM Triage & Governance Operating Model",
            "tags":  "Pipeline governance  \u00b7  Intake design  \u00b7  SLA architecture  \u00b7  Cross-regional deployment",
            "body":  "Built and institutionalised the GTM Triage and Governance Operating Model across GB and APAC, achieving 67% turnaround reduction through structured intake, classification, and routing of 131+ commercial pursuits. Adopted as standard operating practice across both regions ahead of scale pressure.",
        },
        {
            "title": "AI-Powered Revenue Intelligence Engine",
            "tags":  "Python  \u00b7  TF-IDF/NLP  \u00b7  Power BI Advanced DAX  \u00b7  CRM data integration",
            "body":  "Designed and deployed an AI-enabled intelligence pipeline integrating Bloomberg, Factiva, S&P Capital IQ, and CRM opportunity data, compressing research cycles from 15 days to 48 hours. Built supporting Power BI dashboards tracking pipeline velocity, decision health, and conversion across a \u00a350M+ portfolio.",
        },
    ],
    "02": [
        {
            "title": "AI-Powered Competitive Intelligence Engine",
            "tags":  "Python  \u00b7  TF-IDF/NLP  \u00b7  Multi-source ingestion  \u00b7  Factiva, Bloomberg, Capital IQ",
            "body":  "Built and deployed a competitive intelligence pipeline ingesting multi-source signals, applying automated scoring and routing, and surfacing structured competitive context for 131+ commercial pursuits. Compressed research cycles from 15 days to 48 hours with human-in-the-loop governance at high-stakes decision points.",
        },
        {
            "title": "12-Market European Insurance Competitive Analysis",
            "tags":  "Market sizing  \u00b7  GWP mapping  \u00b7  Broker landscape  \u00b7  Competitive positioning",
            "body":  "Led gross written premium and competitive broker landscape analysis across 12 European markets, synthesising pricing dynamics, market share data, and competitive positioning into executive-ready strategic direction for senior leadership C-suite commercial engagement.",
        },
    ],
    "03": [
        {
            "title": "Sales Enablement Content & Battlecard Programme",
            "tags":  "Battlecard development  \u00b7  Talk tracks  \u00b7  Win/loss analysis  \u00b7  Sales playbooks",
            "body":  "Built and maintained a library of competitive engagement frameworks, objection response playbooks, and deal guidance decks used across 131+ commercial pursuits. Developed the content operating model connecting intelligence delivery to sales team execution, contributing to 67% lead-to-C-suite conversion rate.",
        },
        {
            "title": "AI Training Community of Practice & Knowledge Codification",
            "tags":  "GenAI tooling  \u00b7  Knowledge management  \u00b7  Taxonomy design  \u00b7  Capability building",
            "body":  "Built and led an internal AI training community of practice, standardising knowledge codification and taxonomy frameworks across the GB and APAC intelligence team. Reduced analyst onboarding time by 40% and embedded continuous improvement culture into daily operations.",
        },
    ],
    "04": [
        {
            "title": "GBS Operating Model Redesign & Digitisation",
            "tags":  "Process design  \u00b7  Offshore transformation  \u00b7  Technology adoption  \u00b7  Change management",
            "body":  "Designed and delivered end-to-end transformation of the WTW Bengaluru GBS hub, rebuilding intake governance, resourcing frameworks, delivery SLAs, and quality protocols. Introduced Python and GenAI automation compressing research cycles by 67%. Rebuilt the model twice as scope expanded from GB to APAC to MENA.",
        },
        {
            "title": "Global GTM Governance Framework",
            "tags":  "Pipeline governance  \u00b7  Intake classification  \u00b7  Commercial operations  \u00b7  SLA design",
            "body":  "Built and institutionalised the Global GTM Triage and Governance Operating Model across GB and APAC, achieving 67% turnaround reduction and 32% improvement in commercial decision velocity. Adopted as standard operating practice across both regions.",
        },
    ],
    "05": [
        {
            "title": "GTM Deal Desk & Pipeline Governance Architecture",
            "tags":  "Deal desk design  \u00b7  Pipeline intelligence  \u00b7  CRM governance  \u00b7  Intake routing",
            "body":  "Designed and operationalised a GTM deal desk framework governing 131+ commercial pursuits, with structured intake, qualification scoring, routing, and SLA compliance tracking. Achieved 67% turnaround reduction and enabled real-time pipeline visibility across GB and APAC markets.",
        },
        {
            "title": "AI-Powered Revenue Intelligence Engine",
            "tags":  "Python  \u00b7  TF-IDF/NLP  \u00b7  Power BI Advanced DAX  \u00b7  CRM data integration",
            "body":  "Designed and deployed an AI-enabled intelligence pipeline integrating Bloomberg, Factiva, S&P Capital IQ, and CRM opportunity data, compressing research cycles from 15 days to 48 hours. Built Revenue Intelligence dashboards tracking pipeline velocity, decision health, and conversion across a \u00a350M+ portfolio.",
        },
    ],
    "06": [
        {
            "title": "Revenue Intelligence Power BI Dashboard Suite",
            "tags":  "Power BI Advanced DAX  \u00b7  Pipeline analytics  \u00b7  Decision health  \u00b7  Conversion tracking",
            "body":  "Architected and deployed a Revenue Intelligence Dashboard tracking pipeline velocity, decision health, lead-to-meeting conversion, and triage performance across 131+ commercial pursuits. Drove 32% improvement in commercial decision velocity through structured intelligence workflows and real-time reporting.",
        },
        {
            "title": "AI-Powered Intelligence Infrastructure",
            "tags":  "Python  \u00b7  TF-IDF/NLP  \u00b7  Multi-source ingestion  \u00b7  Bloomberg, Factiva, Capital IQ",
            "body":  "Built and deployed an AI-enabled research pipeline integrating Bloomberg, Factiva, S&P Capital IQ, PitchBook, and FactSet, compressing analysis cycles from 15 days to 48 hours. Architecture included explicit governance for human-in-the-loop quality control at high-stakes analytical decision points.",
        },
    ],
    "default": [
        {
            "title": "AI-Powered Intelligence Infrastructure",
            "tags":  "Python  \u00b7  TF-IDF/NLP  \u00b7  Multi-source ingestion  \u00b7  Human-in-the-loop governance",
            "body":  "Built and deployed an AI-enabled intelligence pipeline integrating Factiva, Bloomberg, S&P Capital IQ, PitchBook, and FactSet, compressing research cycles from 15 days to 48 hours. Architecture included explicit governance separating autonomous AI execution from human-supervised judgment at high-stakes decision points.",
        },
        {
            "title": "Global GTM Triage & Governance Operating Model",
            "tags":  "Pipeline governance  \u00b7  Intake design  \u00b7  SLA architecture  \u00b7  Cross-regional",
            "body":  "Built and institutionalised the Global GTM Triage and Governance Operating Model across GB and APAC, achieving 67% turnaround reduction through structured intake, classification, and routing adopted as standard operating practice across both regions.",
        },
    ],
}
