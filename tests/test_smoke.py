from app.db import get_db, seed_db


def test_front_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"confidential tip" in response.data


def test_seed_loads_sample_tips(app):
    with app.app_context():
        count = seed_db()
        rows = get_db().execute("SELECT COUNT(*) FROM tips").fetchone()[0]
    assert rows == count > 0
