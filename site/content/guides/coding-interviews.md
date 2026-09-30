---
title: Coding interviews for new grads
description: How to work a problem out loud, what interviewers are scoring, and a preparation schedule that fits a final year.
updated: 2026-09-30
section: Interviews
order: 3
---

A live coding interview is not a harder online assessment. It is a conversation in which you solve a problem, and both your solution and how you explain it can be evaluated. Many candidates who pass assessments fail interviews because they go silent and code; many who are slower pass because the interviewer could follow them.

## What is scored

- **Understanding.** Did you restate the problem, ask about inputs and edge cases, and confirm before coding?
- **Approach.** Did you propose something, say why, and consider its cost before writing it?
- **Execution.** Is the code correct, readable and organized? Do you trace it with an example?
- **Testing.** Do you check edge cases without being asked?
- **Communication.** Could the interviewer follow your thinking? Did you take hints?

The employer determines the weight of each criterion. Practice correctness, testing, and clear explanation together.

## A working method

1. Restate the problem in your own words. Ask two or three clarifying questions: input size, value ranges, what to return on empty input.
2. Work a small example by hand.
3. Say the obvious approach and its complexity. Ask whether to improve it or code it. Interviewers will tell you.
4. Outline the improved approach in a few lines of comments, then fill in the code.
5. Trace your example through the code, line by line. Fix what you find.
6. Name the edge cases and how the code handles them.
7. State time and space complexity.

Talk throughout, but not constantly. "Let me think for a moment" followed by silence is fine; an unexplained five-minute silence is not.

## Taking hints

A hint is not a failure. Interviewers give them to keep the interview moving and score how you use them. Acknowledge it, think about it, apply it. If you choose a different approach after a hint, explain why and check that you understood the interviewer's constraint. See [How to handle an interview question you don't know](../how-to-handle-an-interview-question-you-dont-know/) for the moves that recover an interview when you are stuck.

## Preparation

The content is the same as [Coding assessments](../coding-assessments/): arrays, strings, hashing, sorting, recursion, basic dynamic programming, trees and graphs. The added skill is doing it out loud. Practice with another person, or alone by speaking to the screen and recording it. Try a few focused sessions each week, then adjust using mock results, your starting knowledge, and the employer's topics. No fixed schedule guarantees readiness. For the patterns to study in order, see the [LeetCode roadmap for new grads](../leetcode-roadmap-for-new-grads/). Not every loop uses LeetCode-style coding; see [AI-assisted interviews](../ai-assisted-interviews/) for the broader format landscape and [Role-specific technical preparation](../role-specific-technical-preparation/) for non-coding tracks.

Know one language well: its standard collections, string handling and sorting API without looking them up. Confirm the supported languages; some roles or platforms require a particular language.

For the fundamentals behind the questions (how a hash map is built, what recursion costs, how a scheduler or an allocator works), the [Computer Science course](https://course-computer-science.riteshrana.engineer/) by this board's maintainer builds those systems from first principles with runnable code. It is free and open source, and its early phases on discrete math and data structures are the part that matters for interviews.

## Language and tooling questions

Expect a few questions about the language you used and about fundamentals: how a hash map works, what recursion costs, what a race condition is, how you would test the code. These are shallow but not optional.

## On the day

Set up the environment ten minutes early. Use paper only if the interview rules permit it. If it is remote, close everything else. If you get stuck, say what you are stuck on; that is a question, and questions get answers. After the interview, record the concepts and what you would improve, while respecting confidentiality restrictions on the questions. A [behavioral interview](../behavioral-interviews/) is often in the same loop; prepare it separately.

Confirm the format and the AI rules before you start. Many live coding platforms now include built-in AI tooling whose allowed/disallowed status is not obvious from the editor. See [AI-assisted interviews](../ai-assisted-interviews/) for how to read the invitation and the platform's tools policy.
