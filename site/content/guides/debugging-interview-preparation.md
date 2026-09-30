---
title: Debugging interview preparation for new grads
description: How debugging rounds work, how to talk through unfamiliar code out loud, and how to practice without a real codebase.
updated: 2026-09-30
section: Technical preparation
order: 6
---

Debugging rounds are common at backend, platform, infrastructure, and ML-platform companies. The interviewer hands you a small program that does not work — a bug in production, a flaky test, an output that is wrong by a row — and watches you find the bug out loud. The format may be live, AI-mediated, or asynchronous with a recorded walk-through. See [AI-assisted interviews](../ai-assisted-interviews/) for the platform rules.

## What is being scored

- **Hypothesis formation.** Did you read the code before changing it? Did you form a guess about what is wrong?
- **Instrumentation.** Did you add a print, a log, a breakpoint at the right place, and not before?
- **Reasoning about data.** Did you trace the actual values through the function, or did you guess?
- **Communication.** Did you narrate each move so the interviewer could follow?
- **Stopping.** Did you confirm the fix and explain why, instead of moving on to the next guess?

## A working method

1. Read the problem statement and the code out loud. Say what you think the program is supposed to do in one sentence.
2. Find the smallest input that exhibits the bug, or trace the smallest failing example the interviewer gives you.
3. Form a hypothesis before you run anything. "I think this fails when the input is empty because this branch assumes the list has at least one element." State it.
4. Instrument to test the hypothesis. Add a print, a breakpoint, a log line. Do not edit the code yet.
5. Confirm or refute. If refuted, name the new hypothesis, then repeat.
6. When you fix it, name the bug class: "this was an off-by-one in the loop bound." Interviewers want you to recognize the pattern.

## How to practice without a real codebase

- Pick any open-source repo in a language you know. Open a file at random. Read it out loud as if you were about to debug it. State what it does in one sentence. State what you would test first.
- Use small buggy programs you or a practice partner create; keep the expected behavior and a reproducible failing case. Time yourself: ten minutes per bug.
- Read other people's bug reports on GitHub Issues. Most issues are debugging write-ups in disguise. Note the structure: problem, repro, hypothesis, fix, regression test.
- Pair with another candidate. Take a program, swap it for a buggy version, and time-box the other person to find the bug.

## Topics that depend on the role

- Deep knowledge of a specific debugger.
- Reading hex dumps.
- Production tracing systems.
- Build-system and dependency failures.

Any of these may appear in a systems, embedded, or production-support interview. Check the brief rather than excluding them automatically.

## How this connects to the rest of the prep

Debugging is the live-coding cousin of the algorithmic round. Same "talk out loud, name your guess, instrument, confirm" muscle. If your LeetCode prep includes practice explaining your reasoning while you code — see [How to handle an interview question you don't know](../how-to-handle-an-interview-question-you-dont-know/) — you are already training the debugging muscle too.
