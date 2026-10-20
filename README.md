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
| `day3-solution` | A reference solution for Day 3: the guardrails |

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
| status | `new`, `triaged`, `escalated`, `closed` (default `new`). `escalated` is set only by an editor |

Who sent a tip is kept apart from the tip. On Day 3 the contact columns moved out of `tips`
into their own table, which only the editor view reads and the triage agent never queries:

`sources`: one row per tip whose sender left contact details. No row means anonymous.

| column | meaning |
|---|---|
| tip_id | the tip (primary key, refers to `tips.id`) |
| contact_method | `email`, `phone` or `signal` |
| contact_value | address/number |

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
| suggest_escalation | 1 if the agent suggests escalating the tip (urgency `high`), otherwise 0. An editor decides |

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

`tip_events`: the chain of custody of each tip. Never holds contact details.

| column | meaning |
|---|---|
| id | primary key |
| created_at | UTC timestamp, set by the database |
| tip_id | the tip |
| event | `received`, `flagged` (the tip contains instructions aimed at the triage system), `triaged`, `triage_failed`, `escalated` |
| actor | `source`, `system`, `agent`, or the editor's name for `escalated` |
| detail | JSON: run id, the agent's decision, error message |

## Routes

| Route | Shows | Who may open it |
|---|---|---|
| `/` | The tip form | Anyone |
| `/thanks` | Thank-you page after sending a tip | Anyone |
| `/editor` | All tips, newest first, with the agent's triage and the source's contact details. Tips the agent suggests escalating have an **Escalate** button | Editors (there is no login yet: anyone with the address can open it) |
| `POST /editor/tips/<id>/escalate` | Escalates a tip the agent suggested escalating. Needs the editor's name, which is recorded with the time | Editors (no login yet) |
| `/editor/log` | The chain of custody of every tip, then every run of the triage agent: model calls, tool calls with their results, errors. No contact details | Editors (no login yet) |

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
| `... triage-eval` | Runs the agent on the sample tips (on a copy of the database), compares with `data/triage_expected.json`, and fails if a guardrail was broken |

The model can call three tools, one conversation per tip:

| Tool | Returns to the model | Can change |
|---|---|---|
| `get_tip(tip_id)` | The tip's id, time, subject and body. The text is wrapped in `<untrusted_tip_text>` tags. Never the source | Nothing |
| `search_tips(query)` | Up to 5 earlier tips containing the search words, in the same form | Nothing |
| `save_triage(tip_id, desk, urgency, duplicate_of, summary)` | The saved result | Writes the `triage` row, sets `suggest_escalation` if urgency is `high`, and moves a `new` tip to `triaged`. Only for the tip being triaged. It can't escalate |

Guardrails (Day 3). The code enforces these; the prompt only repeats them:

- **Least privilege:** the tools read `tips` only, with named columns. Nothing the agent can call reads
  `sources`, and a test enforces it with an SQLite authorizer.
- **Untrusted input:** tip text reaches the model only as data, between tags (a tip can't close the tag
  early), and the system prompt says to ignore instructions inside it. `save_triage` rejects a summary
  with an email address or phone number, or one that repeats five or more words from an instruction
  hidden in the tip. Tips that contain such instructions are flagged on arrival and in `/editor`.
  This lowers the risk; it does not remove it. The next two guardrails do.
- **Human in the loop:** the agent only sets `suggest_escalation`. A tip becomes `escalated` only when an
  editor posts to the escalate route, and the editor's name and the time go into `tip_events`.
- **Audit trail:** `tip_events` records arrival, flagging, every agent decision or failure, and the
  escalation. It is shown per tip on `/editor/log`.
- **Tested like an attacker:** `data/triage_expected.json` includes the attack tips (9, 11 and 12).
  `triage-eval` exits with an error if any tip is escalated without an editor, or if contact details
  reach a summary, the model or the log.

Limits:

- At most 10 model calls per tip; then the tip stays `new` and an error is logged.
- `save_triage` rejects an unknown desk or urgency, a `duplicate_of` that isn't an earlier tip, an
  empty summary, a summary that breaks the rules above, or another tip's id. The error goes back to the
  model to correct.
- Tests use `FakeModel` and never call the real model.
- Known gaps: `/editor` and `/editor/log` have no login, and the escalate form has no CSRF protection.

## Project layout

```
app/            Flask app (routes in __init__.py, database in db.py, schema.sql)
app/triage.py   the triage agent; app/llm.py connects it to the model;
                app/guardrails.py holds the checks around it
                (check the connection with: python -m app.check_model)
app/templates/  HTML pages
data/           sample tips
tests/          pytest tests
exercises/      step-by-step guide for each day
guides/         how to work safely with a coding agent
handouts/       printable PDFs of the setup guide, exercise and safety guide
AGENTS.md       instructions your coding agent reads automatically
```
