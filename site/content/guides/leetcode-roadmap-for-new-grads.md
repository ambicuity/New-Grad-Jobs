---
title: LeetCode roadmap for new grads
description: The patterns to learn, in the order to learn them, and the ones that are not worth your time.
updated: 2026-09-30
section: Technical preparation
order: 1
---

LeetCode-style practice is the right preparation for interviews that test algorithmic problem solving under time pressure, and it is one of several preparation paths. Some loops use it; others use take-homes, domain cases, work samples, or system design conversations instead. Follow the format the employer gave you. See [AI-assisted interviews](../ai-assisted-interviews/) for how to read the invitation and identify the actual evaluation, and [The new grad interview process](../interview-process/) for where this fits in the loop.

For data engineers and analysts, also see [SQL interview preparation](../sql-interview-preparation/). For ML/AI roles, see [ML/AI interview preparation](../ml-ai-interview-preparation/). For backend or platform roles, see [Systems interview preparation](../systems-interview-preparation/). For roles that emphasize debugging or reading unfamiliar code, see [Debugging interview preparation](../debugging-interview-preparation/).

Where LeetCode is the right prep, begin with recurring data-structure and algorithm patterns, then adapt to the employer's published topics and your mock results. [Amazon's software-development preparation topics](https://amazon.jobs/content/en-gb/how-we-hire/interview-prep/software-development-topics) span algorithms, data structures, design, databases, operating systems, and other fundamentals; ask the recruiter which apply to your role.

## Phase 1: arrays, hash maps, strings (2–3 weeks)

Start with these foundational patterns.

- Two pointers (left/right, slow/fast)
- Sliding window (fixed and variable size)
- Hash map lookups for complement / count / seen
- Prefix sums for range queries
- Sorting plus linear pass for the simple cases

Practice goal: solve representative problems accurately within the time available for your round. Difficulty labels do not guarantee a fixed completion time.

## Phase 2: trees and graphs (2–3 weeks)

- Binary tree traversals: BFS for level order, DFS for path and depth
- Recursion on trees with a clear base case
- Graph BFS and DFS on an adjacency list
- Topological sort and the dependency question it answers

Goal: choose and explain an appropriate traversal. Add weighted shortest paths or union-find if the employer's topics or practice gaps call for them.

## Phase 3: linked lists, stacks, queues, heaps (1 week)

- Reverse a linked list (interviewers ask this to test pointer discipline)
- Stack for "next greater" and bracket problems
- Heap for the "k-th largest" question

Goal: hand-implement the basic operations on each.

## Phase 4: dynamic programming and backtracking (2–3 weeks, only if you have time)

Dynamic programming requirements vary. If your preparation time is short, begin with:

- The classic 1D DP (climbing stairs, house robber)
- The classic 2D DP (grid paths, longest common subsequence)
- Backtracking on subsets or permutations

If your loop is sooner, use the employer's guidance and a mock to decide which gaps to prioritize.

## What to deprioritize

Advanced structures and specialized bit tricks may be lower priorities when time is limited, unless the role or employer names them. No public problem list guarantees what you will see. Learn binary search and interval problems alongside the phases above; cover union-find when connectivity problems are relevant.

## How to study

1. Pick one pattern. Read the standard solution and write down the shape of it in two sentences.
2. Solve three new problems in that shape without looking. If you cannot, you have not learned the pattern; try another.
3. Spaced repetition: solve one problem per pattern every week for the rest of the prep.

Quality of reps beats volume. Sixty problems out of six patterns beats three hundred problems out of fifty.

## Pacing

For a three-month search, three problems a day, four days a week, with one day off a week, lands you around the patterns above. For a one-month plan, use an initial mock and the role requirements to reduce scope. Read [How to prepare for an interview in 7 days](../how-to-prepare-for-an-interview-in-7-days/) for the final-week schedule.
