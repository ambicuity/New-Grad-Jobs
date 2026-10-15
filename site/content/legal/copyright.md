---
title: Copyright, Attribution and Third-Party Content Policy
description: Who owns what on NGJ (New Grad Jobs), how job listings are attributed to employers, what the MIT License does and does not cover, and how to ask for a correction, removal or permission.
effective: 2026-10-15
updated: 2026-10-15
---

NGJ (New Grad Jobs) is built from two very different kinds of material: open-source code and writing by its maintainer, and job postings published by employers. This policy keeps them apart. The short version:

- **The maintainer's code, guides and documentation** are under the MIT License.
- **Job postings belong to the employers** and source platforms that published them. NGJ does not own them, and the MIT License does not cover them.
- **Attribution is not permission.** NGJ credits and links every listing to its source, but crediting a source does not give anyone, NGJ included, a licence to its content.
- **To report a problem**, email contact@riteshrana.engineer (section 8).

## 1. What NGJ's maintainer owns

Ritesh Rana holds the copyright in the original work published in the [NGJ repository](https://github.com/ambicuity/New-Grad-Jobs): the scraper and website code, the site's design, the guides, the about page and these policies. Contributors keep the copyright in their own contributions, which they submit under the same licence.

That work is licensed under the [MIT License](https://github.com/ambicuity/New-Grad-Jobs/blob/main/LICENSE) (copyright 2026 Ritesh Rana). You may use, copy, modify and distribute it, including commercially, as long as you keep the copyright notice and the licence text. The MIT License grants no trademark rights. Please do not use the names "NGJ" or "New Grad Jobs" to suggest that your project is NGJ or is endorsed by it.

## 2. Job listings belong to their publishers

Every listing on NGJ comes from a posting that an employer published, either in its own careers system (for example Greenhouse, Lever, Ashby, Workday, iCIMS or SuccessFactors) or on Indeed. The [data sources page](../data-sources/) lists them all. For each listing, NGJ shows:

- the job title, employer name and location, as published;
- the posting date and any salary range, only when the source states them;
- the posting's description, converted to plain text: in full (up to 50,000 characters) on the job page and in the board's detail pane, and as an excerpt of at most 3,000 characters in `jobs.json`;
- a link to the original posting, so you apply on the employer's site.

NGJ shows these postings to help people find openings that employers chose to advertise publicly. NGJ has **not** obtained permission from every employer or source platform, and it does not claim that listings are "used with permission". The copyright in a posting's text stays with whoever owns it. If you own a posting and do not want it on NGJ, or want it shown differently, see section 8.

## 3. Employer names, trademarks and logos

Employer names appear on NGJ only to identify who is hiring and to link to the employer's own posting. NGJ does not display employer logos. All trademarks belong to their owners. Their appearance on NGJ does not mean the owner sponsors, endorses or is affiliated with NGJ, and NGJ does not say otherwise.

Some labels on NGJ are NGJ's own editorial classifications, applied by rule, not statements by the employer. These include company tiers such as "FAANG+", the job categories, and the flags "no sponsorship" and "citizenship required".

## 4. How listings are attributed

NGJ attributes every listing in these ways:

- the **employer's name** is shown with every listing;
- the **APPLY** link goes to the original posting on the employer's or job system's site;
- each job page names the **source system** (for example "Greenhouse" or "Workday");
- each job page shows the **date NGJ last confirmed the role was open at the employer**, and the posting date when the source gives one;
- the [about page](../about/) reports each source's status for the latest run.

When NGJ finds the same role in more than one source, it keeps one listing and prefers the employer's own careers system over an Indeed copy.

## 5. What NGJ changes, and what it adds

NGJ processes postings automatically. It:

- **normalises** them: it converts descriptions from HTML to plain text, standardises locations and dates, and reads salary only from the posting. Links are kept as the source published them; NGJ adds no tracking or affiliate parameters;
- **deduplicates** them;
- **classifies** them: category, new grad signals, company tier, and the sponsorship and citizenship flags;
- **limits length**: descriptions longer than 50,000 characters are cut, and `jobs.json` carries a 3,000-character excerpt.

The classifications, field names, schema and the way the data is organised are NGJ's own contribution. NGJ does not rewrite or summarise posting text with AI, and it does not change what a posting says about the job.

## 6. Reusing NGJ's data

NGJ publishes its data as files ([jobs.json](../jobs.json), RSS feeds and others, listed on the [data sources page](../data-sources/)). If you reuse them:

- NGJ's own additions (section 5) may be used under the MIT License, to the extent NGJ has rights in them;
- third-party posting text, employer names and marks are not NGJ's to license. You are responsible for any permission your use needs, especially for bulk or commercial republication;
- credit the employer, link to the original posting, and mention that the data came from NGJ;
- do not suggest that NGJ, an employer or a source platform endorses your use.

## 7. Open-source software and fonts

The website bundles these third-party packages. Each keeps its own licence, and the full licence texts ship with the site in [third-party-licenses.txt](../third-party-licenses.txt):

| Package | Licence | Used for |
| --- | --- | --- |
| React, React DOM and Scheduler (Facebook, Inc. and its affiliates, now Meta) | MIT | the interactive board |
| TanStack Virtual (`@tanstack/react-virtual`, `@tanstack/virtual-core`) | MIT | scrolling long job lists |
| JetBrains Mono, via `@fontsource/jetbrains-mono` (The JetBrains Mono Project Authors) | SIL Open Font License 1.1 | the board's typeface |

The page counter script is loaded from GoatCounter's own servers, under GoatCounter's ISC licence, and is not redistributed by NGJ. The scraper's Python dependencies run only in NGJ's build pipeline and are not shipped with the website. They are listed with their licences in the repository's [THIRD_PARTY_NOTICES.md](https://github.com/ambicuity/New-Grad-Jobs/blob/main/THIRD_PARTY_NOTICES.md).

## 8. Corrections, removals and copyright notices

Email **contact@riteshrana.engineer**. Use one of these subject lines so the message is handled quickly:

- **"Listing correction"** for a wrong, expired or misleading listing, or a wrong employer name or attribution. A public [GitHub issue](https://github.com/ambicuity/New-Grad-Jobs/issues) also works.
- **"Listing removal"** if you are the employer and want your postings left out of NGJ.
- **"Copyright notice"** or **"Trademark concern"** for an intellectual property complaint.
- **"Privacy request"** if a listing exposes personal information (see the [privacy policy](../privacy/)).

**A copyright notice should include**:

1. your physical or electronic signature, as the owner or a person authorised to act for the owner;
2. the copyrighted work you believe is infringed;
3. the material on NGJ you want removed, with its URL;
4. your name, postal address, telephone number and email address;
5. a statement that you believe in good faith that the use is not authorised by the owner, its agent or the law;
6. a statement that the information in the notice is accurate and, under penalty of perjury, that you are the owner or are authorised to act for the owner.

These are the elements that the US Digital Millennium Copyright Act lists for a notice (17 U.S.C. § 512(c)(3)). This process is offered whether or not any statutory safe harbour applies to NGJ. Under 17 U.S.C. § 512(f), knowingly misrepresenting that material is infringing can make you liable for damages.

**What happens next.** The maintainer acknowledges the message, reviews it, and may hide the material while the review is under way. Confirmed problems are corrected or removed. Because NGJ republishes from its sources on every run, a removal is made in NGJ's configuration or rules, so the next run does not bring the listing back. Listings that already appeared in the repository's README remain in its public git history, which records past versions of that file.

If material you published was removed and you believe that was a mistake, reply to the maintainer and explain why. The decision will be reviewed.

## 9. Permissions and licensing questions

For permission to use NGJ's branding, or for any licensing question, email contact@riteshrana.engineer with the subject "Licensing question". For permission to reuse a job posting, contact the employer that published it. NGJ cannot grant rights it does not have.

## 10. Changes and contact

This policy may be updated, and the "Last updated" date will change when it is. Earlier versions are kept in the [file history on GitHub](https://github.com/ambicuity/New-Grad-Jobs/commits/main/site/content/legal/copyright.md).

**Email:** contact@riteshrana.engineer

**Related:** [Terms of Service](../terms/) · [Privacy policy](../privacy/) · [Data sources](../data-sources/)
