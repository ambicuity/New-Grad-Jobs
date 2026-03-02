# 🎓 Welcome to the New-Grad-Jobs Wiki

New Grad Jobs is a fully automated, extremely low-cost aggregator for entry-level tech positions. We scrape 70+ company and ATS endpoints every 5 minutes and deploy the results to a static JSON state.

## 📊 Project Status: Live & Automated
The core aggregation engine is fully operational.
- **Scraping Engine**: Active. Running via GitHub Actions cron.
- **Frontend App**: Active. Deployed via GitHub Pages.
- **Data State**: Active. Over ~1,500 active roles tracked.

## 🧭 Navigating the Wiki

This wiki is your central hub for understanding the "Why" and "Where" of the project:

- **[Project Roadmap](Roadmap)**: See our goals for 2026/2027, including new architectural features and geographic expansions.
- **[System Architecture](../architecture.md)**: Explore the in-depth Mermaid.js diagram of our zero-cost static scraping pipeline.
- **[Governance Model](../../GOVERNANCE.md)**: Learn how decisions are made under our BDFL framework.
- **[Architecture Decisions (ADRs)](../adr/0001-python-scraper-architecture.md)**: Read the historical context behind our strict technical constraints (e.g., why we ban the use of PostgreSQL).

## 🤝 Getting Involved

Want to help us find jobs faster?
1. Check the [**Contributing Guide**](../../CONTRIBUTING.md) to learn how to claim a Sprint and use `make setup`.
2. Browse our `good first issue` tags on the Issue Tracker.
