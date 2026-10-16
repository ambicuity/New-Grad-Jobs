---
title: Open source contributions for new grads
description: Choose a project, read its contribution rules, pick a first issue, make a small useful change and describe it honestly on your résumé.
updated: 2026-10-15
published: 2026-10-15
section: GitHub and portfolio
order: 4
format: checklist
use_when: Read this when you want to contribute to an open source project for the first time and present the work honestly to employers.
you_get: You get how to choose a project, what to read first, how to find and claim an issue, a contribution checklist and résumé wording.
---

A merged change to someone else's project shows things a solo project cannot: that you can read unfamiliar code or documents, follow a project's conventions and respond to review. It is one kind of evidence, not a requirement for a first job. This guide covers making a first contribution and describing it accurately. For presenting your own repositories, see [GitHub profile for new grads](../github-profile-for-new-grads/) and [What makes a GitHub repository impressive?](../what-makes-a-github-repo-impressive/)

## Choose a project

Start with something you already use: a library from a class project, a data tool, a documentation site, a plugin for software in your field. You will understand the problem, and you are more likely to keep going.

Then check whether the project is active enough for a newcomer.

- **License.** Look for a LICENSE file. Open Source Guides notes that [if a project does not have a license, it is not open source](https://opensource.guide/how-to-contribute/).
- **Recent activity.** Look at recent commits on the main branch and how many people are contributing.
- **Responsive maintainers.** Check whether issues get replies, whether pull requests are reviewed, and when one was last merged.
- **A welcoming setup.** A CONTRIBUTING file, a code of conduct and labelled beginner issues suggest the maintainers expect new contributors.

A large, famous project is not better for a first contribution. A smaller, active project where a maintainer will review your change can teach you more.

## Read the rules before you start

Every project works a little differently. Read these in order:

1. **README:** what the project does and how to install it.
2. **CONTRIBUTING:** how to set up a development environment, run tests, format commits and open a pull request. GitHub lets maintainers place it [in the repository root, `docs` or `.github` folder](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/setting-guidelines-for-repository-contributors), and links to it when you open an issue or pull request.
3. **Code of conduct:** the behaviour expected in issues, reviews and chat. Follow it in every exchange.
4. **Issue and pull request templates:** fill them in fully.
5. **Any contributor agreement.** Some projects ask you to sign a contributor licence agreement or add a sign-off line to commits. Read what you are agreeing to before you sign.

If you are employed or have an internship, check whether your employment agreement covers work you do outside your job. See [Reading your employment agreement](../reading-your-employment-agreement/).

## Find a first issue

::: evidence official
GitHub's documentation explains that maintainers can apply the [`good first issue` label](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/encouraging-helpful-contributions-to-your-project-with-labels) to issues in public repositories, and that the label can increase the likelihood those issues are surfaced to new contributors. Open Source Guides suggests adding `/contribute` to a repository's URL on GitHub to see its beginner-friendly issues.
:::

Good first contributions are often not code:

- Fixing an unclear or outdated step in the documentation you hit while installing.
- Reproducing a reported bug and adding the exact steps and versions to the issue.
- Adding a missing test for existing behaviour.
- Improving an error message, a translation or an example.

Open Source Guides makes the same point: [you do not need to contribute code](https://opensource.guide/how-to-contribute/), and documentation, design and organisation are often the most neglected parts of a project.

## Claim it, then ask before big changes

- Comment on the issue before starting, so nobody duplicates the work. Say what you plan to do in a sentence.
- For a typo or a broken link, a pull request on its own is usually fine.
- For anything larger, open or comment on an issue first and ask whether the maintainers want the change. Open Source Guides advises asking before working on a substantial contribution.
- Keep discussion in the public issue rather than private messages, unless it is a security report the project asks you to send privately.

## Make the contribution

A checklist for the pull request:

1. Fork the repository and create a branch for one change.
2. Set up the project exactly as CONTRIBUTING describes, and run the existing tests before you change anything.
3. Make the smallest change that resolves the issue. Avoid reformatting unrelated files.
4. Add or update a test or documentation where the project expects it.
5. Write a description that says what changed, why and how you checked it. Link the issue with a keyword such as `Closes #123`; GitHub [closes the linked issue automatically](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue) when the pull request is merged into the default branch.
6. Respond to review politely and promptly. Make the requested changes, or explain clearly if you think something else would work better.

If you used AI tools, check the project's policy on them, review every line yourself and be able to explain it. Your name is on the change.

## If it is not merged

Maintainers decline changes for many reasons: scope, timing or a different plan. You can ask for feedback, but the decision is theirs. If there is no response for a while, one polite follow-up comment is reasonable. Then move on to another issue or project. Do not open duplicate pull requests or tag maintainers repeatedly.

## Describe it honestly on your résumé

Name the project, say what you changed and link the pull request so a reviewer can check it. Use the status that is true.

> **Contributor, [project name]** ([link to pull request]): Fixed [bug] in [component] that caused [effect]; added a regression test. Merged into [version or month, year].

> **Documentation, [project name]**: Rewrote the [platform] installation guide after reproducing [problem]; change reviewed and merged by maintainers.

Rules to keep it accurate:

- Say "contributor", not "maintainer" or "core developer", unless the project gave you that role.
- Say "merged" only for merged changes. An open pull request can be described as "submitted" or "in review".
- Do not count trivial changes, such as whitespace fixes, as major contributions.
- Use numbers only if you can show them, as in [Résumé bullet points that get read](../resume-bullet-points/).

Be ready to explain the change in an interview: what the issue was, how you found your way around the codebase and what the reviewer asked you to change. Contributions also fit naturally in the projects section described in [New grad projects that count](../new-grad-projects/).
