---
title: System design for new grads
description: What a system design conversation at entry level actually covers, and the small set of concepts worth knowing.
updated: 2026-09-30
section: Interviews
order: 5
---

System-design expectations vary by employer and role. Confirm whether your loop includes a design round and how deep it goes. This guide provides a starting method for an entry-level conversation.

## What is being judged

At entry level, the interviewer wants to see whether you can reason about a system larger than a function: identify the parts, say how they talk to each other, and understand where it gets slow or breaks. You may need domain knowledge as well as reasoning. They expect you to ask questions, make reasonable choices and explain trade-offs.

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
- Load balancing and the trade-offs of storing session state on individual servers
- Replication for reads and for failure; the difference between consistent and eventually consistent
- Sharding and the operational complexity it introduces
- Idempotency: why the same request twice must not charge twice
- Rate limiting and time-outs, as protection for the system and for its callers
- Where logging and metrics go, and what you would alert on

You do not need to know products. "A cache" is a fine answer; naming a specific one without knowing how it behaves is not.

## Talking about your own projects

The most likely version of this interview for a new grad is a deep dive into a project on your résumé: draw it, explain the choices, say what broke and what you would change. Prepare that for every project you list; see [New grad projects](../new-grad-projects/).

## Preparation

The maintainer's [System Design course](https://course-system-design.riteshrana.engineer/) covers foundations such as DNS and databases, then works through designs including video platforms and payments. Choose topics that match your interview scope, sketch your own design before reading the lesson, and explain the trade-offs out loud. Treat the course as a study resource; the employer's instructions determine what your interview covers.

For the concepts above, two free, open-source courses by this board's maintainer cover exactly this ground with runnable code: the [Computer Science course](https://course-computer-science.riteshrana.engineer/) builds databases, B-trees, TCP state machines and Raft consensus from first principles in its later phases, and the [Computer Networks course](https://course-computer-networks.riteshrana.engineer/) traces packets through IP, TCP, DNS and HTTP and works through real failure modes. Take the phases you need and stop there. Then practice the method above on ordinary products you use: a URL shortener, a photo feed, a chat app, a job board. Twenty minutes each, out loud, drawing as you go. Use mock feedback to decide whether you need more design practice or time on [coding interviews](../coding-interviews/).
