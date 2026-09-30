---
title: AI-assisted interviews for new grads
description: How AI is used in interviews today, how to identify the format you've been given, the rules each employer sets, and how to prepare without becoming dependent on the tool.
updated: 2026-09-30
section: Interviews
order: 9
---

Hiring teams use AI in interviews in many different ways, and each employer defines its own rules. The single most important principle is:

> **Every company and platform can set its own rules. Follow the instructions in the specific assessment you were given rather than assuming any AI tool is allowed.**

This guide explains what to expect, how to read the invitation, and how to prepare without misrepresenting how you work.

## How AI shows up in interviews today

A few distinct formats, which often appear together in one loop:

- **AI-scored interviews.** You record answers; a model scores them. Output is a score and sometimes a transcript the recruiter reads.
- **AI-moderated interviews.** A chatbot asks the questions in real time, possibly with adaptive follow-ups based on your last answer.
- **AI-generated follow-ups.** A human interviewer runs the loop, but the system suggests the next question based on what you said.
- **Asynchronous recorded interviews.** No live interviewer. You see a question, record an answer, and the next question adapts.
- **AI coding environments.** A coding platform (CoderPad, HackerRank, CodeSignal, etc.) where AI assistance may or may not be allowed.
- **Coding assessments with permitted AI.** Some employers now explicitly allow ChatGPT, Copilot, or Gemini; others explicitly prohibit them.
- **Coding assessments with prohibited AI.** The instruction is usually one line; treat it as binding.
- **Take-home and work-sample assessments.** Open-ended deliverables with a stated time budget and allowed-resources list.
- **Human + AI hybrid.** A human interviewer plus an AI tool on screen that the interviewer can see.
- **Live coding without AI.** The traditional format, still common at large companies.

These can co-exist within the same loop: a recruiter screen, an AI-scored asynchronous round, and a human-led final are all common together.

## Step 1: identify the format

Before you prepare, name what you have. The invitation email, the assessment URL, the candidate instructions page, and the assessment UI itself all tell you. Read them in order.

The questions to answer:

- Is this **live** with a human, **live with AI**, or **asynchronous** (you record, no one is on the other end)?
- Is the interview being **recorded**? If yes, the recording notice usually says so.
- What **platform** is it on? (HireVue, Modern Hire, Pymetrics, CoderPad, HackerRank, CodeSignal, Workday, Greenhouse, an internal tool.)
- **Is AI allowed?** Some invitations say explicitly. Others don't, which usually means no.
- **Is ChatGPT / Copilot / Gemini allowed?** Look for the named tools.
- **Are external websites allowed?** Some platforms block browser navigation.
- **Can you use documentation?** (Language docs, library docs, but not solutions to the problem.)
- **Can you run code locally?** Some platforms let you use your own editor.
- **Is the webcam required?** Is the **microphone** required?
- **Are there time limits? Can you pause? Can you restart?**
- **Are follow-up questions adaptive?** (The platform changes the next question based on your answer.)
- **What happens if the platform fails?** Who do you contact?

If an item is not stated, do not assume the answer that is convenient for you. Ask the recruiter.

## Step 2: the pre-assessment checklist

Run this list one day before (or earlier) and again one hour before. Each row is a yes/no or a fix:

```text
□ Platform identified and tested in a non-production preview
□ Browser updated; no extensions that block camera/mic
□ Camera, speakers, microphone tested on the same machine
□ Internet connection stable; backup hotspot noted
□ Quiet, well-lit space for camera if the format requires it
□ Allowed tools and only allowed tools installed
□ Disallowed tools closed and notifications muted
□ Notes scratchpad ready (paper is usually allowed; some platforms prohibit it)
□ Calendar cleared for the duration plus 30 minutes
□ Recruiter contact saved in case the platform fails
```

If you cannot check any of these, that is the item to fix first.

## Step 3: prepare for the actual format

A common mistake is to prepare for "an interview" when you have been given a specific evaluation mechanism. The moves below are different for each:

