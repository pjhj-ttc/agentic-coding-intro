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
