---
title: Online coding assessments
description: What automated assessments test, how they are scored, and a preparation plan that fits around coursework.
updated: 2026-09-25
section: Interviews
order: 2
---

Many large employers send new grad applicants a timed online assessment before anyone has spoken to them. It is the cheapest filter they have, and for the applicant it is the stage most often failed by people who would have done fine in an interview. The difference is preparation for the format, not the content.

## The format

A link, a deadline to start (often a week), then a fixed time window once you begin, commonly one to two hours. Two to four problems, usually of increasing difficulty, in a browser editor with a hidden test suite. Some platforms record the screen or ask for the camera; read the instructions before starting.

Scoring is mostly automatic: how many hidden tests pass, sometimes weighted by problem. Partial credit is common, so a working solution that is slow scores better than a fast one that is wrong. A few employers also review the code afterwards.

## What the problems test

- Reading a problem statement precisely, including the edge cases in the constraints
- Arrays, strings, hash maps, sorting, two pointers, prefix sums
- Recursion and simple dynamic programming
- Trees and graphs: traversal, shortest path in unweighted graphs
- Implementing a small simulation exactly as specified

Most new grad assessments do not go beyond this. The harder problem at the end is there to separate the top of the pool, and missing it is not a failure.

## A preparation plan

1. **Learn the platform.** Practice on the same kind of editor with the same time limit. The mechanics (reading input, choosing a language, running custom tests) should be automatic.
2. **Drill the categories above until each is familiar**, not until you have seen every problem. Two or three problems per category, understood thoroughly, beats fifty half-remembered. If a category is new to you rather than rusty, learn it properly first; the free [Computer Science course](https://course-computer-science.riteshrana.engineer/) covers data structures and algorithms from first principles.
3. **Time yourself** for the last third of your practice. The skill is finishing within the window.
4. **Write tests before submitting.** Empty input, one element, duplicates, maximum size, negative numbers. Hidden suites are built from exactly these.

## During the assessment

- Read every problem first and start with the one you are surest of.
- Get a correct brute-force solution down, submit, then improve. Partial credit is real.
- Do not leave a problem with zero output. Handle the trivial cases even if the general one is beyond you.
- Watch the clock and leave five minutes for a final submit of every problem.

## Integrity

Assessments come with rules, and employers enforce them: plagiarism checks across candidates, proctoring, and follow-up interviews that ask you to explain your submission. Solve it yourself. A pass you cannot explain in the next round costs more than a fail.

## After

Note the problems you saw in your tracker; patterns repeat within a company and across a hiring season. If you fail, the same employer often allows another attempt next cycle, and the categories above are exactly what to practice. The [Coding interviews](../coding-interviews/) guide covers the live version.
