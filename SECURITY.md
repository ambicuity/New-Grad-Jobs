# Security Policy

## Supported Versions

The following versions of New Grad Jobs are currently receiving security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | ✅ Active support  |
| < 1.0   | ❌ Not supported   |

## Reporting a Vulnerability

**Please do NOT open a public GitHub Issue for security vulnerabilities.**

Opening a public issue exposes the vulnerability to all users — including malicious actors — before a patch is available.

### Private Disclosure Process

1. **Email the maintainer directly at:** `contact@riteshrana.engineer`
2. Use the subject line: `[SECURITY] New Grad Jobs - <brief description>`
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
- **Python scraper** (`scripts/update_jobs.py`): Arbitrary code execution, SSRF, credential leakage
- **Dependency vulnerabilities**: Known CVEs in `requirements.txt` dependencies
- **GitHub Pages frontend** (`docs/`): XSS, content injection, open redirects
- **`config.yml`**: Configurations that could enable malicious scraping behavior

The following are **out of scope**:

- Vulnerabilities in third-party job boards (Greenhouse, Lever, etc.) — report to those vendors
- Rate-limiting or IP banning by scraped sites (expected operational behavior)
- Social engineering attacks

## Security Best Practices for Contributors

When contributing to this project, please observe the following:

- **Never hardcode credentials, tokens, or API keys** — use GitHub Secrets and environment variables
- **Validate all external data** — data from scraped APIs should be treated as untrusted
- **Pin dependency versions** — use exact versions in `requirements.txt` to prevent supply-chain attacks
- **Review GitHub Actions permissions** — workflows should request the minimum permissions required

Thank you for helping keep New Grad Jobs and its users safe.