- **AI-scored / recorded:** write out your answer first, then record. Read the question twice. Most platforms let you re-record a small number of times; use them, not all on one take.
- **AI-moderated / adaptive:** the system may follow up on something you said in a way you cannot predict. The only robust prep is to know the material — STAR stories, the project on your résumé, your two-minute summary. See [Behavioral interviews](../behavioral-interviews/).
- **AI coding environment, AI allowed:** use the allowed tool deliberately — to check edge cases, look up APIs, and explore alternatives — but write the first draft unassisted, because the platform can usually tell.
- **AI coding environment, AI prohibited:** close the tabs. The platform often records browser activity; a disallowed tab open during the assessment is a misrepresentation.
- **Take-home / work sample:** read the brief end to end before starting. Read the allowed-resources list twice. Match the deliverable to the format the employer asked for (PDF, repo, recording).
- **Human-led:** the rules of [Behavioral interviews](../behavioral-interviews/) and [Coding interviews](../coding-interviews/) still apply.

## How to answer when the AI interviewer asks an unexpected follow-up

Treat the follow-up as the question it is. Do not pivot to a prepared answer; the system may be scoring whether you can answer what was actually asked.

- Restate the follow-up out loud in your own words.
- Name what you do know that is close.
- Reason from there. See [How to handle an interview question you don't know](../how-to-handle-an-interview-question-you-dont-know/).
- If the prompt is ambiguous, say so: "I want to make sure I'm answering the right question — are you asking X or Y?"

## How to explain reasoning when the AI keeps probing

The platform is usually testing whether you can sustain a coherent thread of thought across turns. Keep one explicit thread:

- Start each answer with one sentence that names the prior answer's point you are extending.
- Use the same vocabulary across turns; do not rename the same thing.
- State your assumption before you reason from it.
- End with what you would do if the assumption were wrong.

## How to recover from a misunderstood AI question

If the platform asks something that does not match what you thought the question was, do not pretend. The recovery move is to ask once:

> "I want to make sure I understand — are you asking [X] or [Y]?"

If the system does not clarify, name your interpretation and answer that. Then in the debrief (below), note that the prompt was unclear.

## How to handle ambiguous prompts

Ambiguity is a feature of some AI interviews: the system is testing how you decide. Name the ambiguity, then commit to one interpretation and answer it. Do not stall.

## Adaptive interviews

Some platforms change the difficulty of the next question based on how you did. The only useful prep is to keep your pace consistent. Trying to "dumb down" so the questions stay easy backfires in most systems; trying to bluff and getting reset wastes time. Solve the question you have, then take the next one.

## What to do when the platform behaves unexpectedly

- Browser freeze or crash: reload, re-enter if the platform allows, otherwise email the recruiter immediately.
- Question does not load: take a screenshot, do not guess at the missing part, contact the recruiter.
- Audio or video fails: most have a phone-in number; use it rather than quitting.
- A tool you are allowed to use does not work: document the issue and continue; ask for a retake only when a workaround exists.

## How to practice with AI without becoming dependent

AI is a useful practice partner if you keep two rules:

- Use the model the way you would use a peer who can read your code, not the way you would use a calculator. Ask it to challenge your reasoning, not to write it for you.
- Practice the parts you can fail at. A rep with the model where you succeed does not train the muscle that fails on the day. See [How to handle an interview question you don't know](../how-to-handle-an-interview-question-you-dont-know/) for the moves you should be able to do without help.

## Post-interview debrief

Within an hour of finishing, write down:

- The platform and format.
- The questions you were asked, in your own words.
- What you would answer differently, and why.
- Whether you complied with the rules (no disallowed tabs, no AI where prohibited, no paper where prohibited).
- Whether the platform behaved as advertised.

The format and rules tell you what to prepare for next time. The questions tell you what to study. The behavior tells you whether to take the platform seriously.

## The line

The line is the same as [AI-assisted applications: what not to automate](../ai-applications-what-not-to-automate/): you can defend every claim and every action in the interview. If a tool helped you in a way the assessment prohibited, you cannot. If you used only the tools the assessment allowed, you can. The first is dangerous; the second is fine.
