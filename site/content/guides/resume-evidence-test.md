---
title: The résumé evidence test
description: A repeatable test for every line on your résumé: can you prove the claim, can you explain the mechanism, can you reproduce the result? The same test catches AI-inflated metrics.
updated: 2026-09-30
section: Résumé and applications
order: 5
---

A résumé metric needs an explanation of how it was measured. The claim "reduced latency by 40%" looks impressive on paper and turns into a liability the moment the interviewer asks how it was measured. This guide is that test, in three questions, with a worksheet you can run on every bullet.

::: evidence practical
If you cannot answer "how do you know?" for a metric on your résumé, the bullet is doing you harm. Either replace the metric with a different one you can defend or describe the change without a number.
:::

## The three questions

For every bullet on your résumé, ask these three in order. If any answer is "no" or "I don't know", the bullet is too strong. Rewrite or remove it.

### 1. Can you prove it?

"Prove it" means: is there a reliable record or explanation that supports the claim?

- A benchmark result, a graph, a benchmark output.
- A ticket, a pull request, a commit log.
- A dashboard, a metric, an alert.
- A test, a benchmark suite, a profiler output.
- A user survey, a usage log, a quote from a teammate.
- A project history, a changelog, a release note.

If the only evidence is your memory of "it felt faster", you cannot prove it. Do not invent measurements. A truthful qualitative description may be more appropriate.

### 2. Can you explain it?

"Explain it" means: can you describe the mechanism by hand, without notes, in plain language?

- What was the original latency, the original behaviour, the original number?
- What changed? Which file, which service, which decision?
- How did you measure the change? What was the methodology?
- What trade-offs existed? What did you give up?
- What would you do differently now?

If the honest answer to any of these is "I'm not sure", the bullet is too strong. You can rewrite it (replace the metric with a description), or you can do the work to be able to explain it (re-read the code, re-run the benchmark, talk to a teammate).

### 3. Can you reproduce it?

"Reproduce it" means: if the interviewer asks "could you do it again, on a different system", what is your answer?

- "Yes, here's the approach." — strong.
- "It was a one-off, but here's what I learned." — acceptable if you are honest.
- "No, the conditions were specific." — explain those limits. A truthful past achievement does not promise the same result in every future setting.

The third question catches the silent inflation. Distinguish your contribution from team work and conditions you cannot recreate. Do not claim independent expertise that the experience did not establish.

## The worksheet

Print this, fill it in, keep it next to your résumé.

| Claim | Prove it (artefact) | Explain it (mechanism) | Reproduce it (could you do it again?) |
|---|---|---|---|
| Reduced latency by 40% | Profiler output, dated | Replaced repeated reads with one batched query | Yes, on a similar system |
| Led a team of 4 to ship X | PR list, retros | Held weekly syncs; here's what changed | Yes |
| Built Y used by Z users | Logs, testimonials | React frontend on S3; Flask API on a server | Yes |
| Won the hackathon | Submission, photos | Built a working demo in 36 hours | Different constraints, different result |
| Improved test coverage from 40% to 80% | Coverage report | Wrote unit tests for the X module first | Yes |

The shape of the worksheet matters more than its length. One row per bullet. One column per question. Use the worksheet to identify unsupported claims or limits to explain. These rows are illustrative examples, not achievements to copy. Never disclose confidential records, customer data or private colleague information as proof.

## Where AI helps, where AI hurts

The test interacts with AI use in two ways.

- **AI helps you write the bullet.** A model can rephrase "built a thing" into "built a thing that did X for Y people" if you give it the facts. The fact comes from you.
- **AI hurts you when it invents the metric.** A model may invent a number you did not provide. If you cannot defend the number it chose, the bullet is doing you harm.

Run the test on every AI-edited bullet. The [AI Job Search Framework](../ai-job-search-framework/) section B has the matching guidance on factuality verification and hallucination detection.

::: evidence practical
An unsupported metric can undermine credibility. A defensible claim with no number beats an indefensible claim with one. "Reduced dashboard load from N seconds to M" is better than "improved performance by 40%" if the second number was guessed.
:::

## When "no metric" is the right answer

Not every bullet has a number. That is fine. The bullet should still survive the test. Here is a bullet that passes the test without a metric.

> **Owned onboarding for the campus ambassador program.** Designed the application form, coordinated interviews and documented selection decisions with the committee.

- Prove it: the application form, the interview notes, the process records, where sharing is permitted.
- Explain it: what the role needed, what you looked for, how the loop worked.
- Reproduce it: yes, with adjustments.

The bullet works because it is concrete, named and bounded. "Owned onboarding" without specifics would fail.

## Common patterns that fail the test

These are the patterns to rewrite or remove.

- **Percentages without a baseline.** "Improved X by 30%" — improved from what? The baseline is the proof.
- **Words without artefacts.** "Spearheaded", "championed", "led initiatives" — what specifically did you do?
- **Comparisons to imaginary versions.** "Built a more efficient system" — efficient than what?
- **Verbs that hide the work.** "Helped", "assisted", "was responsible for", "participated in". Replace with what you actually did.

## How to use the test

- **Before you apply.** Run the test on every bullet. Rewrite the ones that fail.
- **Before an interview.** Re-run the test on the bullets most likely to come up. Rehearse the answers out loud.
- **After an interview.** Note any bullet the interviewer questioned. Rewrite it for next time.

## Related guides

- [Résumé bullet points that get read](../resume-bullet-points/) — the format and the rewrite examples.
- [An ATS-friendly résumé](../ats-friendly-resume/) — formatting that does not get in the way.
- [Tailoring your résumé](../tailoring-your-resume/) — how to vary the bullets without inflating them.
- [The AI Job Search Framework](../ai-job-search-framework/) — section B on AI for résumé work.
