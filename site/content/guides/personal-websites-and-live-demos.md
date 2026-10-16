---
title: Personal websites and live demos
description: When a portfolio site or live demo helps, what to put on it, how to keep it working, protect your privacy and meet basic accessibility checks.
updated: 2026-10-15
published: 2026-10-15
section: GitHub and portfolio
order: 3
format: checklist
use_when: Read this when you are deciding whether to build a portfolio site or a live demo, or want an existing one to hold up when a reviewer clicks.
you_get: You get when a site helps, a page outline, a demo-maintenance routine, privacy and accessibility checks, and free hosting options.
---

A personal site is a place to put evidence that a résumé cannot hold: a design case study, a working dashboard, a writing sample, a video of a robot you built. It is optional. When it exists, it has to load, work and be safe to share. This guide covers when to build one, what goes on it and how to keep it working.

## When a site or demo helps

A site earns its place when the work is easier to judge by seeing or using it than by reading a bullet point.

| Field | What a site or demo can show |
|---|---|
| Design, UX, architecture | Case studies with the problem, process, constraints and final work |
| Frontend and web development | A deployed app a reviewer can click through |
| Data and analytics | An interactive dashboard or a written analysis with charts and the data source |
| Writing, communications, journalism | Published clips or edited samples, with dates and outlets |
| Marketing | Campaign examples with the goal, your part and the results you can show |
| Mechanical, electrical, civil engineering | Photos, drawings, test results and a short video of a build working |

If the roles you target never look at portfolios and your work already reads well on a résumé and in [a GitHub profile](../github-profile-for-new-grads/), a site may add little. Spend the time on [projects that count](../new-grad-projects/) instead.

## What to put on it

Keep it to a few pages a reviewer can scan.

1. **Home:** your name, the kind of role you want, and two or three featured pieces with one line each.
2. **One page per featured project:** what it is, who it was for, your part, decisions you made, the result and a link to the live demo, repository or file.
3. **About:** a short paragraph on your background, plus a résumé link.
4. **Contact:** a professional email address or a contact form, plus LinkedIn.

On each project, separate your work from the team's and from any template or tutorial. If a client or employer owns the work, get permission before publishing it, and remove confidential details. Use real outcomes only, the same standard as in [The résumé evidence test](../resume-evidence-test/).

## Privacy: what not to publish

A portfolio is public. Treat everything on it as visible to anyone.

- Do not publish your home address, personal phone number, date of birth or ID numbers. A city and a professional email are enough.
- Strip location data from photos, and blur faces or names of people who have not agreed to appear.
- Do not post confidential employer, client or patient information, even in a screenshot.
- Check the repository behind the site for keys, passwords and personal data before you publish. Assume it is visible too.

::: evidence official
GitHub's documentation states that [GitHub Pages sites are publicly available on the internet, even if the repository is private](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site) where a plan allows private repositories, and advises removing sensitive data from the repository before publishing. On GitHub Free, the repository must be public.
:::

If you also contribute code publicly, GitHub lets you [use a noreply address for commits](https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-personal-account-on-github/managing-email-preferences/setting-your-commit-email-address) so your personal email does not appear in them.

## Keeping demos working

A broken link undercuts the evidence it was meant to show. Run this routine before each round of applications and after any change.

- **Open every link** from a private browser window, on a phone as well as a laptop.
- **Use sample data.** Never connect a public demo to real personal data. Label sample data as sample data.
- **Keep secrets out of the browser.** API keys in frontend code are visible to visitors.
- **Plan for the demo being down.** A free service may pause, limit or remove a project. Add a short screen recording and screenshots to the project page so a reviewer can still see it work.
- **Pin versions** and write down how to redeploy, so you can fix it quickly when something breaks.
- **Mark old projects** with the date, or take them down if you can no longer maintain them.

## Accessibility basics

Reviewers, like any visitors, may use a screen reader, keyboard navigation or zoom. You do not need a full audit to cover the basics.

- Give informative images a text alternative and leave decorative ones empty.
- Use real headings in order, and descriptive link text rather than "click here".
- Check text contrast. WCAG's minimum for normal text is a ratio of 4.5:1.
- Make everything usable with a keyboard, with a visible focus outline.
- Caption videos and provide transcripts for audio.
- Make sure text can be enlarged without breaking the layout.

::: evidence official
The W3C's [How to Meet WCAG (Quick Reference)](https://www.w3.org/WAI/WCAG22/quickref/) lists each success criterion, including 1.1.1 Non-text Content, 1.4.3 Contrast (Minimum) and 2.1.1 Keyboard. Its [Easy Checks](https://www.w3.org/WAI/test-evaluate/preliminary/) page gives a first review anyone can run: page titles, alt text, headings, contrast, text resizing, keyboard access, forms, moving content and multimedia alternatives.
:::

## Free hosting options

Several services host static sites at no cost, within their published limits and terms. Read the current documentation before you commit to one.

- **GitHub Pages** publishes a site from a repository. Its [usage limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) include a 1 GB maximum published site size and a soft bandwidth limit of 100 GB per month, and it is not intended as free hosting for an online business or for sensitive transactions.
- **GitLab Pages** [publishes static sites from a GitLab repository](https://docs.gitlab.com/user/project/pages/) through GitLab CI/CD and is listed on the Free tier. It supports static site generators and plain HTML, but not server-side code.
- **Your school** may offer web space or a portfolio platform. Ask what happens to it after you graduate.

A custom domain is optional. If you buy one, set a renewal reminder so the address you put on your résumé does not lapse.

## Linking it from your application

Put the site URL in your résumé header and on LinkedIn, and link individual project pages where a posting asks for work samples. See [Cover letters and application questions](../cover-letters-and-application-questions/) for portfolio fields in application forms, and [What makes a GitHub repository impressive?](../what-makes-a-github-repo-impressive/) for the repository behind a demo.
