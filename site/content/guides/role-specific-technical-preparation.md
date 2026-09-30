---
title: Role-specific technical preparation for new grads
description: How to read a posting and build a preparation plan for the exact role, rather than the role you wish it was.
updated: 2026-09-30
section: Technical preparation
order: 7
---

A posting for a "Software Engineer, New Grad" at one company is a backend role; at another it is a mobile role; at another it is a tooling or infrastructure role. Each has its own preparation. The general rule is the same as the rest of this guide: prepare for the format and role the employer actually gave you, not the one you wish they had.

If you have already identified that the role is one of the tracks below, jump to that guide. If you are not sure, read on.

## How to tell which track you are looking at

Three signals:

- **The title.** Backend / platform / infrastructure / SRE / systems → [Systems interview preparation](../systems-interview-preparation/). ML / AI / research scientist → [ML/AI interview preparation](../ml-ai-interview-preparation/). Data / analytics / BI → [SQL interview preparation](../sql-interview-preparation/). Cloud / DevOps → [Cloud interview preparation](../cloud-interview-preparation/). Frontend / mobile / full-stack → see below.
- **The job description's verbs.** "Build a feature end to end", "ship to production", "work with stakeholders" usually indicates product engineering. "Operate the platform", "improve reliability", "on-call" usually indicates platform/SRE. "Train models", "evaluate on offline metrics", "run experiments" indicates ML.
- **The team page and recent blog posts.** This is the strongest signal. A team that talks about their recommender system is an ML team; a team that talks about their storage engine is a systems team. Read the team's last quarter of blog posts before you prepare.

## Frontend, mobile, and full-stack roles

Most loops combine LeetCode-style coding with a frontend or mobile-specific round. The frontend round usually asks you to build a small UI from a spec: a dropdown, a sortable table, a small game. The mobile round usually asks you to design a screen's data flow or implement a small view.

Prepare by:

- Picking one framework you know well (React, SwiftUI, Compose, Vue, whatever the role uses) and building a small project end to end with it. Not a tutorial; a thing you decided to build.
- Practicing the spec-driven UI problem. Given a spec, build it under a timer.
- For mobile: be ready to talk about state management, navigation, and how the view connects to the model.
- For full-stack: be ready to talk about the API contract between the two ends.

## Embedded and hardware-adjacent roles

Less common on the software engineering side of the board, but they exist. These loops test:

- C or C++ fluency (memory model, pointers, lifetime, undefined behavior).
- Reading a datasheet or a hardware manual excerpt.
- A small embedded problem (interrupts, ring buffers, state machines).

The LeetCode-style round is often replaced by a longer paired-programming round on unfamiliar code. See [Debugging interview preparation](../debugging-interview-preparation/).

## Security roles

Some companies run a security-specific new-grad loop. It usually combines LeetCode-style coding, a security fundamentals round (threat modeling, common vulnerability classes, secure coding patterns), and a take-home CTF-style problem. Read the invitation carefully; the rules for AI use in a CTF take-home are often strict.

## Quant and research-engineering roles

These loops usually test probability, statistics, mental math, and sometimes a small modeling problem. Coding may be in Python or a domain-specific language. See [ML/AI interview preparation](../ml-ai-interview-preparation/) for the modeling overlap.

## How to build the prep plan

For each application:

1. Read the posting once for the verbs, twice for the specific technologies, three times for the team signals.
2. Pick one or two preparation guides above that match the track.
3. Add one week of role-specific prep on top of your base prep (DSA, behavioral, project work).
4. Adjust for the assessment format — see [AI-assisted interviews](../ai-assisted-interviews/).

That is the plan that beats a generic "do 100 LeetCode problems" plan because it matches what the company actually gave you.
