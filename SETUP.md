# SETUP.md — 60-second quickstart

1. **Fork this repository** — click "Use this template" on GitHub to create your own copy.

2. **Edit `config/sources.yml`** — replace the example URLs with your own feed URLs.
   The default config tracks NCUA credit union regulatory filings.
   Supported types: `rss`, `json`, `html`.

3. **(Optional) Add an OpenRouter API key** for LLM-assisted extraction:
   - Settings → Secrets and variables → Actions → New repository secret
   - Name: `OPENROUTER_API_KEY` — Value: your key from openrouter.ai (free tier available)
   - Without this key the pipeline runs in deterministic mode and still produces a full dashboard.

4. **Enable Actions and Pages:**
   - Actions: Settings → Actions → General → Allow all actions (usually on by default)
   - Pages: Settings → Pages → Build and deployment → Source → **GitHub Actions**

5. **Run the workflow manually once:**
   Actions → Update SmartKit Dashboard → Run workflow

6. **Visit your dashboard:**
   Settings → Pages shows the URL — typically `https://<you>.github.io/<repo>/dashboard/`

---

**Local preview** (no server needed): run `python pipeline/main.py` once to generate
`data/latest.js`, then open `dashboard/index.html` directly in your browser.
