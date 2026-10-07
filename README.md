# Tip Portal

Course repo for **Agentic Coding, Agents & Safeguards**.

Over three sessions you build, automate and harden a confidential news-tip portal
for a fictional newspaper, *The Daily Ledger*:

| Day | Date | What you do |
|---|---|---|
| 1 | Oct 1 | Build the tip submission portal with a coding agent → [setup](exercises/day1-setup.md), then [exercise](exercises/day1-exercise.md) |
| 2 | Oct 7 | Turn it into an autonomous triage agent → [setup](exercises/day2-setup.md), [exercise 1: your AGENTS.md](exercises/day2-exercise1.md), then [exercise 2: the triage agent](exercises/day2-exercise2.md) |
| 3 | Oct 22 | Attack your own agent, then add the guardrails that stop it |

**Read before you start:** [Secure development with Copilot Chat](guides/secure-copilot.md)

You download this project from GitHub once. After that, everything you build stays **on your
laptop**: git runs locally as your save points, and you don't upload anything.

## Setup (10 min)

Follow the step-by-step guide: **[exercises/day1-setup.md](exercises/day1-setup.md)**

The short version, in a VS Code terminal:

```powershell
git clone https://github.com/pjhj-ttc/agentic-coding-intro.git; cd agentic-coding-intro
powershell -ExecutionPolicy Bypass -File .\setup.ps1          # should end with "All good!"
.\.venv\Scripts\python -m flask --app app run --debug         # then open http://127.0.0.1:5000
```

## Working in the repo

Create your own branch so you can always compare with the starting point:

```powershell
git switch -c my-work
```

### Fell behind? Jump to a checkpoint

Each day starts from a known-good checkpoint:

| Branch | Contents |
|---|---|
| `main` | Day 1 starting point, plus the Day 2 exercises and files |
| `day1-solution` | A reference solution for Day 1 (the starting point for Day 2) |
| `day2-solution` | A reference solution for Day 2 (the starting point for Day 3) |

```powershell
git add -A; git commit -m "my work so far"   # keep your own work
git fetch
git switch -c my-day2-work origin/day1-solution
```

At the start of each session, download the new checkpoints (this doesn't touch your own work):

```powershell
git fetch
```

## Data model

The `tips` table in [app/schema.sql](app/schema.sql) is shared across the whole course. Do not
rename or remove columns without asking. If this table and the schema file ever disagree, the
schema file is right.

| column | meaning |
|---|---|
| id | primary key |
| created_at | UTC timestamp, set by the database |
| subject | short title, required |
| body | the tip itself, required |
| contact_method | `email`, `phone`, `signal`, or NULL for anonymous |
| contact_value | address/number, or NULL for anonymous |
| status | `new`, `triaged`, `escalated`, `closed` (default `new`) |

## Routes

| Route | Shows | Who may open it |
|---|---|---|
| `/` | The front page | Anyone |

Add a row here whenever you add a route.

## Project layout

```
app/            Flask app (routes in __init__.py, database in db.py, schema.sql)
app/templates/  HTML pages
data/           sample tips
tests/          pytest tests
exercises/      step-by-step guide for each day
guides/         how to work safely with a coding agent
handouts/       printable PDFs of the setup guide, exercise and safety guide
AGENTS.md       instructions your coding agent reads automatically
```
