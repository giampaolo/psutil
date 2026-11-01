# Contributing to psutil project

## AI policy

- psutil does not accept pull requests or issues which are written by an AI
  agent without any human mediation. You must review the code you submit,
  **write the PR or issue text in your own words**, and post it yourself.
- **No AI in comments.** Comments on issues and PRs must be written by you, not
  by an AI tool.
- Purely AI-generated contributions are closed without review, and accounts
  that keep sending them are blocked.
- **Don't open a PR for an issue opened by someone else**, unless `giampaolo`
  asked for one on that issue. These PRs are closed. This rule is mostly there
  to stop AI slop. If you want to fix it, say so on the issue.
- If an AI agent helps you, it must follow [AGENTS.md](AGENTS.md).

## Issues

- The issue tracker is for reporting problems or proposing enhancements related
  to the **program code**.
- Please do not open issues **asking for support**. Instead, use the forum at:
  https://groups.google.com/g/psutil.
- Before submitting a new issue, **search** if there are existing issues for
  the same topic.
- **Be clear** in describing what the problem is, and fill in the default issue
  **template**. There is a bot which reads the title and description and
  assigns **labels** automatically. Labels help keeping the issues properly
  organized and searchable (by OS, issue type, etc.).
- When reporting a malfunction, consider enabling
  [debug mode](https://psutil.io/devguide/#debug-mode) first.
- To report a **security vulnerability**, use the
  [Tidelift security contact](https://tidelift.com/security). Tidelift will
  coordinate the fix and the disclosure of the reported problem.

## Pull Requests

- If you wish to implement a new feature it's mandatory to **discuss it first**
  on the issue tracker.
- In order to get acquainted with the code base and tooling, take a look at the
  **[Development Guide](https://psutil.io/devguide/)**.
- The PR system is for fixing bugs or make enhancements related to the
  **program code**.
- No need to touch the changelog or credits files. A bot automatically adds
  those entries for you before merging.
