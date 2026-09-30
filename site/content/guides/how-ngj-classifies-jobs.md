---
title: How NGJ classifies jobs
description: The rules that decide whether a posting is a new grad job, which category it lands in, and which flags it gets, in the order they run.
updated: 2026-09-30
section: NGJ data
order: 2
---

Every posting goes through the same fixed sequence of rules, written in the scraper's configuration and source. There is no model guessing and no hand editing, which means the rules can be wrong in predictable ways and can be corrected by anyone who reads them. This page walks the sequence.

## 1. Hard rules: is it new grad at all?

A posting must pass all of these to reach the board. Matching is on whole words, never on substrings, so "intern" does not match "international" and "lead" does not match "leadership".

- **No exclusion word** in the title: senior, sr, staff, principal, lead, manager, director, VP, vice president, head of, architect, distinguished, fellow, or an experience floor of "5+ years" and up. One family of titles is exempted because "associate" is the level there, not a seniority word: associate product, program or project manager, including the technical variants. A seniority word elsewhere in such a title still excludes it.
- **An early-career signal in the title.** The configured signals include "new grad", "graduate program", "campus", "early career", cohort years, "junior", "associate", "entry level", level markers and some common entry role names. An internship title can also pass this gate before the soft rules are applied. A signal only in the description does not pass this title-based gate.
- **A strong new-grad phrase or a role word in the title**: engineer, developer, analyst, designer, nurse, accountant, consultant, coordinator, specialist and dozens more covering every field. A strong program phrase can pass even without a separate role word. See [What counts as a new grad job?](../what-counts-as-a-new-grad-job/).

## 2. Soft rules: the near-miss tier

A posting that passes the hard rules but fails one or more of these becomes a near miss, subject to the configured size cap. It is visible behind WIDEN SCOPE only when you enable every reason recorded for that posting, and is never included in curated counts:

- it is an internship, co-op, student placement or summer program
- its title is level III or higher
- its location is outside the United States, Canada and India, and it is not plainly remote
- it was posted 60 to 120 days ago

Older than 120 days is out. The location rule reads the text in segments: an explicit target country passes, a named foreign country or city fails, an unqualified "Remote" passes, a US state or a known city passes. An empty location passes as a permissive fallback; it does not establish eligibility to work from any particular country.

## 3. Category

Each job gets one of thirty categories. The title is checked first against exact patterns ("Software Engineer", "Registered Nurse"), then against looser title patterns, then the description, then a last-resort pattern, and finally "other". Technical program manager and network engineer are special-cased because their titles match several categories. The categories are the ROLE facet, the feeds, the landing pages and the README table, all from the same list.

## 4. Company tier

Company names are matched against two lists: the largest technology and finance employers (FAANG+) and well-funded startups (unicorn). Everything else is "other". This is a name list, not a judgment; a company missing from it simply shows as other.

## 5. Flags

- **No sponsorship** and **citizenship required** come from phrase lists; [Sponsorship language](../sponsorship-language/) has them.
- **Closed** comes from strict phrases in the description or markers in the title; [Expired jobs](../expired-jobs/) explains.
- **Remote** is read from the location text and the title.
- **Compensation** is shown when the source provides a range.

## When the rules are wrong

They are, sometimes. A title that fails the configured signal or role checks is invisible on the curated board even if its description welcomes graduates; the EXPLORE tab exists for that, and [Finding hidden new grad roles](../finding-hidden-new-grad-roles/) explains it. A miscategorized title or a missing company can be reported in the repository. The exact current gates live in [filters.py](https://github.com/ambicuity/New-Grad-Jobs/blob/main/scripts/ngj/filters.py) and [config.yml](https://github.com/ambicuity/New-Grad-Jobs/blob/main/config.yml).
