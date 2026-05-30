# SmartKit

> Zero-cost, auto-updating intelligence dashboard. Fork → add URLs → enable Actions → get a live feed.

Full documentation coming in Phase 7. See `SETUP.md` for the 60-second quickstart once it is written.

---

## GitHub Actions — two known gotchas

**1. Scheduled workflows only run from the default branch.**
If your default branch is `main`, the `schedule:` trigger in `update.yml` will
only fire when that file exists on `main`. A schedule defined on a feature branch
will never trigger automatically.

**2. GitHub disables scheduled workflows after ~60 days of repository inactivity.**
If no commits are pushed and no workflows are triggered for roughly 60 days,
GitHub silently pauses the schedule. Re-enable it from the Actions tab
(`Actions → Update SmartKit Dashboard → Enable workflow`), or push any commit
to reset the inactivity timer.
