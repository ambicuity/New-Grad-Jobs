---
title: ML/AI interview preparation for new grads
description: What machine-learning and AI new-grad loops actually test, and what to skip.
updated: 2026-09-30
section: Technical preparation
order: 4
---

ML and AI new-grad interviews come in several formats: classical ML theory questions, deep learning / LLM-specific questions, a take-home on a small dataset, a live coding round on data manipulation, a system design conversation about a small model service, or a domain case (recommender, search, ranking). Some loops include LeetCode-style coding; others do not. The first thing to do is read the invitation and identify the format. See [AI-assisted interviews](../ai-assisted-interviews/) for that step and [The new grad interview process](../interview-process/) for where the ML round fits in the loop.

## What is tested at new grad level

The core areas:

- **Classical ML fundamentals.** Bias-variance, train/validation/test splits, regularization, what cross-validation does and does not tell you. When to use which model family.
- **Applied ML.** Feature engineering for tabular data, evaluation metrics for the problem (not the model), the data leakage patterns that quietly inflate your validation score.
- **Statistics.** Probability, sampling, hypothesis tests, confidence intervals. The level tested is "what does this number actually mean", not "derive this from scratch".
- **Coding.** SQL for data manipulation, Python for prototyping, sometimes a small algorithms question. See [SQL interview preparation](../sql-interview-preparation/) and [LeetCode roadmap for new grads](../leetcode-roadmap-for-new-grads/).
- **Communication.** Translating a vague business question into an ML problem, and translating an ML answer back into a decision.

## What is not usually tested at new grad level

- Deriving backprop from scratch on the whiteboard.
- Reciting transformer architecture from memory.
- Recommender-system proofs.
- Specific vendor products.

If the role is research-oriented (foundations, applied research, post-training), the depth shifts toward the theoretical side; ask the recruiter what the round actually scores.

## How to prepare

- **Two weeks of fundamentals.** Read one good applied ML book end to end; do the exercises. Do not collect more books.
- **Two weeks on a real dataset.** Pick a Kaggle competition, finish a baseline, and write up what worked and what didn't. The write-up is the artifact the interviewer is most likely to ask about.
- **Two weeks on case questions.** Given a vague business problem (retention drops, recommendation quality, an LLM feature for a product), write a one-page memo: how would you frame it, what data you would look at first, what you would ship in two weeks versus two quarters.

## How to talk about projects

Interviewers at this level care about whether you can reason about a model in production, not whether you can recite its loss function. For each project, prepare:

- The business question, in plain English.
- The data you had, what was missing, and what you would do differently.
- The metric you picked, and why.
- The failure mode that worried you most.
- What you would change with two more weeks.

That last sentence — "what I would change" — is the strongest signal at new grad level. See [Behavioral interviews](../behavioral-interviews/) for the broader STAR structure when you have a non-ML story to tell.
