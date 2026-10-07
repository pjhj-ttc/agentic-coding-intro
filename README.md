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

The triage agent adds two tables:

`triage`: the agent's assessment, at most one row per tip.

| column | meaning |
|---|---|
| tip_id | the tip (primary key, refers to `tips.id`) |
| created_at | UTC timestamp, set by the database |
| desk | `politics`, `business`, `environment`, `health`, `local`, or `none` (not a news tip) |
| urgency | `high`, `normal`, `low` |
| duplicate_of | id of an earlier tip about the same story, or NULL |
| summary | one sentence for the editor |
| model | the model that made the assessment |

`agent_log`: one row for everything the agent does.

| column | meaning |
|---|---|
| id | primary key |
| created_at | UTC timestamp, set by the database |
| run_id | groups the events of one run of the agent |
| tip_id | the tip being triaged |
| event | `model_call`, `tool_call` or `error` |
| name | the tool, for tool calls and tool errors |
| detail | JSON: tool arguments and result, token usage, or the error message |

## Routes

| Route | Shows | Who may open it |
|---|---|---|
| `/` | The tip form | Anyone |
| `/thanks` | Thank-you page after sending a tip | Anyone |
| `/editor` | All tips, newest first, with the agent's triage and the source's contact details | Editors (there is no login yet: anyone with the address can open it) |
| `/editor/log` | Every run of the triage agent: model calls, tool calls with their results, errors | Editors (no login yet) |

Add a row here whenever you add a route.

## Triage agent

`app/triage.py` reads each new tip, picks a desk and an urgency, looks for earlier tips about
the same story, and writes a one-sentence summary for the editor. It talks to the language model
only through `app/llm.py`.

It reads the model key from `~/.tip-portal/key.txt`, outside the project (see the Day 2 setup).
Run it from the repo root:

| Command | What it does |
|---|---|
| `.\.venv\Scripts\python -m flask --app app triage` | Triages every tip with status `new` |
| `... triage --dry-run` | Prints the results, saves nothing (the run is still logged) |
| `... triage-eval` | Dry run on the sample tips, compared with `data/triage_expected.json` |

The model can call three tools, one conversation per tip:

| Tool | Returns to the model | Can change |
|---|---|---|
| `get_tip(tip_id)` | The whole tip, including the source's contact details | Nothing |
| `search_tips(query)` | Up to 5 earlier tips containing the search words, whole tips including contact details | Nothing |
| `save_triage(tip_id, desk, urgency, duplicate_of, summary)` | The saved result | Writes the `triage` row, and sets the tip's status: `escalated` if urgency is `high`, otherwise `triaged`. Only for the tip being triaged |

Limits:

- At most 10 model calls per tip; then the tip stays `new` and an error is logged.
- `save_triage` rejects an unknown desk or urgency, a `duplicate_of` that isn't an earlier tip, an
  empty summary, or another tip's id. The error goes back to the model to correct.
- Tests use `FakeModel` and never call the real model.
- Escalation happens without an editor's approval.

## Project layout

```
app/            Flask app (routes in __init__.py, database in db.py, schema.sql)
app/triage.py   the triage agent; app/llm.py connects it to the model
                (check the connection with: python -m app.check_model)
app/templates/  HTML pages
data/           sample tips
tests/          pytest tests
exercises/      step-by-step guide for each day
guides/         how to work safely with a coding agent
handouts/       printable PDFs of the setup guide, exercise and safety guide
AGENTS.md       instructions your coding agent reads automatically
```
