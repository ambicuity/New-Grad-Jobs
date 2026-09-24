# Governance Model

New Grad Jobs operates under a **Benevolent Dictator for Life (BDFL)** model. This model ensures that decision-making remains focused, agile, and aligned with the project's core mission: providing a high-quality, fully automated, and unbiased job board for new graduates.

## Project Leadership

The project is currently led and maintained by **@ambicuity** (Ritesh Rana).

The BDFL is responsible for:
- Defining the strategic direction and roadmap of the project.
- Ensuring the architectural integrity and reliability of the scraper, which refreshes the board about every 30 minutes.
- Reviewing and approving major architectural changes or new feature additions.
- Establishing and enforcing code quality, testing, and security standards.
- Managing community interactions and enforcing the Code of Conduct.

## Decision-Making Process

While the BDFL retains final say on all project matters, New Grad Jobs thrives on community input. Decisions are made transparently through:

1.  **Architecture Proposals:** Significant technical changes should begin as an issue using the `Architecture Proposal` template. This allows the community to discuss the merits, drawbacks, and implementation strategy before code is written.
2.  **Pull Requests:** All code contributions are reviewed via Pull Requests. The BDFL (and any future core maintainers) will review PRs for alignment with the project's goals, code quality, and security standards.
3.  **Discussions:** General ideas, Q&A, and community-driven initiatives are encouraged within GitHub Discussions.

## Pathways to Leadership

As the project scales, the governance model may evolve. Contributors who consistently demonstrate commitment to the project's goals, provide high-quality code and reviews, and adhere to our engineering standards may be invited by the BDFL to join a core maintainer team.

We value:
- **Extreme Ownership:** Taking responsibility for features from proposal to production.
- **Production-Grade Engineering:** Writing clean, testable, and secure code.
- **Community Support:** Helping other contributors and users in issues and discussions.

## Conflict Resolution

Disputes or disagreements regarding technical direction or community conduct will be resolved by the BDFL, prioritizing the long-term health and stability of the project. If you have concerns about the governance process or a specific decision, please open an issue or start a GitHub Discussion to address it constructively.

## Succession (in case of emergency)

If the maintainer becomes permanently unreachable, the community is authorized to continue the project. Succession applies when any of these is true:

1. `main` has received no human commits for 6 consecutive months. Automated `🤖 Update job listings` commits do not count.
2. The scheduled workflows have been disabled (by GitHub or for quota reasons) and no fix has been pushed for 3 months.
3. More than 50 valid pull requests have gone unreviewed for 3 months.

Any established contributor (at least 5 merged PRs) may then:

1. **Fork** the repository as the community continuation, and announce the fork in the issue tracker (and in `README.md`, if anyone still has write access).
2. **Form a steering committee** of the three most active contributors to the fork. It replaces the BDFL model.
3. **Stop the original scraper.** Anyone with admin access should disable the scheduled workflows on this repository, so that no unmonitored scraper keeps hitting the job-board APIs.

No credentials are needed to take over. Every source is a public endpoint and there are no external accounts, databases or secrets. A fork only needs Actions enabled, **Settings → Pages → Source = GitHub Actions**, and `site/public/CNAME` replaced or deleted for its own domain. It should also set `NGJ_SITE_URL` to its own URL: the scraper and the SEO build default to `https://jobs.riteshrana.engineer/`. The rest of the setup is in [docs/operations.md](docs/operations.md).
