# 🧊 Succession Plan (The "ICE" Protocol)

In the event of an emergency (In Case of Emergency) where the Benevolent Dictator For Life (BDFL) or the primary core maintainer is permanently unreachable, this repository must gracefully transition to the community.

This document authorizes the community to execute the succession process.

## 🚨 Triggers for Succession
The succession protocol is automatically authorized if:
1. The `main` branch has received **0 commits** for 6 consecutive months.
2. The GitHub Actions workflows have been disabled by GitHub due to quota exhaustion, and no fix has been pushed.
3. Over 50 valid Pull Requests sit unreviewed for 3 months.

## 👑 The Handoff Process

If the triggers are met, any established contributor (someone with at least 5 previously merged PRs) is authorized to:
1. **Fork the Repository**: Create a definitive community fork (e.g., `New-Grad-Jobs-Community`).
2. **Update the `README.md`**: In the parent repository (if write access is somehow available) or heavily advertise in the Issue Tracker that the official continuation of the project is at the new fork.
3. **Elect a Steering Committee**: The BDFL model is immediately suspended. The top 3 most active contributors in the new fork must form a temporary Steering Committee.
4. **Disable Actions on the Parent**: If anyone has repository admin access, immediately disable the GitHub Actions cron jobs on this original repository to prevent rate-limit bans against the target APIs from an unmonitored script.

## 🗝️ System Access
Because the system uses an [Infrastructure Map](Infrastructure-Map) completely confined to GitHub (no AWS accounts, no external PostgreSQL databases), **you do not need the maintainer's passwords to continue the project.**

A fresh fork inherits the entire infrastructure out of the box. You simply need to enable GitHub Actions and GitHub Pages on the new repository fork to turn the lights back on.
