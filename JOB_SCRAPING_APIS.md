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

### 2. Existing APIs (Maintained)
- **Greenhouse API**: Company-specific job boards
- **Lever API**: Company-specific job boards  
- **Google Careers API**: Direct Google job searches

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