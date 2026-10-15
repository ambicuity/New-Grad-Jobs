---
title: Terms of Service
description: The rules for using NGJ (New Grad Jobs): what the board is and is not, how job listings work, acceptable use, the public data files, intellectual property, disclaimers and how to reach the maintainer.
effective: 2026-10-15
updated: 2026-10-15
---

These terms apply to the NGJ (New Grad Jobs) website at [jobs.riteshrana.engineer](https://jobs.riteshrana.engineer/), its static pages, its public data files and feeds, and the source code repository at [github.com/ambicuity/New-Grad-Jobs](https://github.com/ambicuity/New-Grad-Jobs). By using the site you agree to them. If you do not agree, please do not use the site.

## 1. Who runs NGJ

NGJ is maintained by Ritesh Rana (the "maintainer", "we" or "us"). You can reach the maintainer at **contact@riteshrana.engineer**. Corrections to listings can also be opened as [GitHub issues](https://github.com/ambicuity/New-Grad-Jobs/issues), which are public.

In these terms, "NGJ" or "the service" means the website, its pages and the files it publishes. A "listing" is a job posting shown on NGJ. An "employer" is the organisation that published the original posting.

## 2. What NGJ is, and what it is not

NGJ is a free job-discovery service. An automated program collects postings from employers' own careers systems (such as Greenhouse, Lever, Ashby, Workday and others) and from Indeed. It keeps the postings that look like new grad or entry-level roles in the United States, Canada and India, and publishes them as static web pages and files about every 30 minutes. The [data sources page](../data-sources/) lists every source.

NGJ is **not** an employer, recruiter, staffing agency, employment agency or placement service. It does not represent you or any employer, and it does not receive, read, forward or screen applications. When you choose APPLY, you leave NGJ for the employer's own site, where the employer's terms apply. NGJ charges nothing and does not take payment from anyone to list a job. The site shows sponsor and donation links, which are labelled.

There are no accounts on NGJ. You do not need to sign up, and the site has no forms that collect information from you.

## 3. Who may use NGJ

NGJ is meant for students, recent graduates and anyone else looking for an early-career job. It is not directed at children under 13. If you are under the age of majority where you live, please use NGJ with the involvement of a parent or guardian, and follow the minimum-age rules of any employer you apply to.

## 4. Job listings come from third parties

Every listing comes from an employer or from Indeed. NGJ filters, categorises and formats listings by rule, but it does not write them, and it does not check each one by hand. That means:

- **Listings can be wrong or out of date.** A role may close, change or be removed after NGJ last checked it. Titles, locations, salaries and descriptions are shown as the source published them, sometimes shortened.
- **Labels are automated.** Categories, "new grad" signals, company tiers and the visa labels are applied by rules and can be wrong. "No restriction stated" means NGJ found no stated sponsorship or citizenship restriction in the posting. It is not a promise that a role sponsors visas.
- **Salary is only what the posting says.** NGJ never estimates pay.
- **NGJ does not vet employers.** Listings are collected from the employer's own careers system wherever possible, but NGJ cannot confirm that every posting is genuine. A real employer will not ask you to pay to apply, buy equipment up front, or share bank details before an offer. If a listing looks like a scam, please report it (section 9).

Always confirm the details that matter to you, such as the role, location, pay, work authorisation and deadline, on the employer's own page before you apply.

## 5. No employment outcome is promised

NGJ does not promise any interview, offer, salary, visa sponsorship, start date or other outcome. Hiring decisions are made only by employers. NGJ is not responsible for an employer's hiring process, its decisions or how it treats your application.

## 6. Links to other sites

NGJ links to employers' sites, to job systems, to GitHub, to sponsors and to other websites. NGJ does not control those sites. Their content, availability, terms and privacy practices are their own. A link does not mean that NGJ endorses the site, or that the site endorses NGJ.

## 7. Acceptable use

You may use NGJ for any lawful purpose. When you do, please do not:

- break the law, or use NGJ to defraud, harass, spam or mislead anyone, including employers and other job seekers;
- try to break into, disrupt, overload or probe for weaknesses in the site or its hosting, except through the responsible disclosure process in the repository's [security policy](https://github.com/ambicuity/New-Grad-Jobs/security/policy);
- add malware, or try to bypass the site's security controls (such as its Content Security Policy);
- pretend to be NGJ or the maintainer, or suggest that NGJ, an employer or a source platform endorses you or your product when it does not.

**Automated access is allowed.** Search engines, accessibility tools, feed readers, research tools and other software may read NGJ. Please keep request rates moderate, follow [robots.txt](../robots.txt), and prefer the published data files ([jobs.json](../jobs.json), the [RSS feeds](../feed.xml) and [llms.txt](../llms.txt)) to fetching thousands of pages one by one. The data files are regenerated on every run and contain everything the pages show. GitHub, which hosts the site, may limit traffic that harms its service.

## 8. Using NGJ's data files

NGJ publishes its listings as files, including `jobs.json`, `jobs-index.json`, `descriptions/`, `jobs-extended.json`, `corpus-index.json`, `health.json` and the RSS feeds. You are welcome to read and use them. When you do:

- **Third-party content is not NGJ's to license.** Job titles, descriptions and other posting text belong to the employers or source platforms that published them. Employer names and marks belong to their owners. Reusing that content, especially republishing it in bulk or commercially, may need the owner's permission. These terms do not grant it. See the [copyright and attribution policy](../copyright/).
- **NGJ's own additions** (the field names and schema, category labels, flags and the way the data is organised), to the extent NGJ has rights in them, may be used under the same MIT License as the source code.
- Please credit the employer, link to the original posting, and say that the listing came from NGJ if you republish it. Do not suggest that NGJ, an employer or a source platform endorses your use.
- The files are a snapshot. Check the `generated_at` time, and confirm a listing with the employer before relying on it.

## 9. Reporting a problem

To report an inaccurate, expired, misleading, fraudulent or improperly attributed listing, a copyright or trademark concern, or a privacy concern, follow the process in the [copyright and attribution policy](../copyright/). Simple corrections can be filed as a public [GitHub issue](https://github.com/ambicuity/New-Grad-Jobs/issues). Anything private or legal should go by email to **contact@riteshrana.engineer**.

## 10. Intellectual property

- **Source code and repository content.** The code, guides and documentation in the repository are published under the [MIT License](https://github.com/ambicuity/New-Grad-Jobs/blob/main/LICENSE), copyright Ritesh Rana, unless a file says otherwise. The MIT License covers the maintainer's own work only. It does not cover third-party job content, employer names or marks, or third-party software, which keep their own licences (see the [third-party notices](../third-party-licenses.txt)).
- **The NGJ name.** The MIT License does not grant permission to use the names "NGJ" or "New Grad Jobs", or the site's branding, in a way that suggests your project is NGJ or is endorsed by it.
- **Third-party content.** NGJ claims no ownership of job postings, employer names, logos or trademarks. They are shown to identify the employer and the job, and to link to the original posting.

## 11. Availability and changes to the service

NGJ runs on free infrastructure (GitHub Actions and GitHub Pages) and depends on many third-party sources. Scrapes fail, sources change, and listings can be delayed, missing or duplicated. The maintainer tries to keep the site running and accurate, and reports each run's status on the [about page](../about/), but does not guarantee that NGJ will be available, current or error-free. The maintainer may change, pause or discontinue any part of NGJ at any time.

## 12. Disclaimers

NGJ is provided free of charge, "as is" and "as available". To the extent the law allows, the maintainer makes no warranties about NGJ or its listings, whether express or implied, including warranties of accuracy, completeness, fitness for a particular purpose and non-infringement.

Some laws do not allow these warranties to be excluded. In that case, they are excluded only as far as the law allows. Nothing in these terms limits any right you have that cannot be waived or limited by contract, including rights under consumer protection law where you live.

## 13. Limitation of liability

To the extent the law allows, the maintainer is not liable for any loss that comes from relying on a listing, from an employer's or a third-party site's conduct, from a missed opportunity, or from the service being unavailable, inaccurate or out of date. This includes indirect or consequential loss.

This section does not limit liability for fraud, wilful misconduct or gross negligence, for death or personal injury caused by negligence, or for anything else that cannot be limited under the law that applies.

## 14. Privacy

The [privacy policy](../privacy/) explains what information the site and its providers handle, and it is part of these terms.

## 15. Governing law and disputes

These terms do not choose a governing law or a court. If a dispute arises, the law and courts that apply are those determined by the ordinary rules where the dispute is heard. Nothing in these terms takes away protection you have under the law of the place where you live.

Before starting a formal dispute, please email the maintainer, who will try to resolve it informally.

## 16. Changes to these terms

The maintainer may update these terms. The "Last updated" date at the top of this page shows when they last changed. Material changes are described in the commit that makes them, and every earlier version is kept in the [file history on GitHub](https://github.com/ambicuity/New-Grad-Jobs/commits/main/site/content/legal/terms.md). If you keep using NGJ after a change takes effect, the updated terms apply from then on.

If any part of these terms is found unenforceable, the rest stays in effect.

## 17. Contact

**Email:** contact@riteshrana.engineer

**Public issues and corrections:** [github.com/ambicuity/New-Grad-Jobs/issues](https://github.com/ambicuity/New-Grad-Jobs/issues)

**Security reports:** [GitHub private vulnerability reporting](https://github.com/ambicuity/New-Grad-Jobs/security/advisories/new)
