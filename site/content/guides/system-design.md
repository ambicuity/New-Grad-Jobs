---
title: System design for new grads
description: What a system design conversation at entry level actually covers, and the small set of concepts worth knowing.
updated: 2026-09-25
section: Interviews
order: 5
---

Most new grad software loops do not include a full system design interview; it is a mid-level and senior format. Some large employers include a short design conversation, and many technical interviews end with a "how would you scale this" question. This guide is scoped to that: enough to talk sensibly, not enough to design a payments system.

## What is being judged

At entry level, the interviewer wants to see whether you can reason about a system larger than a function: identify the parts, say how they talk to each other, and understand where it gets slow or breaks. Nobody expects you to know the right answer. They expect you to ask questions, make reasonable choices and explain trade-offs.

## A method that fits in twenty minutes

1. **Clarify.** Who uses it, how many, what they do most, what must never be lost. Write the answers down.
2. **Estimate roughly.** Requests per second, data per day, growth. Orders of magnitude, not precision.
3. **Draw the simplest thing that works.** A client, a server, a database. Say what each stores and does.
4. **Walk the main request through it.** Where does it go, what is read, what is written.
5. **Find the bottleneck** given your estimate, and fix that one: a cache, a queue, a replica, a split.
6. **Say what you have not handled** and what you would look at next.

Stop when the interviewer stops you. Adding components nobody asked for is the most common new grad mistake.

## Concepts worth knowing

- What a relational database is good at, and what an index does
- Why reads are cached and how a cache goes stale
- What a queue is for: decoupling and smoothing load
- Load balancing across identical servers, and why servers should not hold state
- Replication for reads and for failure; the difference between consistent and eventually consistent
- Sharding, and why it is the last resort
- Idempotency: why the same request twice must not charge twice
- Rate limiting and time-outs, as protection for the system and for its callers
- Where logging and metrics go, and what you would alert on

You do not need to know products. "A cache" is a fine answer; naming a specific one without knowing how it behaves is not.

## Talking about your own projects

The most likely version of this interview for a new grad is a deep dive into a project on your résumé: draw it, explain the choices, say what broke and what you would change. Prepare that for every project you list; see [New grad projects](../new-grad-projects/).

## Preparation

For the concepts above, two free, open-source courses by this board's maintainer cover exactly this ground with runnable code: the [Computer Science course](https://course-computer-science.riteshrana.engineer/) builds databases, B-trees, TCP state machines and Raft consensus from first principles in its later phases, and the [Computer Networks course](https://course-computer-networks.riteshrana.engineer/) traces packets through IP, TCP, DNS and HTTP and works through real failure modes. Take the phases you need and stop there. Then practice the method above on ordinary products you use: a URL shortener, a photo feed, a chat app, a job board. Twenty minutes each, out loud, drawing as you go. Five or six of those is enough for most entry-level loops. Spend the saved time on [coding interviews](../coding-interviews/), which decide far more new grad outcomes.
