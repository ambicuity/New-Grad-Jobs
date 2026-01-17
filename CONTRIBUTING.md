# Contributing to New Grad Jobs

Thank you for your interest in contributing to the New Grad Jobs list! This repository is **fully automated** but we welcome community contributions to help catch jobs our scrapers might miss.

## 🔍 Finding a Job to Add

Please ensure the job posting meets these requirements:

### ✅ Must Have
- Be for **new graduates** or **entry-level** candidates (0-2 years experience)
- Be in a **tech-related field**:
  - Software/Computer Engineering
  - Data Science/Engineering
  - Machine Learning/AI
  - Site Reliability/DevOps
  - Infrastructure/Network Engineering
  - Product Management
  - Quantitative Finance
- Be located in the **United States** or be **fully remote (US)**
- Have a **working application link**
- Not already exist in our list

### ❌ We Don't Accept
- Internship positions (see our internship repo instead)
- Positions requiring 3+ years of experience
- Non-tech roles (marketing, sales, etc. unless tech-adjacent)
- Positions outside the USA

## 📝 How to Contribute

### Adding a New Job

1. Go to [Issues → New Issue](https://github.com/ambicuity/New-Grad-Jobs/issues/new/choose)
2. Select **"New Role"** template
3. Fill in the required information:
   - Company name
   - Job title
   - Location
   - Application URL
   - Category (Software Engineering, Data Science, etc.)
4. Submit the issue

Our team will review and add it to the next update!

### Reporting a Closed Job

1. Go to [Issues → New Issue](https://github.com/ambicuity/New-Grad-Jobs/issues/new/choose)
2. Select **"Edit Role"** template
3. Paste the application URL of the closed job
4. Mark it as closed
5. Submit the issue

### Reporting Issues

Found a bug or have a suggestion? 

1. Go to [Issues → New Issue](https://github.com/ambicuity/New-Grad-Jobs/issues/new/choose)
2. Select **"Bug Report"** or **"Feature Request"** template
3. Describe the issue in detail
4. Submit the issue

## 🤖 How Our Automation Works

Unlike manually-maintained job lists, this repository:

1. **Scrapes 70+ company job boards** every 5 minutes using:
   - Greenhouse API
   - Lever API  
   - Google Careers API
   - JobSpy (LinkedIn, Indeed, Glassdoor)

2. **Filters automatically** for:
   - New grad keywords in titles
   - USA-based locations
   - Recent postings (last 60 days)
   - Tech-related roles

3. **Updates README.md and jobs.json** automatically via GitHub Actions

Community contributions help us catch:
- Companies not using standard job boards
- Jobs with unusual titles our filters miss
- Positions that close before our next scrape

## 📋 Guidelines

### Do
- ✅ Submit one issue per job posting
- ✅ Double-check the application link works
- ✅ Include all required information
- ✅ Search existing issues before submitting

### Don't
- ❌ Submit duplicate postings
- ❌ Submit expired/closed positions as new
- ❌ Submit non-USA positions
- ❌ Submit senior/experienced roles

## 🙏 Thank You!

Every contribution helps new graduates find their dream job. Thank you for being part of this community!

---

Questions? Open a [discussion](https://github.com/ambicuity/New-Grad-Jobs/discussions) or reach out to the maintainers.
