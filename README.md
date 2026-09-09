# JD Scoring Engine

Streamlit app that scores a job description against a candidate profile on five dimensions
(experience quantum, industry alignment, seniority fit, technical skills, domain depth) and
returns INVEST / BORDERLINE / SKIP with an honest verdict.

Before the score is returned, a judgment layer (judgment.py) runs four checks: role-type
conflict detection, an overconfidence guard against keyword-only matches, a cover letter
honesty check, and a strategic commentary block. Downstream tabs route the right CV variant,
tailor bullets, and generate interview prep.

Model: Llama 3.3 70B via the Groq API (OpenAI-compatible client).

## Run locally
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # add your key
streamlit run app.py

## Deploy
Push to GitHub, connect at share.streamlit.io, paste GROQ_API_KEY and DEMO_MODE into Secrets.
