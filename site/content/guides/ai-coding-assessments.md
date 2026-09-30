---
title: AI coding assessments for new grads
description: How AI is used in take-home and live coding assessments, what employers allow, and how to prepare without misrepresenting how you code.
updated: 2026-09-30
section: AI and job search
order: 3
---

Some employers now allow AI tools in their coding assessments and some prohibit them, and the rules change by role, by team, and by year. This guide explains what to expect and how to find out what your specific assessment allows.

> **Every employer and platform sets its own rules. Read the candidate instructions for the specific assessment rather than assume any tool is allowed.**

For the broader interview format landscape, see [AI-assisted interviews](../ai-assisted-interviews/). For AI use in the application itself, see [AI-assisted applications: what not to automate](../ai-applications-what-not-to-automate/).

## Where AI shows up in coding assessments

- **AI-assisted take-home.** You build a small project at home over a few days. Some employers expect you to use an AI tool; some forbid it. The instructions usually say.
- **AI-assisted live coding.** You solve a problem in a shared environment with a human interviewer. The platform may have an AI assistant built in; whether you are allowed to use it varies.
- **AI-graded assessment.** The platform uses a model to grade your solution, sometimes alongside a human reviewer. Ask which rubric and review process apply; do not try to guess a hidden model's preferences.
- **Asynchronous AI evaluation.** You submit a coding challenge; a model evaluates correctness, style, or both. A human review may follow; check the employer's process rather than assume it.
- **AI-proctored assessment.** A model watches your screen, your camera, or your typing pattern while you take the assessment. Disallowed tools or sites open during the assessment can trigger a flag.

These features can be combined. Confirm which are actually enabled for your assessment. Automated test-case scoring is also different from a generative model reviewing your work.

## How to find out what your specific assessment allows

1. **Read the invitation email.** Most invitations state the rules. If it says nothing, ask the assessment contact; use AI only within explicit permission from the employer for that assessment.
2. **Read the candidate instructions page.** The platform's pre-assessment page usually has an "AI policy" or "tools allowed" section.
3. **Read the assessment environment header.** The platform often shows what tools and sites it has whitelisted or blacklisted.
4. **Ask the recruiter.** If it is still ambiguous after the three reads, ask. A direct question is the right move; an assumption you get wrong is the wrong one.

## What to do when AI is allowed

- Use it deliberately: to check edge cases, look up language APIs you have not used in a while, and explore alternatives to your first idea.
- Start with your own understanding of the requirements. Use AI for a draft or review only when permitted, and verify the design choices you will have to defend.
- Be ready to explain every line in the follow-up interview. Both the submission and any follow-up may be evaluated.
- Keep the AI's output small enough that you can trace it. A 200-line patch you did not write is a problem in the follow-up.

## What to do when AI is prohibited

- Close every AI tool before the timer starts. Browser tabs, IDE plugins, the OS-level assistant.
- Monitoring varies by enabled features. [HackerRank documents several integrity modes](https://support.hackerrank.com/articles/1079706165-proctoring-hackerrank-tests), with different browser, screen, and webcam controls. Follow the stated rules and close prohibited resources; an integrity flag requires review and is not automatically proof of misconduct.
- If the platform fails, leave prohibited tools closed, document the error, and contact support. Follow the restart instructions.
- If your study habits depend on AI, practice a few rounds without it before the assessment. The first rep cold-turkey is the worst rep.

## What to do when it is ambiguous

If the invitation, instructions, and platform do not say, default to the conservative reading: AI is not allowed. Ask the recruiter if you have time. If the assessment starts in five minutes and the answer is not clear, write your own code.

## The follow-up interview

An AI coding assessment may be followed by a live interview where you walk the interviewer through your solution. Two common failure modes:

- You cannot explain a section of the code because the AI wrote it. The interviewer will notice.
- The interviewer asks you to modify the solution in real time. If you used AI on the original, the modification can fall apart.

For both reasons, the safest pattern is to write the solution yourself and use AI as a reviewer.

## What this means for preparation

- If your target companies allow AI in coding assessments, build a small project with one and walk through it yourself afterwards. Get used to the rhythm: prompt, read, edit, defend.
- If your target companies prohibit AI, practice at least one take-home and one live coding round without any AI tool. Time-box yourself the way the real assessment will.
- See [The new grad interview process](../interview-process/) for where coding assessments fit in the loop, and [LeetCode roadmap for new grads](../leetcode-roadmap-for-new-grads/) for the patterns to study.
