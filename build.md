# BUILD.md — Build Instruction for Claude Code

> **You are building a public open-source boilerplate that strangers will fork.**
> The entire value proposition is: **a non-technical-ish user forks the repo, enters one or more source URLs, optionally pastes one free API key, enables GitHub Actions — and gets a live, auto-updating intelligence dashboard at zero cost for both infrastructure and model.**
> 
> Optimise every single decision for that forker. Readability over cleverness. Working-by-default over feature-rich. If a choice makes the first run harder, it is the wrong choice.

-----

## 0. Prime directives (read before writing any code)

1. **Zero cost, always.** Infra = GitHub Actions + GitHub Pages (free tier). Model = OpenRouter free-tier models by default. Never introduce a dependency that requires payment to run the default configuration.
1. **Three-tier model strategy (this is the core architecture — get it right):**
- **Tier 0 — Deterministic fallback (no secrets):** On a fresh fork with NO API key set, the pipeline must STILL run end-to-end and produce a populated `data/latest.json` and a working dashboard, using keyword/regex extraction only. The user must see something working before they configure anything.
- **Tier 1 — OpenRouter free model (default once key added):** User pastes one free OpenRouter key as a repo secret. Pipeline calls a `:free` model (configurable string) for extraction. This is the intended normal mode.
- **Tier 2 — Bring your own key/model:** Same key field; user may name any model (paid OpenRouter model, or an OpenAI/Anthropic-compatible endpoint). Just a config change.
1. **Graceful degradation is mandatory.** If the configured model is rate-limited, retired, or the key is missing/invalid, the pipeline logs a clear warning and **falls back to the deterministic tier** rather than crashing. Free-tier model availability rotates; assume the configured model may vanish.
1. **The LLM never decides relevance.** The LLM ONLY converts free text into structured fields. The keep/drop and ranking decisions live in deterministic code reading a rules file. Add a comment block stating this rule at the top of the scoring module.
1. **The user edits configuration, never machinery.** Everything a forker touches lives in `config/`. The pipeline code, workflow, and dashboard logic are things they never open. Validate this at the end (Phase 8).
1. **No build step for the dashboard.** Static HTML + vanilla JS reading `data/latest.json`. No npm, no bundler, no framework. It must open correctly as a local file and on GitHub Pages with zero compilation.
1. **Language:** Python 3.11+ for the pipeline. Minimal pinned dependencies.

-----

## 1. Repository structure (build exactly this)

```
/
├── config/
│   ├── sources.yml        # USER EDITS: list of source URLs + type (rss/json/html)
│   ├── rules.yml          # USER EDITS: keyword weights, thresholds, source trust
│   └── settings.yml       # USER EDITS: dashboard title, schedule note, model string
├── prompts/
│   └── extract.md         # the single extraction prompt (advanced users may edit)
├── pipeline/
│   ├── main.py            # orchestrator: fetch → extract → score → render
│   ├── fetch.py           # pull + normalise sources (rss/json/html)
│   ├── extract.py         # text → structured fields (3-tier model logic lives here)
│   ├── score.py           # deterministic relevance scoring (reads rules.yml)
│   ├── render.py          # writes data/latest.json the dashboard consumes
│   └── llm.py             # thin OpenRouter client + fallback handling
├── dashboard/
│   ├── index.html         # static, reads ../data/latest.json
│   └── app.js             # vanilla JS render
├── data/
│   └── latest.json        # current state (committed; ONLY current, never history)
├── examples/
│   └── regulatory-niche/  # a ready-to-use config for one narrow regulator
│       ├── sources.yml
│       ├── rules.yml
│       └── settings.yml
├── .github/workflows/
│   └── update.yml         # cron + commit-if-changed + Pages deploy
├── .env.example
├── requirements.txt
├── LICENSE                # MIT
├── SETUP.md               # 60-second checklist for forkers
└── README.md              # the product face (write this carefully — see Phase 7)
```

-----

## 2. Build phases (do them in order; verify each before moving on)

### Phase 1 — Scaffold + Tier 0 first run (no secrets)

- Create the structure above with stub files.
- Implement `fetch.py`: given `sources.yml`, fetch each URL, detect/parse RSS (use `feedparser`), JSON, or basic HTML (use `requests` + `beautifulsoup4`), and normalise every item to a common dict: `{title, summary, url, published, raw_text, source}`.
- Implement `extract.py` **Tier 0 only for now**: deterministic extraction (pull keywords, dates, basic fields with regex) — no LLM yet.
- Implement `score.py`: read `rules.yml`, score each item, drop below threshold, rank the rest.
- Implement `render.py`: write `data/latest.json` (current items only) with a `generated_at` timestamp and the dashboard title from settings.
- Implement `main.py` to orchestrate.
- Implement the static `dashboard/` to render `latest.json`.
- **VERIFY:** run `python pipeline/main.py` with a sample RSS URL and NO secrets. Open `dashboard/index.html` in a browser. Confirm a populated dashboard. Do not proceed until this works.

### Phase 2 — Tier 1 + Tier 2 model logic + graceful fallback

