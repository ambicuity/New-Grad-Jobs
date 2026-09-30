---
title: LeetCode roadmap for new grads
description: The patterns to learn, in the order to learn them, and the ones that are not worth your time.
updated: 2026-09-30
section: Technical preparation
order: 1
---

LeetCode-style practice is the right preparation for interviews that test algorithmic problem solving under time pressure, and it is one of several preparation paths. Some loops use it; others use take-homes, domain cases, work samples, or system design conversations instead. Follow the format the employer gave you. See [AI-assisted interviews](../ai-assisted-interviews/) for how to read the invitation and identify the actual evaluation, and [The new grad interview process](../interview-process/) for where this fits in the loop.

For data engineers and analysts, also see [SQL interview preparation](../sql-interview-preparation/). For ML/AI roles, see [ML/AI interview preparation](../ml-ai-interview-preparation/). For backend or platform roles, see [Systems interview preparation](../systems-interview-preparation/). For roles that emphasize debugging or reading unfamiliar code, see [Debugging interview preparation](../debugging-interview-preparation/).

Where LeetCode is the right prep, most new-grad coding interviews test the same fifteen to twenty patterns, not the same three hundred problems. A new-grad roadmap covers those patterns, plus the language-specific gotchas you will trip on. Anything beyond that is research, not interview prep.

## Phase 1: arrays, hash maps, strings (2–3 weeks)

The most-tested patterns, and the easiest to learn deeply.

- Two pointers (left/right, slow/fast)
- Sliding window (fixed and variable size)
- Hash map lookups for complement / count / seen
- Prefix sums for range queries
- Sorting plus linear pass for the simple cases

Goal: solve any easy or medium problem in these categories in under twenty-five minutes.

## Phase 2: trees and graphs (2–3 weeks)

- Binary tree traversals: BFS for level order, DFS for path and depth
- Recursion on trees with a clear base case
- Graph BFS and DFS on an adjacency list
- Topological sort and the dependency question it answers

Goal: pick the right traversal without thinking. Most tree and graph problems on new-grad loops come from this set.

## Phase 3: linked lists, stacks, queues, heaps (1 week)

- Reverse a linked list (interviewers ask this to test pointer discipline)
- Stack for "next greater" and bracket problems
- Heap for the "k-th largest" question

Goal: hand-implement the basic operations on each.

## Phase 4: dynamic programming and backtracking (2–3 weeks, only if you have time)

Most new-grad loops have at most one DP question, and it is usually a small one. If your loop is in three weeks, focus on:

- The classic 1D DP (climbing stairs, house robber)
- The classic 2D DP (grid paths, longest common subsequence)
- Backtracking on subsets or permutations

If your loop is sooner, skip this phase entirely and come back if you bomb a DP question on a mock.

## What to skip

- Hard problems past the top 200. You will not see one.
- Bit manipulation beyond AND / OR / XOR / shift. Same reason.
- Segment trees, red-black trees, union-find. Not at new grad level.

## How to study

1. Pick one pattern. Read the standard solution and write down the shape of it in two sentences.
2. Solve three new problems in that shape without looking. If you cannot, you have not learned the pattern; try another.
3. Spaced repetition: solve one problem per pattern every week for the rest of the prep.

Quality of reps beats volume. Sixty problems out of six patterns beats three hundred problems out of fifty.

## Pacing

For a three-month search, three problems a day, four days a week, with one day off a week, lands you around the patterns above. For a one-month prep, drop the DP phase and accept that graph problems will take longer. Read [How to prepare for an interview in 7 days](../how-to-prepare-for-an-interview-in-7-days/) for the final-week schedule.
