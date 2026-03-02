# 📜 Decision Log

This is a chronological ledger of major technical pivots and architectural decisions (`ADRs`) that fundamentally shape the New Grad Jobs project.

> [!NOTE]
> If you are proposing a massive refactor, check this ledger first. The pivot you want to make has likely already been evaluated!

### Historical Ledger

* **March 2026: The AI-Ready Layer & Taboos**
  * **Context**: Repetitive pull requests attempting to "modernize" the repo with React and PostgreSQL.
  * **Pivot**: Explicitly defined the "Architectural Taboos" in `.cursorrules` forbidding heavy databases and frontend frameworks to ensure zero-cost hosting. Ported architecture from undocumented knowledge to ADRs.

* **February 2026: Migrated Core Engine to `update_jobs.py` Monolith**
  * **Pivot**: Consolidated multiple scattered Python files into a single, high-performance scraper script to decrease contributor onboarding friction. [See ADR-0001: Zero-Cost Scraper Architecture](https://github.com/ambicuity/New-Grad-Jobs/blob/main/docs/adr/0001-python-scraper-architecture.md).

* **January 2026: Multi-Source Deduplication Strategy**
  * **Pivot**: Realized JobSpy and direct Greenhouse APIs were pulling the exact same jobs, confusing applicants. Implemented an SHA-256 hash algorithm combining `Company + Standardized Title + Location`. [See ADR-0004: Deduplication Strategy](https://github.com/ambicuity/New-Grad-Jobs/blob/main/docs/adr/0004-deduplication-strategy.md).

* **December 2025: Transition to Pure GitHub Actions**
  * **Context**: External VPS hosting became too expensive to maintain a simple cron job.
  * **Pivot**: Moved all computation to GitHub Actions and all state to `jobs.json` stored directly in git.

---
### Process for Adding to the Ledger
If you author an Architecture Decision Record (ADR) in `docs/adr/` that results in a significant code change or refactor, you must summarize the pivot in this document chronologically.