- Implement `llm.py`: an OpenRouter client reading `OPENROUTER_API_KEY` from env, model string from `settings.yml` (default to a current free model string, e.g. a `:free` model — pick one that exists today and note in a comment it may need updating). Include timeout + retry + clear error handling.
- Upgrade `extract.py`: if a key is present, use `llm.py` to extract structured fields from `raw_text` per `prompts/extract.md`; **validate the returned JSON against a required-field schema**; on missing key, invalid key, rate-limit, model-not-found, or malformed output, **log a warning and fall back to Tier 0 deterministic extraction**. Never crash.
- Tier 2 is just the user changing the model string in `settings.yml` — make sure any OpenRouter-compatible model string works, and document how to point at another provider’s base URL.
- **VERIFY:** run once with a free OpenRouter key set, once with the key unset, once with a deliberately bad model string. All three must complete and produce a dashboard.

### Phase 3 — GitHub Actions workflow

- Write `.github/workflows/update.yml`:
  - Triggers: `schedule` (cron — default every 6 hours) + `workflow_dispatch` (manual button).
  - `concurrency` group to prevent overlapping runs / half-deploys.
  - Steps: checkout → setup Python → `pip install -r requirements.txt` → run `pipeline/main.py` → commit `data/latest.json` ONLY if changed (`git diff --staged --quiet || git commit ...`, no empty commits) → deploy `dashboard/` to GitHub Pages (use the official Pages deploy actions + OIDC permissions).
  - Reference `OPENROUTER_API_KEY` as an **optional** secret — workflow must succeed whether or not it is set.
- Add a README note about two known GitHub gotchas: scheduled workflows only run from the **default branch**, and GitHub disables scheduled workflows after ~60 days of repo inactivity.

### Phase 4 — The shipped example (the demo)

- Build `examples/regulatory-niche/` targeting ONE narrow, real regulator with a public RSS/JSON feed (pick something specific and uncrowded — a single agency digest or a state board, NOT a broad feed). Include matching `sources.yml`, `rules.yml` (relevance keywords for that sector), and `settings.yml` (dashboard title).
- Make the repo’s **default top-level `config/` ship with this example pre-loaded** so a fresh fork immediately tracks something real on first run.

### Phase 5 — Robustness & forkability polish

- `requirements.txt` pinned + minimal (`feedparser`, `requests`, `beautifulsoup4`, `pyyaml`, plus whatever `llm.py` needs).
- `.env.example` with `OPENROUTER_API_KEY=`.
- Logging throughout (clear INFO lines: which tier was used, how many items kept/dropped, fallback reasons).
- MIT `LICENSE`.
- Handle empty/failed sources without crashing the whole run (one bad source ≠ failed pipeline).

### Phase 6 — SETUP.md (the 60-second path)

A numbered checklist, nothing else: 1) Use this template / fork. 2) Edit `config/sources.yml` — add your URL(s). 3) (Optional) add `OPENROUTER_API_KEY` secret for smarter extraction. 4) Enable Actions + Pages. 5) Run the workflow manually once. 6) Visit your Pages URL.

### Phase 7 — README.md (this is the product — spend real effort here)

Include, in this order:

- One-line description + a one-sentence “what you get.”
- 60-second quickstart (mirror SETUP.md).
- A labelled architecture diagram (ASCII is fine): `sources → fetch → extract (LLM optional) → score (deterministic) → render → commit → Pages`, annotated with the three model tiers.
- “Change these files” section: `sources.yml`, `rules.yml`, `settings.yml` — with a tiny example diff for each.
- “Zero cost, explained” section: GitHub Actions + Pages free tier; OpenRouter free model; works with no key at all via deterministic fallback.
- **Credit section (keep this — it earns trust):** “This packages well-established patterns into a plug-and-play template: Simon Willison’s *Git scraping* (cron + commit-to-repo as a versioned store) and standard OpenRouter/LLM extraction. The contribution here is the assembly and the plug-and-play experience, not the underlying primitives.”
- **“When NOT to use this”** section: sub-second latency, high event volume, large mutable state, real-time chat. Naming the limits is a feature.
- Tone: confident, technical, zero hype. No emoji.

### Phase 8 — Validate the promise (do this last, as a forker would)

- Re-read SETUP.md and follow it literally against the built repo. If completing it requires editing anything outside `config/`, FIX that — the machinery must stay closed to the user.
- Confirm: fresh clone + no secrets → `python pipeline/main.py` → populated dashboard. Then with a free key → richer extraction. Both must work.
- Print a final summary of: every file a user edits, every secret (all optional), and the exact first-run command.

-----

## 3. Constraints recap (don’t violate these)

- Default config runs at **$0** with **no account required** (deterministic tier).
- **Never** commit unbounded history to the repo — `data/latest.json` is current-state only. (Trend history over time is a documented future add-on, not in v1.)
- **Never** let the LLM make the keep/drop decision.
- **Never** add a dashboard build step.
- **Never** crash on a missing key, dead model, or bad source — degrade and log.
- Source input is **URL-only for v1**. Resolving a source by *name* is explicitly a v2 feature — leave a clearly-marked `# v2:` stub comment where it would slot in, but do not build it.

## 4. First message to start the session

Paste this to Claude Code after adding this file to the repo:

> “Read BUILD.md in the repo root and build Phase 1 only. Stop after Phase 1 and show me the run output and the dashboard so I can verify before we continue.”
> Then proceed phase by phase, verifying each.
