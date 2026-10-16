---
title: How NGJ reads salary ranges
description: Where the salary on a listing comes from, how currency is decided, which figures are left out, and what a posted range does and does not tell you.
updated: 2026-10-15
published: 2026-10-15
section: NGJ data
order: 6
format: explainer
use_when: Read this when a listing shows a salary range, or none, and you want to know where it came from and how far to trust it.
you_get: You get the sources NGJ reads pay from, how currency and pay period are handled, what is filtered out, and how to check a range.
---

Many postings on the board show no salary at all. The ones that do show a range NGJ read from the employer's own posting. NGJ never estimates pay. This guide explains exactly how a range gets onto a listing, so you know what it means and when to look at the original posting instead.

## Where the number comes from

There are two routes, and the first one wins when both are available.

- **Structured pay from the job system.** Some job systems publish pay as separate fields alongside the posting: Ashby (yearly ranges, when the employer chooses to include compensation), Rippling (yearly ranges only) and Indeed results collected through JobSpy. NGJ uses those fields as published.
- **A range written in the description.** Otherwise NGJ looks for a salary range in the posting text itself, such as "$85,000 – $105,000", "$85K to $105K" or "USD 85,000 to 105,000". The first range that passes the checks below is used.

Either way, the figure is the employer's, not NGJ's. The code is public: [compensation.py](https://github.com/ambicuity/New-Grad-Jobs/blob/main/scripts/ngj/compensation.py) holds every pattern and limit described here.

## How currency is decided

A currency is never guessed when it matters.

- A symbol or code that names the currency is used as written: US$, USD, C$, CAD, £, €, ₹ and INR. Indian ranges written in lakhs, such as "12 – 18 LPA", are read as rupees.
- A bare "$" is read through the job's location: US dollars for a US, remote or unknown location, Canadian dollars for a Canadian one.
- For a bare "$" in any other country, or in a location that mixes the US and Canada, the currency is left unknown rather than labelled US dollars, because the same sign is used by several currencies.

The job's own page on NGJ shows the currency code next to the range, and leaves the salary out when the currency is unknown. The board's list and detail pane currently show every range with a "$" sign, so for a job outside the US open its page or the employer's posting to confirm the currency before comparing it with anything.

## Pay period: yearly figures only

Every range on NGJ is an annual amount.

- When Indeed (through JobSpy) says its figure is hourly, daily, weekly or monthly, NGJ converts it to a year using fixed multipliers: 2,080 hours, 260 days, 52 weeks or 12 months. That is a full-time year with no overtime, which is an assumption, not a promise. Ashby and Rippling ranges are used only when they are yearly.
- Hourly or monthly figures written only in the description text are not converted, so those postings usually show no range.
- A single yearly figure in the text, such as "$90,000 per year", is shown as a range from 10% below to 10% above it, so that it can sit alongside true ranges. Open the posting to see the exact figure.

## What is filtered out

Job descriptions are full of numbers that are not pay. Before searching, NGJ removes phrases about funding rounds, valuations, revenue, market capitalisation and stock tickers. A range is then kept only if it looks like an annual salary:

| Currency | Lowest accepted | Highest accepted |
| --- | --- | --- |
| US and Canadian dollars | 30,000 | 600,000 |
| Pounds and euros | 18,000 | 450,000 |
| Indian rupees | 300,000 | 15,000,000 |

A range read from the text must also be no wider than 250,000 in dollars, 200,000 in pounds or euros, or 10,000,000 in rupees. Anything outside these limits, such as a signing bonus quoted on its own, a stock price or a typo, is dropped rather than shown. That means a genuine salary outside the limits is dropped too.

## Why many listings show no range

- The employer did not publish one. Many postings simply do not include pay.
- The range is in a format the patterns do not recognise, or only in an attached document or the employer's separate pay-transparency page.
- It was hourly or monthly in the text, or outside the limits above.

Some places require pay ranges in postings. New York requires businesses with four or more employees to list compensation ranges for designated job opportunities, promotions and transfers, and Washington requires a wage scale or salary range in postings from employers with 15 or more employees.

::: evidence official
The [New York State Department of Labor](https://dol.ny.gov/pay-transparency) says businesses with four or more employees must list compensation ranges for designated jobs, and the [Washington Department of Labor & Industries](https://lni.wa.gov/workers-rights/wages/equal-pay-opportunities-act/) says employers with 15 or more employees must include a wage scale or salary range in job postings. Rules elsewhere differ; check the official page for the place you are applying.
:::

## What a range does and does not tell you

A posted range is the employer's statement for that posting. It may cover several levels or locations, it rarely includes bonus, equity or benefits, and it is not an offer. Use it as one input:

1. Open the original posting and read the range in context: location, level and anything said about bonus or equity.
2. Compare it with official wage data for the occupation and area, as [How to research your market salary](../compensation-research/) explains.
3. When an offer arrives, read [Understanding new grad compensation](../understanding-compensation/) and [Evaluating an offer](../evaluating-an-offer/) before deciding.

If a listing shows a range that is wrong for its posting, report it in the [repository](https://github.com/ambicuity/New-Grad-Jobs/issues) with the job link. For how postings reach the board in the first place, see [How job data is collected](../how-job-data-is-collected/) and [How NGJ classifies jobs](../how-ngj-classifies-jobs/).
