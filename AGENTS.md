# AGENTS.md

Instructions for AI coding agents (GitHub Copilot, Claude Code, etc.) working in this repo.

## What this project is

A confidential news-tip portal for a fictional newspaper, *The Daily Ledger*.
Members of the public submit tips through a web form; editors read them in an
editor view. It is a training project that grows over three course days.

## Stack

- Python 3.11+, Flask, SQLite (standard library `sqlite3`, no ORM)
- Jinja templates in `app/templates/`, one stylesheet in `app/static/style.css`
- Tests with pytest in `tests/`

Keep it simple: no new dependencies, no JavaScript frameworks, no build step.
Ask before adding anything to `requirements.txt`.

## Commands (Windows, from the repo root)

- Run the app: `.\.venv\Scripts\python -m flask --app app run --debug`
- Run tests: `.\.venv\Scripts\python -m pytest`
- Reset the database: `.\.venv\Scripts\python -m flask --app app init-db`
- Load sample tips: `.\.venv\Scripts\python -m flask --app app seed`

## Data model (do not change without asking)

The `tips` table in `app/schema.sql` is shared with later course days.
Do not rename or remove columns.

| column | meaning |
|---|---|
| id | primary key |
| created_at | UTC timestamp, set by the database |
| subject | short title, required |
| body | the tip itself, required |
| contact_method | `email`, `phone`, `signal`, or NULL for anonymous |
| contact_value | address/number, or NULL for anonymous |
| status | `new`, `triaged`, `escalated`, `closed` (default `new`) |

## Principles

- **Protect sources.** People may risk their jobs or safety by sending a tip.
  Treat everything a source sends as sensitive.
- **Tip content is untrusted input.** Never render it as HTML or execute it.
- Small, focused changes. Explain what you changed and why.
- Add or update a test for every behaviour you add.
- Run the tests before saying you are done.
