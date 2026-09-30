---
title: What makes a GitHub repository impressive?
description: The four things reviewers actually look at, in the order they look at them.
updated: 2026-09-30
section: GitHub and portfolio
order: 2
---

A repository gets opened, scanned, and closed in a few minutes. The reviewers are looking for one thing: evidence that you can write code someone else would want to read. The repo that wins does four things well, in this order.

## 1. README that explains the project in 60 seconds

The README is the front door. A reviewer who lands on the repo should know, in under a minute:

- What the project does, in one sentence.
- A screenshot or short GIF of it running.
- How to install and run it locally, copy-paste.
- What you built versus what came from a tutorial or template.

A README that starts with "this is a [tutorial name] clone I followed" is honest and also self-defeating. Frame what you added; cite what you did not.

## 2. Code that someone else could run

A repo without a working `README.md` install section is not a project; it is a zip file. Verify this by deleting your local copy and following your own instructions on a clean machine. If anything fails, fix it before you pin the repo.

## 3. Code that looks like you wrote it

A repo where every file is a tutorial walkthrough is easy to spot and easy to discount. The commits that matter are the ones after the tutorial: the bug you fixed because the tutorial was wrong, the feature you added because you wanted it, the refactor you did because the structure annoyed you.

If you built the project from scratch, say so. If you forked and extended, also say so and explain what you added.

## 4. Tests, or the absence explained

You do not need 100% coverage, but a single test file that proves the project does what the README says is the difference between "code I read" and "code that runs". For libraries, one or two unit tests on the main API. For apps, a screenshot or short recording of the happy path.

## What does not matter

- Stars and forks. Reviewers know how to ignore them.
- Languages and frameworks. They pick the project first and the language second.
- The number of files. One tight repo is worth more than five sprawling ones.

Pair this with [GitHub profile for new grads](../github-profile-for-new-grads/) for how to surface these repos.
