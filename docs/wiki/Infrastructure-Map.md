# 🗺️ Infrastructure Map

Because this project operates as a "Foundation of One" with zero-cost infrastructure, the map is remarkably simple.

If the original maintainer disappears, this document explains exactly what secrets, dependencies, and levers keep the application running.

## 🗄️ Hosting & Compute
All core infrastructure is provided natively by GitHub for free.
- **Compute (Cron)**: GitHub Actions (`.github/workflows/update-jobs.yml`)
- **Database/Storage**: Git Commits pointing to `jobs.json`
- **Frontend Hosting**: GitHub Pages (configured in Repository Settings -> Pages, tracking the `docs/` folder on `main`).

## 🔑 CI/CD Secrets
The repository relies on the automated GitHub token provisioning. There are **NO external API keys** required to run the scraper, as it hits exclusively public endpoints.
- `GITHUB_TOKEN`: Automatically injected by Actions. Required for the `update-jobs` workflow to commit the generated JSON and Markdown back to the `main` branch.
  *(Ensure Action permissions are set to Read & Write in repository settings).*

## 📦 Third-Party Dependencies (SaaS / Ext)
- **`python-jobspy`**: Used to proxy search results from Indeed, LinkedIn, and Glassdoor without requiring OAuth authentication. If JobSpy fundamentally breaks, the project loses 50% of its intake.
- **Release Please (Google)**: Used to automatically update the `CHANGELOG.md` based on Conventional Commits format.

## 🌐 Domains
- **Currently**: Deployed to the standard `github.io` subdomain.
- **DNS (If Applicable)**: None configured natively. If a custom domain is ever added, it will be managed via GitHub Pages settings with an A Record pointing to GitHub's IPs.
