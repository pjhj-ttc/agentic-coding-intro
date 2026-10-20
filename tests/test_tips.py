import logging

from app.db import get_db, seed_db


def all_tips(app):
    with app.app_context():
        return get_db().execute("SELECT * FROM tips").fetchall()


def all_sources(app):
    with app.app_context():
        return get_db().execute("SELECT * FROM sources").fetchall()


def test_submit_anonymous_tip(client, app):
    response = client.post("/", data={"subject": "Hello", "body": "A tip"})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/thanks")

    [tip] = all_tips(app)
    assert tip["subject"] == "Hello"
    assert tip["status"] == "new"
    assert all_sources(app) == []


def test_submit_tip_with_contact(client, app):
    client.post("/", data={
        "subject": "Hello", "body": "A tip",
        "contact_method": "signal", "contact_value": "+45 00 00 00 00",
    })
    [tip] = all_tips(app)
    [source] = all_sources(app)
    assert source["tip_id"] == tip["id"]
    assert source["contact_method"] == "signal"
    assert source["contact_value"] == "+45 00 00 00 00"


def test_anonymous_tip_drops_contact_value(client, app):
    client.post("/", data={"subject": "Hello", "body": "A tip", "contact_value": "me@example.com"})
    assert all_sources(app) == []


def test_contact_details_are_not_stored_with_the_tip(app):
    with app.app_context():
        columns = [r["name"] for r in get_db().execute("PRAGMA table_info(tips)")]
    assert "contact_method" not in columns and "contact_value" not in columns


def test_editor_shows_contact_details(client, app):
    client.post("/", data={
        "subject": "Hello", "body": "A tip",
        "contact_method": "email", "contact_value": "source@example.com",
    })
    assert "email: source@example.com" in client.get("/editor").get_data(as_text=True)


def test_empty_form_is_rejected(client, app):
    response = client.post("/", data={"subject": " ", "body": ""})
    assert response.status_code == 400
    assert b"Please give your tip a subject" in response.data
    assert all_tips(app) == []


def test_contact_method_needs_value(client, app):
    response = client.post("/", data={"subject": "Hi", "body": "Tip", "contact_method": "email"})
    assert response.status_code == 400
    assert all_tips(app) == []


def test_unknown_contact_method_is_rejected(client, app):
    response = client.post("/", data={
        "subject": "Hi", "body": "Tip", "contact_method": "carrier-pigeon", "contact_value": "x",
    })
    assert response.status_code == 400


def test_too_long_tip_is_rejected(client, app):
    response = client.post("/", data={"subject": "Hi", "body": "x" * 10_001})
    assert response.status_code == 400
    assert all_tips(app) == []


def test_huge_request_is_rejected(client, app):
    response = client.post("/", data={"subject": "Hi", "body": "x" * 100_000})
    assert response.status_code == 413
    assert all_tips(app) == []


def test_editor_lists_newest_first(client, app):
    client.post("/", data={"subject": "First", "body": "one"})
    client.post("/", data={"subject": "Second", "body": "two"})
    page = client.get("/editor").get_data(as_text=True)
    assert page.index("Second") < page.index("First")


def test_editor_escapes_html_in_tips(client, app):
    with app.app_context():
        seed_db()
    page = client.get("/editor").get_data(as_text=True)
    assert "<script>" not in page
    assert "&lt;script&gt;" in page


def test_requests_are_not_logged_with_ip(app):
    assert logging.getLogger("werkzeug").getEffectiveLevel() > logging.INFO
