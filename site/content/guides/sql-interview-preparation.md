---
title: SQL interview preparation for new grads
description: What data and analytics loops test, the patterns to learn, and the ones that come up most often.
updated: 2026-09-30
section: Technical preparation
order: 2
---

SQL comes up in most data, analytics, backend, and ML new-grad loops. The interview format varies: it may be a live SQL pad, a take-home with a database, a HackerRank-style timed set, or a written question as part of a larger case. The format and role can change the emphasis: query writing, data interpretation, schema design, or performance. Confirm the SQL dialect and whether execution is available. Read [AI-assisted interviews](../ai-assisted-interviews/) for those rules before you sit down.

## What is tested

At new grad level, SQL interviews test four things:

- **Reading and joining.** Multi-table joins, self joins, conditional aggregation, group-by with filters (HAVING).
- **Writing.** CTEs, window functions, subqueries, set operators. Know when a window function preserves detail that a grouped result would remove.
- **Reasoning about data.** Why this query is slow, what the schema implies, what the row count should be, where the null lives.
- **Communication.** Walking the interviewer through your approach before you write the query.

## The patterns that come up most

- **Aggregation:** GROUP BY with COUNT, SUM, AVG; HAVING for post-aggregation filters.
- **Joins:** INNER, LEFT, with non-trivial ON clauses; self joins for "find rows that share an attribute with another row".
- **Window functions:** ROW_NUMBER, RANK, DENSE_RANK, LAG, LEAD, running totals with SUM() OVER.
- **CTEs:** for readability, especially when the query has more than one logical step.
- **Set operations:** UNION, INTERSECT, EXCEPT for the rare question that wants them.
- **NULL handling:** COALESCE, NULL-safe joins, IS NULL on optional foreign keys.
- **Date and time:** filtering on date ranges, extracting parts, the difference between DATE and TIMESTAMP.

## How to prepare

- Pick a sample database (Sakila, Employees, or a public Kaggle set) and answer fifty questions against it without a query generator. The muscle that fails on the day is the one you trained.
- For suitable problems, compare a window-function solution with an alternative. The interview asks for the version you would write in production; you choose which one to deliver.
- Time-box yourself. Twenty minutes per question is generous; ten is closer to a real loop.
- Practice explaining the query as you write it. The interviewer wants to follow your reasoning; the query is the artifact, not the test.

## Additional topics to confirm

- Database administration (indexes, partitions, vacuuming).
- Stored procedures and triggers.
- Vendor-specific extensions (Postgres-only or MySQL-only syntax).
- ORM-specific query construction.

Backend and data-engineering roles can require indexes, query plans, transactions, and dialect-specific behavior even when the role is not database administration. Use the posting and recruiter guidance to choose the depth.

## When to skip LeetCode-style SQL and study this instead

If the loop's take-home or assessment asks you to optimize a slow query, debug a missing row, or model a small schema, the prep shifts toward query plans, EXPLAIN output, and schema design. See [Systems interview preparation](../systems-interview-preparation/) for the overlap.
