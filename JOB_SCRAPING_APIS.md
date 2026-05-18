# Job Scraping APIs Documentation

This document explains the various job scraping APIs and services integrated into the New Grad Jobs aggregator.

## Currently Integrated APIs

### 1. JobSpy Integration ✅
**Status: Fully Implemented**

JobSpy is an open-source Python library that scrapes jobs from popular job sites including LinkedIn, Indeed, and Glassdoor.

**Configuration:**
```yaml
jobspy:
  enabled: true
  sites:
    - "indeed"
    - "linkedin"
    - "glassdoor"
  search_terms:
    - "new grad software engineer"
    - "entry level software engineer"
  location: "United States"
  results_wanted: 50
  hours_old: 72
```

**Features:**
- No API key required (free and open source)
- Supports multiple major job sites
- Built-in filtering by location and posting date
- Handles proxy rotation and anti-bot measures

### 2. Existing ATS APIs (Maintained)

- **Greenhouse Job Board API** — `https://boards-api.greenhouse.io/v1/boards/<slug>/jobs?content=true`. The `?content=true` flag is mandatory; without it Greenhouse omits the description body and compensation extraction silently produces no results. 113 boards configured.
- **Lever Postings API** — `https://api.lever.co/v0/postings/<team>`. Returns description / descriptionPlain. 2 boards configured (most legacy Lever boards have migrated off; see [`docs/removed-companies.md`](docs/removed-companies.md)).
- **Workday CXS Jobs API** — `https://<host>/wday/cxs/<tenant>/<site>/jobs` POST. 57 boards configured; 38 enterprise tenants currently return HTTP 422 due to per-tenant infrastructure variation — see [`docs/Workday-Investigation.md`](docs/Workday-Investigation.md) for the curl-level investigation and the path forward (playwright bootstrap).
- **Google Careers** — Disabled. The endpoint deprecated in late 2024 and now returns 404.

### 3. Ashby Posting API ✅

**Status: Fully Implemented** (`fetch_ashby_jobs` in [`scripts/update_jobs.py`](scripts/update_jobs.py)).

Modern ATS used by many AI labs and devtools companies that aren't on
Greenhouse / Lever / Workday. 43 boards configured, unlocking OpenAI,
Notion, Cursor, Mistral AI, Cohere, Perplexity, Linear, Modal, Snowflake,
Plaid, ElevenLabs, Decagon, and ~30 more.

**Endpoint:** `https://api.ashbyhq.com/posting-api/job-board/<slug>?includeCompensation=true`

**Configuration (already in [`config.yml`](config.yml)):**
```yaml
ashby:
  companies:
    - name: "OpenAI"
      url: "https://api.ashbyhq.com/posting-api/job-board/openai"
    - name: "Notion"
      url: "https://api.ashbyhq.com/posting-api/job-board/notion"
    # …
```

**Features:**
- No API key required (public posting API).
- Returns **structured compensation** (`compensationTiers`) when companies opt in — preferred over regex extraction.
- Description HTML available in `descriptionHtml` (cleaned to plaintext via `clean_description()` before serialization).
- HTTP_SESSION must **not** advertise `br` (Brotli) in `Accept-Encoding`; Python's `requests` library does not decode Brotli natively, and Ashby's Cloudflare layer preferred br over gzip — silently producing un-parseable bodies. Fix already landed.

## Ready for Configuration APIs

### 3. SerpApi - Google Jobs API 🚧
**Status: Configuration Ready**

SerpApi provides access to Google Jobs search results in a structured format.

**Setup:**
1. Sign up at [serpapi.com](https://serpapi.com)
2. Get your API key
3. Set environment variable: `export SERP_API_KEY="your_api_key"`
4. Enable in config.yml:
   ```yaml
   scraper_apis:
     serp_api:
       enabled: true
       api_key: "${SERP_API_KEY}"
   ```

### 4. ScraperAPI - General Web Scraping 🚧
**Status: Configuration Ready**

ScraperAPI handles proxy rotation, CAPTCHA solving, and JavaScript rendering for scraping any job site.

**Setup:**
1. Sign up at [scraperapi.com](https://scraperapi.com)
2. Get your API key
3. Set environment variable: `export SCRAPER_API_KEY="your_api_key"`
4. Enable in config.yml:
   ```yaml
   scraper_apis:
     scraper_api:
       enabled: true
       api_key: "${SCRAPER_API_KEY}"
   ```

## Additional APIs (Configuration Available)

The following enterprise-grade APIs are configured in the system but require API keys and subscriptions:

- **Zyte (Scrapinghub)**: Enterprise job scraping service
- **Bright Data**: Large-scale proxy network with job scraper API
- **ScrapingBee**: AI-powered web scraping with CAPTCHA solving

## Benefits of Multiple API Approach

1. **Comprehensive Coverage**: Different APIs cover different job sites and companies
2. **Redundancy**: If one API fails, others continue working
3. **Rate Limit Management**: Distribute requests across multiple services
4. **Cost Optimization**: Use free APIs where possible, paid APIs for specialized needs

## Adding New APIs

To add a new job scraping API:

1. Update `config.yml` with the new API configuration
2. Add a new function `fetch_[api_name]_jobs()` in `update_jobs.py`
3. Add the function call to the main aggregation loop
4. Update this documentation

## Usage Notes

- JobSpy is enabled by default as it's free and effective
- Paid APIs require environment variables for API keys
- All APIs respect the same filtering criteria (new grad signals, location, recency)
- Results are merged and deduplicated before final output
