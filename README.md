# SmartKit

A zero-cost, auto-updating intelligence dashboard. Fork the repo, point it at one or more public feeds, enable GitHub Actions — and get a live, filterable dashboard at your GitHub Pages URL, updated every six hours, with no infrastructure to manage.

## 60-second quickstart

1. **Fork** — click "Use this template" on GitHub.
2. **Edit `config/sources.yml`** — add your feed URLs (RSS, JSON, or HTML).
3. **Optional:** add `OPENROUTER_API_KEY` as a repository secret for LLM extraction.
4. **Enable Pages:** Settings → Pages → Source → **GitHub Actions**.
5. **Run once:** Actions → Update SmartKit Dashboard → Run workflow.
6. **Visit:** the URL shown in Settings → Pages, typically `https://<you>.github.io/<repo>/dashboard/`.

Full step-by-step: see [SETUP.md](SETUP.md).

---

## Architecture

```
config/sources.yml
       │
       ▼
   [fetch]       RSS · JSON · HTML  (one bad source never stops the run)
       │
       ▼
  [extract]      Tier 0 — regex/keywords        no key required, always runs
       │          Tier 1 — OpenRouter free model  set OPENROUTER_API_KEY secret
       │          Tier 2 — BYOK model/endpoint    change model.name in settings.yml
       │
       │          Tiers 1 and 2 fall back to Tier 0 on any failure (bad key,
       │          rate-limit, retired model, malformed output). Never crashes.
       ▼
   [score]       deterministic keyword weights + source trust  (reads rules.yml)
       │          The LLM never decides what to keep or drop — only this step does.
       ▼
  [render]       writes data/latest.json  +  data/latest.js
       │
       ├──────▶  git commit  (only when data changed — no empty commits)
       │
       └──────▶  GitHub Pages  →  dashboard/index.html  (static, no build step)
```

The pipeline runs in GitHub Actions on a cron (every 6 hours by default) and on manual trigger. The dashboard is plain HTML + vanilla JS — no npm, no framework, opens as a local file.

---

## Change these files

Everything a forker touches lives in `config/`. The pipeline, workflow, and dashboard are machinery you never need to open.

### `config/sources.yml` — your feed URLs

```yaml
 sources:
-  - url: https://www.ncua.gov/newsroom/press-releases/rss
-    type: rss
-    name: NCUA Press Releases
+  - url: https://www.fdic.gov/news/press-releases/press-releases-rss.xml
+    type: rss
+    name: FDIC Press Releases
+  - url: https://api.example.gov/notices.json
+    type: json
+    name: My Agency Notices
```

Supported types: `rss`, `json`, `html`. Add as many sources as you need. One unreachable source logs a warning and the rest continue.

### `config/rules.yml` — what matters to you

```yaml
 keywords:
-  credit union: 2.0
-  ncua: 2.0
-  conservatorship: 3.0
+  bank: 2.0
+  fdic: 2.0
+  deposit insurance: 2.0
   enforcement: 2.0
   violation: 2.0

 scoring:
-  threshold: 0.5
+  threshold: 1.0   # raise to surface only high-signal items
```

Higher keyword weight = more likely to appear on the dashboard. The `threshold` drops anything that scores below it. The LLM never makes keep/drop decisions — this file does.

### `config/settings.yml` — title and model

```yaml
 dashboard:
-  title: NCUA Credit Union Monitor
-  subtitle: National Credit Union Administration — enforcement, guidance, and rulemaking
+  title: FDIC Bank Monitor
+  subtitle: Federal Deposit Insurance Corporation

 model:
-  name: meta-llama/llama-3.1-8b-instruct:free
+  name: google/gemini-flash-1.5   # any OpenRouter model string
```

To use a different provider's endpoint, add `base_url` under `model:`:

```yaml
 model:
   name: gpt-4o-mini
+  base_url: https://api.openai.com/v1
```

---

## Zero cost, explained

| Component | Cost |
|-----------|------|
| Compute | GitHub Actions free tier (2,000 min/month for public repos) |
| Hosting | GitHub Pages (free, unlimited for public repos) |
| Model | OpenRouter free-tier model (set `OPENROUTER_API_KEY`); or nothing at all |
| Storage | One committed JSON file — no database, no object storage |

**No key required.** With no `OPENROUTER_API_KEY` set, the pipeline uses Tier 0 deterministic extraction (regex, keyword matching) and still produces a fully populated, scored dashboard. Adding a free OpenRouter key upgrades to LLM-assisted field extraction for the same $0.

---

## Two GitHub Actions gotchas

**Scheduled workflows only run from the default branch.** If your default branch is `main`, the `schedule:` trigger only fires when `update.yml` exists on `main`. A schedule defined on a feature branch never triggers automatically.

**GitHub disables scheduled workflows after ~60 days of repository inactivity.** If no commits are pushed and no workflows are triggered for roughly 60 days, GitHub silently pauses the schedule. Re-enable it from Actions → Update SmartKit Dashboard → Enable workflow, or push any commit to reset the timer.

---

## Credits

This packages well-established patterns into a plug-and-play template: Simon Willison's *Git scraping* (cron + commit-to-repo as a versioned store) and standard OpenRouter/LLM extraction. The contribution here is the assembly and the plug-and-play experience, not the underlying primitives.

---

## When NOT to use this

- **Sub-second latency.** The pipeline runs on a cron — minimum lag is however long until the next scheduled run. Not suitable for anything that needs to react in real time.
- **High event volume.** The pipeline fetches and scores up to a few dozen items per run and writes a single JSON file. It is not designed for thousands of events per hour.
- **Large mutable state.** `data/latest.json` is current state only. There is no history, no trend tracking, no time-series store. Version history via git is a documented future add-on, not in v1.
- **Real-time alerting or chat.** No push notifications, no webhooks, no streaming. The dashboard is a polling read-only view.
- **Private or sensitive sources.** Everything committed to the repo is public. Do not point this at feeds that contain non-public information unless the repo is private.
