# Contributing Guide

Thank you for your interest in contributing to this project. This document describes the process and conventions for collaborating effectively.

## Table of Contents

- [Development Environment Setup](#development-environment-setup)
- [Git Workflow](#git-workflow)
- [Branch Naming](#branch-naming)
- [Commit Conventions](#commit-conventions)
- [Code Style](#code-style)
- [Reporting a Bug](#reporting-a-bug)
- [Proposing an Enhancement](#proposing-an-enhancement)
- [Pull Requests](#pull-requests)

---

## Development Environment Setup

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) for dependency management
- AWS CLI configured with valid credentials
- Access to the following services: S3, Lambda, Glue, Bedrock, RDS, Step Functions

### Scraper setup

```bash
cd src/scraper
uv venv
uv sync
```

### Required environment variables

For local testing, set the following variables:

```bash
export AWS_DEFAULT_REGION=us-east-2
export BUCKET=s3://your-test-bucket
export MODEL_ID=amazon.nova-lite-v1:0
```

For the Glue jobs (`silver-to-gold.py`), update the RDS credentials directly in the script or, preferably, store them in AWS Secrets Manager.

---

## Git Workflow

1. **Fork** the repository (external contributors) or create a branch directly (team members).
2. Create a branch from `main` following the naming convention below.
3. Make atomic, descriptive commits.
4. Open a Pull Request targeting `main` when the branch is ready.

---

## Branch Naming

| Prefix | Use | Example |
|--------|-----|---------|
| `feature/` | New functionality | `feature/silver-to-gold-v2` |
| `fix/` | Bug fixes | `fix/scraper-retry-logic` |
| `docs/` | Documentation-only changes | `docs/update-etl-readme` |
| `refactor/` | Refactoring without behavior change | `refactor/bedrock-client` |
| `chore/` | Maintenance tasks (dependencies, CI) | `chore/update-uv-lockfile` |

---

## Commit Conventions

Use the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <short imperative description>
```

**Valid types:**

| Type | When to use |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `refactor` | Code refactoring |
| `test` | Adding or fixing tests |
| `chore` | Maintenance (dependencies, lockfiles) |

**Examples:**

```
feat(scraper): add publication date extraction
fix(bronze-to-silver): handle empty reviews gracefully
docs(etl-jobs): update Glue deployment instructions
chore(scraper): update uv.lock with latest versions
```

---

## Code Style

- **Python**: follow [PEP 8](https://peps.python.org/pep-0008/). You can check compliance with `ruff check` if available.
- **SQL**: use uppercase for reserved keywords (`SELECT`, `FROM`, `WHERE`).
- **PySpark (Glue jobs)**: prefer DataFrame transformations over inline SQL where possible to simplify testing.
- **Comments**: only when the *why* is non-obvious. Do not describe what the code does — describe the reason behind a non-evident decision.
- **Credentials**: never hardcode credentials or endpoints. Use environment variables or AWS Secrets Manager.

---

## Reporting a Bug

1. Open an [Issue](https://github.com/SolisAlexis24/data-engineering-popular-books-tracker/issues) with the `bug` label.
2. Include:
   - Expected vs. observed behavior
   - Steps to reproduce
   - Relevant logs (CloudWatch, Glue, Lambda)
   - AWS region and service version affected (if applicable)

---

## Proposing an Enhancement

1. Open an [Issue](https://github.com/SolisAlexis24/data-engineering-popular-books-tracker/issues) with the `enhancement` label.
2. Describe the problem it solves and the expected impact.
3. If it involves changes to the AWS architecture, include a diagram or description of the proposed flow.

---

## Pull Requests

- PRs must target the `main` branch.
- The PR title must follow the same format as commits (`feat:`, `fix:`, etc.).
- Include in the description:
  - What changes and why
  - How to test it (Glue commands, Lambda invocations, etc.)
  - Screenshots or logs if the change affects pipeline output
- At least one reviewer must approve before merging.
- Do not force-push to `main` or merge without review.

---

## Notes on AWS Services

- **Bedrock**: the `amazon.nova-lite-v1:0` model must have access enabled in the Bedrock console before running the Glue jobs.
- **Glue**: test jobs locally or with `aws glue start-job-run` before integrating them into the Step Function.
- **Costs**: Glue jobs and Bedrock calls incur charges. Use small datasets during development and monitor usage with AWS Cost Explorer.
- **Scraper**: respect Goodreads' Terms of Service. Do not increase the scraping frequency beyond the established weekly execution.
