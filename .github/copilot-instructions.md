# Copilot Instructions for New Grad Jobs Repository

## Repository Overview

This repository automatically scrapes new graduate job opportunities from 70+ tech companies and updates README.md every 5 minutes. It's a **Python-based automation tool** using Greenhouse, Lever, Google Careers, and JobSpy APIs.

**Key Facts**: Python 3.11+, ~1,100 lines total, single-script architecture, YAML configuration, auto-generates README.md table.

## Build and Validation

### Required Setup (Always Run First)
```bash
cd /path/to/New-Grad-Jobs
pip install -r requirements.txt  # Takes 30-60 seconds, installs ~15 dependencies
```

### Main Execution
```bash
cd scripts
python update_jobs.py  # Runtime: 4-6 minutes, requires 300+ second timeout
```

### Validation Commands
```bash
python -m py_compile scripts/update_jobs.py  # Syntax check
git status --porcelain                       # Check for changes
git checkout README.md                       # Revert auto-generated changes if needed
```

### Expected Behavior
- Script scrapes 70+ company APIs making 50+ HTTP requests
- Updates README.md with job listings table and current timestamp  
- May show API timeout warnings (normal) and date parsing errors (harmless)
- JobSpy import warnings are normal if library unavailable but won't break execution

## Project Layout and Key Files

### Directory Structure
```
/
├── .github/workflows/update-jobs.yml  # Automation (runs every 5 min)
├── config.yml                         # Central configuration (261 lines)
├── scripts/update_jobs.py             # Main script (749 lines) 
├── README.md                          # AUTO-GENERATED - never edit manually
├── requirements.txt                   # Dependencies (4 packages)
└── JOB_SCRAPING_APIS.md              # API documentation
```

### Configuration Architecture (`config.yml`)
- **Filtering**: 60-day max age, new grad keywords, tech track signals, USA-only
- **APIs**: 47 Greenhouse + 5 Lever companies, Google search terms, JobSpy settings
- **README**: Table format, headers, title configuration

### Main Script (`scripts/update_jobs.py`)
**Key Functions**:
- `load_config()` - Loads YAML configuration
- `fetch_greenhouse_jobs()` - Fetches from company APIs (with retry logic)
- `filter_jobs()` - Applies filtering criteria  
- `generate_readme()` - Creates markdown table output
- `main()` - Orchestrates entire pipeline

**Data Flow**: Config → Multi-API fetch → Filter → Sort → README generation → File write

### GitHub Actions Workflow
- **Trigger**: Every 5 minutes + manual dispatch + push to main
- **Environment**: Ubuntu + Python 3.11 + pip dependencies
- **Git Logic**: Sophisticated conflict resolution with up to 5 retries
- **Output**: Commits only README.md changes with timestamped messages

## Development Guidelines

### Safe vs. Dangerous File Modifications
**✅ SAFE TO MODIFY:**
- `config.yml` - Changes take effect on next execution
- `scripts/update_jobs.py` - Test locally first with full execution
- `.github/workflows/update-jobs.yml` - Can test via manual workflow trigger
- `requirements.txt` - Dependency management
- `JOB_SCRAPING_APIS.md` - Documentation only

**❌ NEVER EDIT:**
- `README.md` - Auto-generated every 5 minutes, changes will be overwritten

### Making Changes
1. **Test locally first**: Always run `cd scripts && python update_jobs.py` before committing
2. **Use configuration**: Modify `config.yml` instead of hardcoding values in Python
3. **Validate syntax**: Run `python -m py_compile scripts/update_jobs.py`
4. **Check output**: Verify README.md updates with current timestamp
5. **Revert test changes**: `git checkout README.md` to undo auto-generated updates

### Common Debugging Scenarios
- **"No jobs found"**: Check `config.yml` filtering criteria may be too restrictive
- **API failures**: Company job board URLs occasionally change - normal for some endpoints
- **Date parsing errors**: JobSpy data format issues - script continues despite warnings
- **Workflow conflicts**: GitHub Actions retry logic usually resolves automatically

## Key Commands for Agents

```bash
# Essential development workflow
pip install -r requirements.txt
cd scripts && python update_jobs.py  # Allow 300+ seconds timeout
python -m py_compile scripts/update_jobs.py
git checkout README.md  # If testing locally
```

**Critical Notes:**
- **README.md is auto-generated** - never manually edit, changes overwritten every 5 minutes
- **Allow adequate timeout** - script makes 50+ API calls, needs 4-6 minutes minimum  
- **Configuration drives behavior** - modify config.yml not Python hardcoded values
- **Trust these instructions** - repository thoroughly analyzed, search only if info incomplete