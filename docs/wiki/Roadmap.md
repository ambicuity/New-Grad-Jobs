# 🚀 New Grad Jobs: 2026/2027 Roadmap

> [!IMPORTANT]
> The New Grad Jobs project relies entirely on GitHub Actions and GitHub Pages for a $0 hosting cost infrastructure. Our roadmap focuses on extending the scraping capabilities, optimizing GitHub Actions execution, and enhancing the static frontend.

## 🟢 Phase 1: Engine Stabilization (Current)
- [x] Migrate configuration from Python to `config.yml`.
- [x] Build automated CI/CD checks for Copilot environments.
- [x] Define strict Architectural Taboos to prevent bloat.
- [x] Implement `make setup` and a 3-Tier Onboarding workflow.

## 🟡 Phase 2: Geographic & Data Expansion (Q3 2026)
- [ ] 🌍 **European Focus**: Add support for region filtering native to JobSpy to target EU (London, Berlin, Amsterdam) entry-level roles explicitly.
- [ ] 🔌 **ATS Diversity**: Add parsers for Workday and SmartRecruiters endpoints (currently only Greenhouse, Lever, and JobSpy are supported).
- [ ] 💾 **Data Retention**: Instead of overwriting `jobs.json` every cycle, implement an archival script that pushes stale jobs to a `data_archive/` folder for historical ML training on hiring trends.

## 🔴 Phase 3: "Zero-Cost" Personalization (Q1 2027)
- [ ] 👤 **Local Storage Profiles**: Upgrade the Vanilla JS frontend in `docs/` to leverage `localStorage` so users can "Save" jobs or filter out companies they've already rejected, without us needing a database.
- [ ] 🧮 **Algorithmic Scoring**: Apply a local relevance score to the static JSON based on how many "flags" a job hits (e.g., US Citizenship Required + High Experience = -20 points).
- [ ] ⚡ **Email Alerts Sandbox**: Explore integrating a free-tier serverless edge function (e.g., Cloudflare Workers) simply to ping external webhook subscribers when matching JSON hashes appear.
