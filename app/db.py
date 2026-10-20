import json
import sqlite3
from pathlib import Path

import click
from flask import current_app, g

from . import guardrails

SEED_FILE = Path(__file__).parent.parent / "data" / "seed_tips.json"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf8"))


def add_tip(conn, tip, created_at=None):
    """Store a tip, its source (if not anonymous) and its first chain-of-custody event.

    Does not commit. `tip` has subject, body and optionally contact_method/contact_value.
    """
    cur = conn.execute(
        "INSERT INTO tips (created_at, subject, body) VALUES (COALESCE(?, datetime('now')), ?, ?)",
        (created_at, tip["subject"], tip["body"]),
    )
    tip_id = cur.lastrowid
    if tip.get("contact_method"):
        conn.execute(
            "INSERT INTO sources (tip_id, contact_method, contact_value) VALUES (?, ?, ?)",
            (tip_id, tip["contact_method"], tip["contact_value"]),
        )
    record_event(conn, tip_id, "received", "source", created_at=created_at)
    if guardrails.looks_like_injection(f"{tip['subject']}\n{tip['body']}"):
        record_event(conn, tip_id, "flagged", "system", created_at=created_at,
                     detail={"reason": "the tip contains instructions aimed at the triage system"})
    return tip_id


def record_event(conn, tip_id, event, actor, detail=None, created_at=None):
    """Add a row to the tip's chain of custody. Does not commit. Never put contact details in `detail`."""
    conn.execute(
        "INSERT INTO tip_events (created_at, tip_id, event, actor, detail)"
        " VALUES (COALESCE(?, datetime('now')), ?, ?, ?, ?)",
        (created_at, tip_id, event, actor, json.dumps(detail, ensure_ascii=False) if detail else None),
    )


def seed_db():
    db = get_db()
    tips = json.loads(SEED_FILE.read_text(encoding="utf8"))
    for tip in tips:
        add_tip(db, tip, created_at=tip["created_at"])
    db.commit()
    return len(tips)


@click.command("init-db")
def init_db_command():
    """Delete all tips and create an empty database."""
    init_db()
    click.echo("Initialized the database.")


@click.command("seed")
def seed_command():
    """Load the sample tips from data/seed_tips.json."""
    count = seed_db()
    click.echo(f"Loaded {count} sample tips.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_command)
