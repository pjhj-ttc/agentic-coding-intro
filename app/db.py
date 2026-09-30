import json
import sqlite3
from pathlib import Path

import click
from flask import current_app, g

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


def seed_db():
    db = get_db()
    tips = json.loads(SEED_FILE.read_text(encoding="utf8"))
    for tip in tips:
        db.execute(
            "INSERT INTO tips (created_at, subject, body, contact_method, contact_value)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                tip["created_at"],
                tip["subject"],
                tip["body"],
                tip.get("contact_method"),
                tip.get("contact_value"),
            ),
        )
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
