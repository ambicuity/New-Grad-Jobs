# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-17

### 🎉 Initial Release

The first official release of New-Grad-Jobs - an automated job aggregator for entry-level tech positions.

### Features

#### 🌐 Interactive Job Board Website
- Modern, premium dark theme with glassmorphism effects
- Real-time search with debounced input
- Multi-filter system:
  - **Categories**: Software, ML/AI, Data, SRE, PM, Quant
  - **Company Sectors**: FAANG+, Unicorn, Defense, Finance, Healthcare, Startup
  - **Locations**: All 50 US states + Remote
- Responsive design for all devices
- Live job count and last updated timestamp

#### 🤖 Automated Job Scraping
- Updates every 5 minutes via GitHub Actions
- Multiple data sources:
  - Greenhouse API
  - Lever API
  - Google Careers
  - JobSpy (LinkedIn, Indeed)
- Smart filtering for new grad positions
- USA location validation

#### 📊 Job Enrichment
- Automatic categorization by role type
- Company tier classification (FAANG+, Unicorn, etc.)
- Sector tagging (Defense, Finance, Healthcare, Startup)
- Sponsorship flag detection

#### 📝 Community Features
- GitHub Issue templates for submitting new roles
- Issue templates for reporting bugs
- Contributing guidelines

### Technical Details
- GitHub Pages deployment from `/docs`
- JSON-based job data for fast frontend loading
- Python-based scraping with retry logic
- Vanilla JavaScript frontend (no heavy frameworks)

### Contributors
Made by **Ritesh Rana**  
Contact: contact@riteshrana.engineer

---

[1.0.0]: https://github.com/ambicuity/New-Grad-Jobs/releases/tag/v1.0.0
