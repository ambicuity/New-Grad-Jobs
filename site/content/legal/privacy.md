---
title: Privacy Policy
description: What information NGJ (New Grad Jobs) and the services it relies on handle when you visit, why, for how long, and how to exercise your privacy rights. No accounts, no forms, no cookies set by NGJ.
effective: 2026-10-15
updated: 2026-10-15
---

This policy explains what information is handled when you use NGJ (New Grad Jobs) at [jobs.riteshrana.engineer](https://jobs.riteshrana.engineer/), who handles it, and the choices you have. It describes what the site's code actually does. You can check every statement against the [source code](https://github.com/ambicuity/New-Grad-Jobs).

## 1. Summary

- NGJ has **no accounts, no sign-up, no forms, no advertising and no newsletter**. It does not ask for your name, email or résumé.
- NGJ sets **no cookies**. Your saved and applied jobs stay in your own browser's storage and are never sent anywhere.
- The main job board loads **GoatCounter**, a privacy-focused page counter. GoatCounter says it does not store IP addresses or set cookies. The other pages (job pages, guides, policies and the about page) run no scripts at all.
- The site is hosted on **GitHub Pages**. GitHub logs visitors' IP addresses for security.
- NGJ does **not sell** personal information, and does not share it for targeted advertising.

## 2. Who is responsible

NGJ is maintained by Ritesh Rana (the "maintainer", "we" or "us"), who decides how the site works and is responsible for this policy. For any privacy question or request, email **contact@riteshrana.engineer**.

GitHub and GoatCounter run their own services and are responsible for how they handle data under their own policies, which are linked below.

## 3. Information NGJ handles

### 3.1 Information you give us

The site has no forms, so it collects nothing from you directly. You may choose to contact the maintainer:

- **By email.** We receive your email address, name (if you include it) and whatever you write.
- **On GitHub.** Issues, pull requests, comments and commits in the repository are public. GitHub handles them under its own terms and [privacy statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement). Please do not post private information in an issue.

### 3.2 Hosting: GitHub Pages

Every request to the site goes to GitHub Pages. As with any website, your browser sends your IP address, your browser's user-agent string, the page requested and, in many cases, the page you came from. GitHub's documentation says that when a Pages site is visited, "the visitor's IP address is logged and stored for security purposes". GitHub decides how long it keeps those logs. GitHub Pages does not give site owners access to visitor logs, and the maintainer does not receive them.

### 3.3 Page counter: GoatCounter

The interactive job board (the home page) loads GoatCounter's script from `gc.zgo.at` about three seconds after the page finishes loading. It sends one count to `riteshrana.goatcounter.com` per page load. The count contains:

- the page path, which is always `/` because the board declares a canonical address;
- the page title, the referring page (if your browser provides it) and your screen width;
- the page's query string. **The board keeps your filters and search words in the address bar**, so the query string can include them, for example `?q=data+analyst&role=data_analyst`;
- what any web request carries: your IP address, your browser's user-agent and its language setting.

According to [GoatCounter's privacy policy](https://www.goatcounter.com/help/privacy), GoatCounter does not store IP addresses. It works out your country from the IP address and your browser and operating system from the user-agent, and it stores those as aggregate counts. It keeps a mapping of site, IP address and user-agent in memory for up to eight hours, so that repeat views can be counted as one visit, and stores only a random ID for it. GoatCounter states that it does not store anything in your browser, so it uses no cookies or local storage. The maintainer sees only GoatCounter's aggregate dashboard and has no way to identify you from it.

The job pages, guides, landing pages, policies and the about page do not load GoatCounter. Their security policy forbids all scripts.

### 3.4 Storage in your browser

NGJ uses your browser's `localStorage` for features you choose to use. The data never leaves your device.

| Key | What it holds | When it is written |
| --- | --- | --- |
| `ngj:saved-jobs:v1` | the IDs of jobs you starred | when you save a job |
| `ngj:applied-jobs:v1` | the IDs of jobs you marked as applied | when you mark a job applied |
| `ng-terminal:gh-v2` | a copy of public repository statistics from GitHub | when you open the CONTRIBUTORS tab; refreshed after an hour |
| `ng-terminal:gh-commits-v1:<username>` | a copy of a contributor's recent public commits from GitHub | when you open that contributor in the CONTRIBUTORS tab; refreshed after an hour |

Clearing your browser's site data for jobs.riteshrana.engineer deletes all of them.

### 3.5 Requests your browser makes to other services

- **GitHub API.** When you open the CONTRIBUTORS tab, your browser asks `api.github.com` for public repository statistics and recent commits. Contributor avatars load from `avatars.githubusercontent.com`. GitHub receives your IP address and browser details with these requests.
- **GoatCounter**, as described in section 3.3.
- **Employers.** When you follow an APPLY link, you go to the employer's or job system's site, and its own privacy policy applies. NGJ adds no tracking or affiliate parameters to these links, and they are opened with `noreferrer`, which tells your browser not to send NGJ's address.
- **Sponsor and donation links** (Tailr, Buy Me a Coffee) take you to those sites only if you click them.

Fonts, styles and the job data are served from NGJ's own domain.

### 3.6 Personal information inside job listings and public pages

Listings are collected from employers' public job postings, and their descriptions are republished in full. A posting sometimes includes a recruiter's or hiring manager's name or work email, and NGJ republishes it as part of the description. If you are named in a listing and want it removed, email the maintainer (see section 9). Removing it from the employer's own posting will also stop it from reappearing.

The CONTRIBUTORS tab shows the public GitHub usernames, names and avatars of people who have contributed to the repository.

## 4. Why information is handled, and the legal basis

Where the EU or UK General Data Protection Regulation (GDPR) applies, these are the purposes and the legal bases relied on:

| Purpose | Information | Legal basis (GDPR / UK GDPR) |
| --- | --- | --- |
| Delivering the site and keeping it secure | request data held by GitHub Pages | legitimate interests in running a secure website (Art. 6(1)(f)) |
| Counting visits in aggregate to see how the board is used | the GoatCounter data in section 3.3 | legitimate interests in understanding use of a free service with minimal data (Art. 6(1)(f)) |
| Saved and applied lists, contributor statistics | browser storage in section 3.4 | stored only on your device, at your request, to provide the feature you use |
| Publishing job listings that may contain names | names or work contact details in public postings | legitimate interests in helping job seekers find openings that employers chose to advertise publicly (Art. 6(1)(f)) |
| Replying to you | your email and message | legitimate interests in answering you (Art. 6(1)(f)), or a legal obligation where your request is a legal one (Art. 6(1)(c)) |

You may object to processing based on legitimate interests (section 8).

## 5. Sharing and disclosure

NGJ does not sell personal information, rent it, or share it for cross-context behavioural or targeted advertising. There are no advertising scripts or tracking pixels on the site. Information reaches others only in these ways:

- **Service providers**: GitHub (hosting, the GitHub API) and GoatCounter (page counts), as described above. Each runs its own service under its own policy, and NGJ does not claim that they act only on its instructions.
- **Employers and other sites** you choose to visit.
- **Legal requirements**: if the law requires it, or to protect the rights, safety or security of users, the public or NGJ.
- **A successor**: if the project is transferred to a new maintainer, this policy (or a notice of any change to it) would go with it.

## 6. International transfers

GitHub processes data in the United States and other countries. GoatCounter processes data under its own policy. If you visit from another country, your request data is handled in those countries. NGJ itself stores no visitor data on any server.

## 7. How long information is kept

- **Browser storage**: until you clear it. The contributor statistics are replaced after an hour.
- **GoatCounter**: aggregate counts stay in the maintainer's GoatCounter account until the maintainer deletes them. They contain no IP addresses.
- **GitHub Pages logs**: kept by GitHub according to its policies.
- **Email**: kept only as long as needed to handle your message, and to keep a record of any legal request and how it was handled.
- **Job data**: each published file is replaced on every run (about every 30 minutes). The repository's `README.md` job tables are committed after each run, so earlier listings remain visible in the public git history. Daily aggregate market snapshots (counts only, no listing text) are kept for 90 days.

## 8. Your rights and choices

### 8.1 Choices you can make now

- Clear the site data in your browser to delete saved and applied jobs.
- Block `gc.zgo.at` with a content blocker, or browse with JavaScript off, to stop the page counter. The static pages and the data files work without it.
- Avoid putting anything private in the board's search box if you do not want it in the address bar, and so in your browser history and the page count.

### 8.2 Rights under privacy laws

Depending on where you live, you may have the right to:

- know what personal information is held about you, and get a copy (access and portability);
- correct it;
- delete it;
- object to processing, or ask for it to be restricted;
- withdraw consent where processing is based on consent;
- opt out of the sale of personal information, of sharing for targeted advertising, and of profiling (NGJ does none of these);
- appeal a decision on your request, and complain to a regulator.

These rights come from laws such as the GDPR and UK GDPR, the California Consumer Privacy Act, the Texas Data Privacy and Security Act and other US state laws, Canada's PIPEDA, and India's Digital Personal Data Protection Act. Not every right applies to every person or to every service. Which laws apply to NGJ depends on facts such as where you live and the size and nature of the service, and the maintainer does not claim that any particular law does or does not apply. The maintainer will still handle requests from anyone, wherever they live.

**How to make a request.** Email **contact@riteshrana.engineer** with the subject "Privacy request" and say what you want. Because NGJ does not keep accounts or identifiers, there is usually nothing it can link to you. You may be asked for enough detail to find the information you mean, such as the listing or the email thread, but never for more than that request needs. You may use an authorised agent where the law allows it.

The maintainer aims to respond within one month, and within any shorter period your law requires. If your request is refused, you will be told why, and you can appeal by replying with the subject "Privacy appeal". The appeal will be reviewed again and answered in writing. You will not be treated differently for using your rights.

**Requests to GitHub or GoatCounter.** NGJ cannot access or delete data that GitHub or GoatCounter holds. Contact them using the links in section 3.

**Complaints.** You can complain to your data protection authority, for example the UK [Information Commissioner's Office](https://ico.org.uk/make-a-complaint/), the authority in your EU member state ([list from the EDPB](https://www.edpb.europa.eu/about-edpb/about-edpb/members_en)), or, in the United States, your state attorney general.

## 9. Children

NGJ is a job board for students and graduates and is not directed at children under 13. It does not knowingly collect personal information from children. If you believe a child has sent personal information to the maintainer, email contact@riteshrana.engineer and it will be deleted.

## 10. Security

The site is static: no server and no database are run by NGJ, and it holds no visitor accounts or passwords. GitHub Pages serves the site over HTTPS and redirects plain-HTTP requests. Every page has a restrictive Content Security Policy that limits which scripts and connections it may use. Every link to a job is checked at publication so that only public `http(s)` addresses are published. Dependencies are hash-locked, the build pipeline's actions are pinned to exact versions, and the code is scanned with GitHub CodeQL. No method of transmission over the internet is completely secure, and NGJ cannot guarantee the security of GitHub's or GoatCounter's systems. Please report vulnerabilities through the [security policy](https://github.com/ambicuity/New-Grad-Jobs/security/policy).

## 11. Changes to this policy

If NGJ's data practices change, for example by adding a new provider, this policy will be updated before or at the same time as the change, and the "Last updated" date will change. Every earlier version is kept in the [file history on GitHub](https://github.com/ambicuity/New-Grad-Jobs/commits/main/site/content/legal/privacy.md).

## 12. Contact

**Privacy requests and questions:** contact@riteshrana.engineer (subject "Privacy request")

**Related:** [Terms of Service](../terms/) · [Copyright and attribution policy](../copyright/) · [Data sources](../data-sources/)
