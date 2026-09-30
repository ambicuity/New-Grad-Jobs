---
title: What makes a GitHub repository impressive?
description: A practical checklist for explaining, running, and verifying the work in your repository.
updated: 2026-09-30
section: GitHub and portfolio
order: 2
---

Make it easy for a reviewer to understand your work, run it, and verify its behavior. The checklist below is a presentation strategy; review order and time vary by employer.

## 1. README that explains the project in 60 seconds

The README is the front door. A reviewer who lands on the repo should know, in under a minute:

- What the project does, in one sentence.
- A screenshot or short GIF of it running.
- How to install and run it locally, copy-paste.
- What you built versus what came from a tutorial or template.

Credit the tutorial or template, then explain the features and decisions you contributed.

## 2. Code that someone else could run

A repo without a working `README.md` install section is not a project; it is a zip file. Verify this with a fresh clone in a separate directory or a clean environment, following your own instructions. If anything fails, fix it before you pin the repo.

## 3. Code that looks like you wrote it

A repo where every file is a tutorial walkthrough is easy to spot and easy to discount. The commits that matter are the ones after the tutorial: the bug you fixed because the tutorial was wrong, the feature you added because you wanted it, the refactor you did because the structure annoyed you.

If you built the project from scratch, say so. If you forked and extended, also say so and explain what you added.

## 4. Tests, or the absence explained

You do not need 100% coverage, but a single test file that proves the project does what the README says is the difference between "code I read" and "code that runs". For libraries, test the main API and important failure cases. For apps, test meaningful behavior and include a screenshot or recording as a demonstration; a recording does not replace automated tests.

## What to keep in perspective

- Stars and forks provide context, but do not establish your contribution or code quality.
- Languages and frameworks can matter for a specific role; explain how your work maps to its requirements.
- File counts and activity graphs do not measure quality.

If you used AI, identify your contribution and explain how you reviewed, tested, and changed the output. Include reproducible dependency setup and keep credentials and personal data out of the repository.

Pair this with [GitHub profile for new grads](../github-profile-for-new-grads/) for how to surface these repos.
