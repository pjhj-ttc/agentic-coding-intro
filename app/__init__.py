import json
import logging
import os

from flask import Flask, redirect, render_template, request, url_for

from . import db, triage

MAX_SUBJECT = 200
MAX_BODY = 10_000
MAX_CONTACT = 200
CONTACT_METHODS = {"email", "phone", "signal"}


def validate_tip(form):
    """Return (tip, errors) for a submitted form."""
    tip = {
        "subject": form.get("subject", "").strip(),
        "body": form.get("body", "").strip(),
        "contact_method": form.get("contact_method", "").strip() or None,
        "contact_value": form.get("contact_value", "").strip() or None,
    }
    errors = []
    if not tip["subject"]:
        errors.append("Please give your tip a subject.")
    elif len(tip["subject"]) > MAX_SUBJECT:
        errors.append(f"The subject can be at most {MAX_SUBJECT} characters.")
    if not tip["body"]:
        errors.append("Please write your tip.")
    elif len(tip["body"]) > MAX_BODY:
        errors.append(f"The tip can be at most {MAX_BODY} characters.")
    if tip["contact_method"] is None:
        tip["contact_value"] = None  # anonymous: never store contact details
    elif tip["contact_method"] not in CONTACT_METHODS:
        errors.append("Please choose a valid contact method.")
    elif not tip["contact_value"]:
        errors.append("Please tell us how to reach you, or choose to stay anonymous.")
    elif len(tip["contact_value"]) > MAX_CONTACT:
        errors.append(f"Contact details can be at most {MAX_CONTACT} characters.")
    return tip, errors


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        DATABASE=os.path.join(app.instance_path, "tips.sqlite"),
        MAX_CONTENT_LENGTH=64 * 1024,  # reject huge submissions before reading them
    )
    if test_config:
        app.config.update(test_config)

    # The development server logs every request with the visitor's IP address.
    # Sources must not be traceable, so keep only warnings and errors.
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)
    triage.init_app(app)

    @app.template_filter("readable_json")
    def readable_json(value, indent=None):
        # Unlike tojson, keeps Ø and ' as they are; the template still HTML-escapes the result
        return json.dumps(value, ensure_ascii=False, indent=indent)

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "GET":
            return render_template("index.html", tip={}, errors=[])

        tip, errors = validate_tip(request.form)
        if errors:
            return render_template("index.html", tip=tip, errors=errors), 400

        conn = db.get_db()
        conn.execute(
            "INSERT INTO tips (subject, body, contact_method, contact_value)"
            " VALUES (?, ?, ?, ?)",
            (tip["subject"], tip["body"], tip["contact_method"], tip["contact_value"]),
        )
        conn.commit()
        return redirect(url_for("thanks"))

    @app.route("/thanks")
    def thanks():
        return render_template("thanks.html")

    @app.route("/editor")
    def editor():
        tips = db.get_db().execute(
            "SELECT tips.*, triage.desk, triage.urgency, triage.duplicate_of, triage.summary"
            " FROM tips LEFT JOIN triage ON triage.tip_id = tips.id"
            " ORDER BY tips.created_at DESC, tips.id DESC"
        ).fetchall()
        return render_template("editor.html", tips=tips)

    @app.route("/editor/log")
    def agent_log():
        events = db.get_db().execute(
            "SELECT * FROM agent_log ORDER BY id"
        ).fetchall()
        runs = {}
        for event in events:
            entry = dict(event)
            entry["detail"] = json.loads(entry["detail"]) if entry["detail"] else None
            runs.setdefault(event["run_id"], []).append(entry)
        # newest run first, events within a run in order
        return render_template("agent_log.html", runs=list(reversed(runs.items())))

    @app.errorhandler(413)
    def too_large(e):
        return render_template(
            "index.html", tip={}, errors=["Your submission is too large."]
        ), 413

    return app
