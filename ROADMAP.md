# Roadmap — New Grad Jobs

> *Where we are and where we're going.* This roadmap reflects priorities as of **March 2026**. Items shift based on community feedback — [vote with a 👍](https://github.com/ambicuity/New-Grad-Jobs/issues) or open an issue to influence what gets built next.

---

## ✅ Shipped (v1.0.0)

- **Multi-source aggregation** — Greenhouse, Lever, Google Careers, JobSpy (Indeed/LinkedIn)
- **Parallel fetching** — 50+ concurrent workers, 5-minute update cycle via GitHub Actions
- **Interactive job board** — Searchable, filterable frontend on GitHub Pages (no framework, Vanilla JS)
- **Smart categorization** — Auto-classify roles into SWE, Data/ML, SRE, Quant, PM, Hardware
- **Company tier tagging** — FAANG+, Unicorn, Defense, Finance, Healthcare, Startup
- **Sponsorship detection** — Flag jobs with no-sponsorship or US-citizenship requirements
- **Community templates** — Issue templates for new roles, closed jobs, bug reports
- **Structured CHANGELOG** — Keep a Changelog format + Semantic Versioning

---

## 🔄 In Progress

### v1.1 — Data Quality & Coverage
- [ ] **Workday API support** — Cover 50+ enterprise companies that use Workday as their ATS (e.g., Deloitte, EY, Accenture)
- [ ] **iCIMS API support** — Additional coverage for large companies on this ATS
- [ ] **Smarter deduplication** — URL normalization to collapse same job submitted by multiple sources
- [ ] **Closed job detection** — Mark and remove listings automatically when the job URL returns 404

### v1.2 — Developer Experience
- [ ] **Automated pre-commit checks** — On-push formatting and secret detection via pre-commit.ci
- [ ] **Release Please automation** — Fully automated CHANGELOG generation and GitHub releases from Conventional Commits
- [ ] **Comprehensive test suite** — Unit tests for `filter_jobs()`, `categorize_job()`, `get_company_tier()`, and date parsing
- [ ] **ADR documentation** — Architecture Decision Records in `docs/adr/` for major design choices

---

## 📋 Planned

### v1.3 — New Grad Intelligence
- [ ] **Salary range display** — Where available from API responses, surface estimated salary
- [ ] **Job freshness indicator** — Visual "Posted X days ago" in the frontend UI
- [ ] **Apply count / competition signal** — Surface "Easy Apply" vs multi-step application
- [ ] **Canadian & remote-global jobs** — Opt-in filter for positions outside the USA

### v1.4 — Community & Scale
- [ ] **GitHub Discussions** — Dedicated forum for job search advice, interview tips, and success stories
- [ ] **Email digest** (no auth required) — Weekly digest of new openings via a Cloudflare Worker / BrainMail integration
- [ ] **Company request bot** — GitHub Actions bot that auto-adds companies from community issues to `config.yml`
- [ ] **Code coverage badge** — Codecov integration to surface test coverage in the README

### v2.0 — Platform Evolution *(exploration phase)*
- [ ] **Job alerts API** — REST endpoint to query the `jobs.json` dataset programmatically
- [ ] **Browser extension** — Flag jobs on LinkedIn/Indeed as "New Grad Verified" using our dataset
- [ ] **i18n README** — Community-translated READMEs (Chinese, Spanish, Portuguese, Hindi)
- [ ] **Playwright fallback scraper** — For job boards that block API access but allow browser scraping

---

## 💡 Speculative / Under Discussion

> These are ideas on the backlog without committed timelines. Open a [Discussion](https://github.com/ambicuity/New-Grad-Jobs/discussions) to champion any of these.

- Resume keyword matching — highlight jobs that align with a user's skills
- Interview prep resources linked per company
- Alumni networking — connect applicants who got offers at the same company
- Self-hostable version of the job board

---

## 📣 Request a Feature

Open a [Feature Request](https://github.com/ambicuity/New-Grad-Jobs/issues/new?template=feature_request.yml) or an [Architecture Proposal](https://github.com/ambicuity/New-Grad-Jobs/issues/new?template=architecture_proposal.yml) for larger changes.

For quick discussions, use [GitHub Discussions](https://github.com/ambicuity/New-Grad-Jobs/discussions).
