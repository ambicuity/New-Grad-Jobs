# Copilot Instructions

The canonical instructions for AI agents and reviewers are in [`AGENTS.md`](../AGENTS.md).
It covers the repo map, commands, architecture, conventions and hard rules. Read it first.

When reviewing or writing code here, the rules that matter most:

1. **Never commit generated data.** `site/public/{jobs.json, jobs-index.json, descriptions/, feed.xml, health.json}` are built in CI and deployed to Pages, not committed.
2. **README.md:** only edit outside the `<!-- COUNT:* -->` markers and the `CATEGORY-LISTINGS` block, which the scraper owns. Never alter the Zapply/Tailr sponsor blocks or move the root-level `apply-faster-banner.png` / `get-started-button.png`.
3. **Honesty:** no invented, estimated or placeholder numbers on the site or README. Every figure must come from published data.
4. **Tests first, deterministic:** pytest runs with network blocked, and site logic lives in `site/src/lib/` with vitest. Keep coverage floors (Python 75%, site lib 80%).
5. **Keep the contracts in sync:** `CATEGORY_PATTERNS` (`scripts/ngj/taxonomy.py`) ↔ `site/src/lib/taxonomy.js` ↔ README COUNT rows. Validate `config.yml` with `scripts/validate_config.py`. Run `make lock` whenever Python dependencies change.
