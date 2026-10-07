"""The triage agent: for each new tip, pick a desk and an urgency, spot duplicates and
write a one-sentence summary for an editor.

The model works through three tools (get_tip, search_tips, save_triage) in a loop,
one conversation per tip. Every model call, tool call and error goes to `agent_log`.
"""

import json
import re
import uuid
from pathlib import Path

import click
from flask.cli import with_appcontext

from . import db
from .llm import ModelError, get_model

DESKS = ("politics", "business", "environment", "health", "local", "none")
URGENCIES = ("high", "normal", "low")
MAX_MODEL_CALLS = 10
EXPECTED_FILE = Path(__file__).parent.parent / "data" / "triage_expected.json"

SYSTEM_PROMPT = f"""You are the triage assistant of The Daily Ledger's newsroom.
You triage one tip at a time from the public tip portal.

1. Read the tip with get_tip.
2. Use search_tips to look for earlier tips about the same story. Search for distinctive
   words: names, places, companies. Try more than one search if needed.
3. Call save_triage exactly once with:
   - desk: one of {", ".join(DESKS)} ("none" if it isn't a news tip)
   - urgency: "high" if it needs an editor today (danger to people, evidence that may
     disappear, a source asking for urgent contact), "low" for minor local matters and
     feedback, otherwise "normal"
   - duplicate_of: the id of the earliest tip about the same story, or null
   - summary: one neutral sentence for an editor
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_tip",
            "description": "Get the tip to triage.",
            "parameters": {
                "type": "object",
                "properties": {"tip_id": {"type": "integer"}},
                "required": ["tip_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_tips",
            "description": "Find earlier tips containing any of the words in the query, best matches first.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_triage",
            "description": "Save the triage result for the tip. Call this once, at the end.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tip_id": {"type": "integer"},
                    "desk": {"type": "string", "enum": list(DESKS)},
                    "urgency": {"type": "string", "enum": list(URGENCIES)},
                    "duplicate_of": {"type": ["integer", "null"]},
                    "summary": {"type": "string"},
                },
                "required": ["tip_id", "desk", "urgency", "duplicate_of", "summary"],
            },
        },
    },
]


class ToolError(Exception):
    """A tool call the agent got wrong. The message goes back to the model."""


class TriageRun:
    """One run of the agent: shares a run id and a database connection across tips."""

    def __init__(self, conn, model, dry_run=False):
        self.conn = conn
        self.model = model
        self.dry_run = dry_run
        self.run_id = uuid.uuid4().hex[:8]

    def log(self, tip_id, event, name=None, detail=None):
        self.conn.execute(
            "INSERT INTO agent_log (run_id, tip_id, event, name, detail) VALUES (?, ?, ?, ?, ?)",
            (self.run_id, tip_id, event, name, json.dumps(detail, ensure_ascii=False)),
        )
        self.conn.commit()

    # ---- tools ----

    def get_tip(self, tip_id, current):
        row = self.conn.execute("SELECT * FROM tips WHERE id = ?", (tip_id,)).fetchone()
        if row is None:
            raise ToolError(f"No tip with id {tip_id}")
        return dict(row)

    def search_tips(self, query, current):
        words = [w for w in re.findall(r"\w+", query.lower()) if len(w) >= 3]
        if not words:
            raise ToolError("Search for at least one word of three letters or more")
        rows = self.conn.execute("SELECT * FROM tips WHERE id < ?", (current,)).fetchall()
        scored = []
        for row in rows:
            text = f"{row['subject']} {row['body']}".lower()
            score = sum(1 for w in words if w in text)
            if score:
                scored.append((score, row["id"], dict(row)))
        scored.sort(key=lambda s: (-s[0], s[1]))
        return [tip for _, _, tip in scored[:5]]

    def save_triage(self, tip_id, desk, urgency, duplicate_of, summary, current):
        if tip_id != current:
            raise ToolError(f"You are triaging tip {current}, not tip {tip_id}")
        if desk not in DESKS:
            raise ToolError(f"Unknown desk {desk!r}. Use one of: {', '.join(DESKS)}")
        if urgency not in URGENCIES:
            raise ToolError(f"Unknown urgency {urgency!r}. Use one of: {', '.join(URGENCIES)}")
        if duplicate_of is not None:
            earlier = self.conn.execute(
                "SELECT id FROM tips WHERE id = ? AND id < ?", (duplicate_of, current)
            ).fetchone()
            if earlier is None:
                raise ToolError(f"duplicate_of must be the id of an earlier tip, not {duplicate_of}")
        if not summary or not summary.strip():
            raise ToolError("The summary can't be empty")

        result = {"tip_id": tip_id, "desk": desk, "urgency": urgency,
                  "duplicate_of": duplicate_of, "summary": summary.strip()}
        if not self.dry_run:
            self.conn.execute(
                "INSERT OR REPLACE INTO triage (tip_id, desk, urgency, duplicate_of, summary, model)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (tip_id, desk, urgency, duplicate_of, result["summary"], self.model.name),
            )
            # Urgent tips go straight to the editor on duty
            status = "escalated" if urgency == "high" else "triaged"
            self.conn.execute("UPDATE tips SET status = ? WHERE id = ?", (status, tip_id))
            self.conn.commit()
        return result

    # ---- the loop ----

    def call_tool(self, tip_id, call):
        name = call["function"]["name"]
        tools = {"get_tip": self.get_tip, "search_tips": self.search_tips,
                 "save_triage": self.save_triage}
        try:
            args = json.loads(call["function"]["arguments"] or "{}")
            if name not in tools:
                raise ToolError(f"Unknown tool {name!r}")
            result = tools[name](**args, current=tip_id)
        except (ToolError, TypeError, json.JSONDecodeError) as e:
            self.log(tip_id, "error", name, {"arguments": call["function"]["arguments"], "error": str(e)})
            return name, {"error": str(e)}
        self.log(tip_id, "tool_call", name, {"arguments": args, "result": result})
        return name, result

    def triage_tip(self, tip_id):
        """Run the conversation for one tip. Returns the saved result, or None if it failed."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Triage tip {tip_id}."},
        ]
        for _ in range(MAX_MODEL_CALLS):
            try:
                reply = self.model.chat(messages, TOOLS)
            except ModelError as e:
                self.log(tip_id, "error", None, {"error": str(e)})
                return None
            calls = reply.get("tool_calls") or []
            self.log(tip_id, "model_call", None, {
                "usage": self.model.last_usage,
                "content": reply.get("content"),
                "tool_calls": [c["function"]["name"] for c in calls],
            })
            message = {"role": "assistant", "content": reply.get("content")}
            if calls:
                message["tool_calls"] = calls
            messages.append(message)
            if not calls:
                messages.append({"role": "user", "content": "Finish by calling save_triage."})
                continue
            saved = None
            for call in calls:
                name, result = self.call_tool(tip_id, call)
                messages.append({"role": "tool", "tool_call_id": call["id"],
                                 "content": json.dumps(result, ensure_ascii=False)})
                if name == "save_triage" and "error" not in result:
                    saved = result
            if saved:
                return saved
        self.log(tip_id, "error", None, {"error": f"Stopped after {MAX_MODEL_CALLS} model calls"})
        return None


