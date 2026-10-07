import pytest

from app import create_app, llm
from app.db import init_db


@pytest.fixture(autouse=True)
def no_real_model_key(monkeypatch, tmp_path):
    """Tests never see the real model key, so they can't call the real model."""
    monkeypatch.delenv(llm.KEY_VARIABLE, raising=False)
    monkeypatch.setattr(llm, "KEY_FILE", tmp_path / "no-key.txt")


@pytest.fixture
def app(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite")})
    with app.app_context():
        init_db()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()
