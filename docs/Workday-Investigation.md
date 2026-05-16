# Workday CXS API — `HTTP 422` investigation

## Problem

The most recent full scrape (770 new-grad jobs total) returned only **90** jobs
from Workday across 60 configured boards. 38 Workday tenants — including
Microsoft, JPMorgan Chase, Goldman Sachs, Morgan Stanley, Oracle, Salesforce,
ServiceNow, Cisco, AMD, Qualcomm, Capital One, Fidelity, Intuit, Lockheed
Martin, etc. — uniformly returned `HTTP 422` with an empty `message`:

```json
{"errorCode":"HTTP_422","errorCaseId":"…","httpStatus":422,"message":"","messageParams":{}}
```

The existing retry logic in [`scripts/update_jobs.py:1318-1324`](../scripts/update_jobs.py#L1318-L1324)
re-acquires a `CALYPSO_CSRF_TOKEN` from `https://{host}/` and re-POSTs once. The
retry still returns 422 — so the original hypothesis (token expired mid-run) is
wrong.

## Investigation findings (2026-05-16)

Live probes against Microsoft, Oracle, and Goldman Sachs Workday tenants:

### Finding 1 — `CALYPSO_CSRF_TOKEN` is not issued on any tested endpoint

| Endpoint | Method | Status | `CALYPSO_CSRF_TOKEN` cookie? |
|---|---|---|---|
| `https://{host}/` | GET, browser headers | 406 / 500 | none |
| `https://{host}{site_path}` | GET, browser headers | 500 | none |
| `https://{host}/wday/cxs{site_path}/client_check` | POST `{}` | 405 / 400 | **none** |
| `https://{host}/wday/cxs{site_path}/jobs` | GET, browser headers | 400 / 422 | none |
| `https://{host}/wday/cxs{site_path}/jobs` | POST `{...}` (production code path) | 422 / 400 | none |

The current `get_workday_csrf_token` function returns an empty string on these
tenants. Confirmed by adding a debug print before the retry — `csrf_token=''`
in all 38 failing cases.

### Finding 2 — Tenants do issue `PLAY_SESSION`, but it isn't sufficient

POSTing to `/wday/cxs/{tenant}/{site}/client_check` (with empty JSON body) does
prime a `PLAY_SESSION` cookie, plus `wd-browser-id`, `__cf_bm`, `_cfuvid`. A
subsequent jobs POST that re-uses the same `requests.Session` (so PLAY_SESSION
auto-attaches) still returns 422 / 400. The session cookie alone is not what
Workday is gating on.

### Finding 3 — Per-tenant infrastructure varies

The cookie set differs between tenant versions:

| Tenant | Workday cluster | First-party cookie |
|---|---|---|
| Boeing | `wd1.myworkdayjobs.com` | `wday_vps_cookie`, `__cflb` |
| Northrop Grumman | `wd1.myworkdayjobs.com` | `wday_vps_cookie`, `__cflb` |
| Oracle | `wd1.myworkdayjobs.com` | `wday_vps_cookie`, `__cflb` |
| Goldman Sachs | `wd5.myworkdayjobs.com` | `wday_vps_cookie`, `__cflb` |
| Microsoft | `wd10.myworkdayjobs.com` | `vps-cke` (different prefix) |

Microsoft's `wd10` cluster issues `vps-cke` instead of `wday_vps_cookie`,
suggesting a newer Workday CXS infrastructure with different anti-bot behavior.

### Finding 4 — Even "previously working" tenants now return 400

Boeing and Northrop Grumman returned **200 jobs and ~50 jobs** in the original
scrape (`b4lgjn86s.output`), but a fresh CLI probe of the same endpoints now
returns 400 with an empty message. Either:

- Workday rolled out an anti-bot upgrade between the scrape (3.4 min ago at
  probe time) and the manual probe, or
- The scraper's shared `requests.Session` accumulated headers/cookies from
  earlier successful (non-Workday) requests that satisfy a check the bare
  probe doesn't replicate.

The second is more likely; needs deeper instrumentation to confirm.

## Why no fix is being shipped in this PR

The plan-mode investigation expected to find a single endpoint that issues
`CALYPSO_CSRF_TOKEN` and write a 5-line patch to call it. The empirical results
above invalidate that hypothesis. A real fix would require:

1. **Reverse-engineer per-tenant cookie chain** — capture a real browser session
   against each Workday cluster (`wd1`, `wd5`, `wd10`) and replicate the exact
   header sequence including Cloudflare `__cf_bm` flow.
2. **Possibly headless-browser the careers page** — `playwright` already in
   `requirements.txt`; could spin up a one-shot session per tenant on first
   request and reuse the cookies. Expensive (1 chromium per tenant) but reliable.
3. **Or call Workday's "Recruiting REST" public API** if available — needs an
   API key the careers-page consumer doesn't have.

Each option is multi-day work and changes the runtime architecture
(`requests.Session` → `playwright` browser context). Out of scope for the
current PR.

## Recommended next steps

1. File a GitHub issue tracking this investigation; link this doc.
2. Spike a `playwright`-based fallback fetcher behind a feature flag for
   tenants that currently return 422 only. Measure cost (jobs/min, memory).
3. If `playwright` proves too heavy, consider dropping the 38 Workday tenants
   from the scrape entirely and adding a static link list (titled "Major
   employers worth checking manually") to the README so the loss is visible
   instead of silent.

## Tenants currently affected

> AMD, Accenture, American Express, BCG, Bank of America, Bristol Myers Squibb,
> Capital One, Charles Schwab, Cisco, Deloitte, EY, Fidelity, General Dynamics,
> Goldman Sachs, Intuit, JPMorgan, Johnson & Johnson, L3Harris, Lenovo,
> Lockheed Martin, McKinsey, Merck, Microsoft, Morgan Stanley, Netflix, Oracle,
> PepsiCo, Procter & Gamble, PwC, Qualcomm, Raytheon, SAP, Salesforce,
> ServiceNow, Splunk, Starbucks, UnitedHealth Group, VMware