def new_tip_ids(conn):
    return [r["id"] for r in conn.execute("SELECT id FROM tips WHERE status = 'new' ORDER BY id")]


def evaluate(conn, model, expected):
    """Triage the expected tips in dry-run mode and compare. Returns (rows, scores)."""
    run = TriageRun(conn, model, dry_run=True)
    existing = {r["id"] for r in conn.execute("SELECT id FROM tips")}
    rows = []
    for exp in expected:
        if exp["tip"] not in existing:
            continue
        actual = run.triage_tip(exp["tip"]) or {}
        rows.append({
            "tip": exp["tip"],
            "expected": exp,
            "actual": actual,
            "match": {f: actual.get(f, "?") in exp[f] for f in ("desk", "urgency", "duplicate_of")},
        })
    scores = {
        f: round(100 * sum(r["match"][f] for r in rows) / len(rows)) if rows else 0
        for f in ("desk", "urgency", "duplicate_of")
    }
    return rows, scores


def show(values):
    return "/".join("-" if v is None else str(v) for v in values)


@click.command("triage")
@with_appcontext
@click.option("--dry-run", is_flag=True, help="Print the results without saving them.")
def triage_command(dry_run):
    """Triage all new tips with the agent."""
    conn = db.get_db()
    try:
        run = TriageRun(conn, get_model(), dry_run=dry_run)
    except ModelError as e:
        raise click.ClickException(str(e))
    ids = new_tip_ids(conn)
    if not ids:
        click.echo("No new tips.")
    for tip_id in ids:
        result = run.triage_tip(tip_id)
        if result is None:
            click.echo(f"Tip {tip_id}: failed, see the agent log (run {run.run_id})")
        else:
            click.echo(f"Tip {tip_id}: {result['desk']}, {result['urgency']} urgency, "
                       f"duplicate of {result['duplicate_of'] or '-'}. {result['summary']}")
    click.echo(f"Run {run.run_id}{' (dry run, nothing saved)' if dry_run else ''}")


@click.command("triage-eval")
@with_appcontext
def triage_eval_command():
    """Run the agent (dry run) on the sample tips and compare with data/triage_expected.json."""
    expected = json.loads(EXPECTED_FILE.read_text(encoding="utf8"))
    try:
        model = get_model()
    except ModelError as e:
        raise click.ClickException(str(e))
    rows, scores = evaluate(db.get_db(), model, expected)
    fields = ("desk", "urgency", "duplicate_of")
    table = [["tip", *fields]]
    for r in rows:
        table.append([str(r["tip"])] + [
            f"{'ok' if r['match'][f] else 'XX'} {show([r['actual'].get(f, '?')])} ({show(r['expected'][f])})"
            for f in fields
        ])
    widths = [max(len(line[i]) for line in table) for i in range(len(table[0]))]
    for line in table:
        click.echo("   ".join(cell.ljust(w) for cell, w in zip(line, widths)).rstrip())
    click.echo(f"\nCorrect: desk {scores['desk']}%, urgency {scores['urgency']}%, "
               f"duplicates {scores['duplicate_of']}%   (expected values in brackets)")


def init_app(app):
    app.cli.add_command(triage_command)
    app.cli.add_command(triage_eval_command)
