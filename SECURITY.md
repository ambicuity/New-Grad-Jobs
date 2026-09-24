# Security Policy

## Supported Versions

The following versions of New Grad Jobs are currently receiving security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | ✅ Active support  |
| < 1.0   | ❌ Not supported   |

Fixes land on `main` and are deployed to <https://jobs.riteshrana.engineer> by the next scraper run. There are no separately maintained release branches.

## Reporting a Vulnerability

**Please do NOT open a public GitHub Issue for security vulnerabilities.**

Opening a public issue exposes the vulnerability to all users — including malicious actors — before a patch is available.

### Private Disclosure Process

1. **Preferred:** use GitHub private vulnerability reporting. Open [**Security → Report a vulnerability**](https://github.com/ambicuity/New-Grad-Jobs/security/advisories/new). The report stays private between you and the maintainer until an advisory is published.
2. **Alternative:** email `contact@riteshrana.engineer` with the subject line `[SECURITY] New Grad Jobs - <brief description>`.
3. Include the following in your report:
   - A description of the vulnerability and its potential impact
   - Steps to reproduce the issue
   - Any proof-of-concept code or screenshots
   - The version(s) affected
   - Your suggested fix (if you have one)

### What to Expect

| Timeline         | Action                                           |
| ---------------- | ------------------------------------------------ |
| Within 48 hours  | Acknowledgement of your report                   |
| Within 7 days    | Initial assessment and severity classification   |
| Within 30 days   | Patch released and CVE filed (if applicable)     |
| Post-patch       | Public disclosure with credit to the reporter    |

We will keep you informed throughout the process and, with your permission, will credit you in the security advisory upon public disclosure.

## Scope

The following are **in scope** for security reports:

- **GitHub Actions workflows**: Secrets exposure, workflow injection, supply-chain attacks
- **Python scraper** (`scripts/update_jobs.py`, `scripts/ngj/`): arbitrary code execution, SSRF, credential leakage, unsafe URLs reaching the published data (see `scripts/url_safety.py`)
- **Dependency vulnerabilities**: known CVEs in `requirements*.txt` or `site/package-lock.json` dependencies
- **Website** (`site/`, deployed to GitHub Pages): XSS, content injection, open redirects, CSP bypasses
- **Published data** (`jobs.json`, `feed.xml`, per-job pages): injection into consumers of the public feed
- **`config.yml`**: Configurations that could enable malicious scraping behavior

The following are **out of scope**:

- Vulnerabilities in third-party job boards (Greenhouse, Lever, etc.) — report to those vendors
- Rate-limiting or IP banning by scraped sites (expected operational behavior)
- Social engineering attacks

## Security Best Practices for Contributors

When contributing to this project, please observe the following:

- **Never hardcode credentials, tokens, or API keys** — use GitHub Secrets and environment variables
- **Validate all external data** — data from scraped APIs should be treated as untrusted
- **Keep dependencies hash-locked.** Python dependencies are declared as ranges in `pyproject.toml` and locked with exact versions **and hashes** in `requirements.txt` / `requirements-dev.txt`. CI installs them with `pip install --require-hashes`. Never hand-edit the lock files: change `pyproject.toml` and run `make lock`. Site dependencies are locked by `site/package-lock.json` and installed with `npm ci`.
- **Pin GitHub Actions to commit SHAs**, as the existing workflows do, and pin pre-commit hooks with `pre-commit autoupdate --freeze`
- **Review GitHub Actions permissions** — workflows should request the minimum permissions required

Thank you for helping keep New Grad Jobs and its users safe.
