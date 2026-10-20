import json
import logging
import os

from flask import Flask, abort, redirect, render_template, request, url_for

from . import db, triage

MAX_SUBJECT = 200
MAX_BODY = 10_000
MAX_CONTACT = 200
MAX_EDITOR_NAME = 80
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
        db.add_tip(conn, tip)
        conn.commit()
        return redirect(url_for("thanks"))

    @app.route("/thanks")
    def thanks():
        return render_template("thanks.html")

    @app.route("/editor")
    def editor():
        # The only page that reads the sources table
        tips = db.get_db().execute(
            "SELECT tips.*, sources.contact_method, sources.contact_value,"
            "       triage.desk, triage.urgency, triage.duplicate_of, triage.summary,"
            "       triage.suggest_escalation,"
            "       escalation.actor AS escalated_by, escalation.created_at AS escalated_at,"
            "       EXISTS (SELECT 1 FROM tip_events WHERE tip_id = tips.id AND event = 'flagged') AS flagged"
            " FROM tips"
            " LEFT JOIN sources ON sources.tip_id = tips.id"
            " LEFT JOIN triage ON triage.tip_id = tips.id"
            " LEFT JOIN tip_events AS escalation ON escalation.tip_id = tips.id AND escalation.event = 'escalated'"
            " ORDER BY tips.created_at DESC, tips.id DESC"
        ).fetchall()
        return render_template("editor.html", tips=tips)

    @app.post("/editor/tips/<int:tip_id>/escalate")
    def escalate(tip_id):
        """The only way a tip becomes 'escalated': an editor decides, and the name is recorded."""
        editor_name = request.form.get("editor", "").strip()
        if not editor_name:
            abort(400, "Please enter your name to escalate a tip.")
        if len(editor_name) > MAX_EDITOR_NAME:
            abort(400, f"The name can be at most {MAX_EDITOR_NAME} characters.")
        conn = db.get_db()
        tip = conn.execute(
            "SELECT tips.status, triage.suggest_escalation FROM tips"
            " LEFT JOIN triage ON triage.tip_id = tips.id WHERE tips.id = ?",
            (tip_id,),
        ).fetchone()
        if tip is None:
            abort(404)
        if tip["status"] == "escalated":
            abort(409, "This tip is already escalated.")
        if not tip["suggest_escalation"]:
            abort(409, "The triage agent has not suggested escalating this tip.")
        conn.execute("UPDATE tips SET status = 'escalated' WHERE id = ?", (tip_id,))
        db.record_event(conn, tip_id, "escalated", editor_name)
        conn.commit()
        return redirect(url_for("editor") + f"#tip-{tip_id}")

    @app.route("/editor/log")
    def agent_log():
        conn = db.get_db()
        events = conn.execute("SELECT * FROM agent_log ORDER BY id").fetchall()
        runs = {}
        for event in events:
            entry = dict(event)
            entry["detail"] = json.loads(entry["detail"]) if entry["detail"] else None
            runs.setdefault(event["run_id"], []).append(entry)

        # The chain of custody per tip: arrival, every agent run, who escalated and when
        custody = {}
        for event in conn.execute(
            "SELECT tip_events.*, tips.subject FROM tip_events"
            " JOIN tips ON tips.id = tip_events.tip_id ORDER BY tip_events.tip_id, tip_events.id"
        ):
            entry = dict(event)
            entry["detail"] = json.loads(entry["detail"]) if entry["detail"] else None
            custody.setdefault((event["tip_id"], event["subject"]), []).append(entry)

        # newest run first, events within a run in order
        return render_template("agent_log.html", runs=list(reversed(runs.items())),
                               custody=list(custody.items()))

    @app.errorhandler(413)
    def too_large(e):
        return render_template(
            "index.html", tip={}, errors=["Your submission is too large."]
        ), 413

    return app
