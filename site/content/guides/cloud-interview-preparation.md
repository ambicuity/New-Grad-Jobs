---
title: Cloud interview preparation for new grads
description: What cloud / platform / DevOps new-grad loops test, the small set of services to know, and the depth that is overkill.
updated: 2026-09-30
section: Technical preparation
order: 5
---

Cloud new-grad loops usually combine a coding round (LeetCode-style or take-home), a systems round, and a cloud-specific round that tests your familiarity with the platform the company uses. Some loops swap one of those for a take-home on a Terraform or YAML exercise. Read the invitation to confirm the format before you start preparing. See [AI-assisted interviews](../ai-assisted-interviews/) for the rules of the platform and [The new grad interview process](../interview-process/) for where this fits.

For broader backend prep, see [Systems interview preparation](../systems-interview-preparation/). For the debugging track, see [Debugging interview preparation](../debugging-interview-preparation/).

## What is tested at new grad level

- **The mental model of the platform.** What a region is, what a zone is, what a managed service gives up relative to running it yourself, what the cost structure looks like.
- **The handful of services used by every team.** Object storage, a queue, a database, a load balancer, an identity service. You should be able to describe what each does and when to pick it.
- **Failure modes.** What happens when a single AZ goes down. What happens when an S3 bucket becomes public by accident. Why the IAM policy you wrote is too permissive.
- **Trade-offs.** Why a managed database is usually right, when a VM is right, what serverless is good for and what it is bad for.
- **Coding.** A small script in Python, Go, or TypeScript that uses one of the services above. Sometimes Terraform or YAML.

## What is not usually tested

- Specific pricing of every SKU.
- Every product in the catalog.
- Certification-level depth (e.g., answering every question on a Solutions Architect Associate exam).
- Networking at packet level.

## How to prepare

- Pick one provider (AWS, GCP, or Azure — whichever the company uses). Build one small project end to end on it: a static site, an API, a queue worker, a database.
- Read the official "What is X?" page for each of the core services. Not the full docs; the overview.
- Break something on purpose. Make a bucket public. Delete a database. Add a bad IAM rule. Watch what the platform tells you. The thing you remember is the thing you broke.
- For the systems round, see [Systems interview preparation](../systems-interview-preparation/).
- For the coding round, see [LeetCode roadmap for new grads](../leetcode-roadmap-for-new-grads/).

## How to answer trade-off questions

The pattern: name the option, name the cost, name what you would monitor to know if the cost was the right call.

> "I'd start with the managed database because the team has two engineers and we shouldn't be on call for replication. The cost is the per-query price; I'd watch the bill monthly and revisit if a workload gets hot."

That sentence is the cloud round, repeated.
