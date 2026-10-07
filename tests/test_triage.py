import json

from app import triage
from app.db import get_db, seed_db
from app.llm import FakeModel, text_reply, tool_call_reply
from app.triage import TriageRun, evaluate


def add_tip(app, subject, body="A tip"):
    with app.app_context():
        conn = get_db()
        cur = conn.execute("INSERT INTO tips (subject, body) VALUES (?, ?)", (subject, body))
        conn.commit()
        return cur.lastrowid


def save(tip_id, desk="local", urgency="normal", duplicate_of=None, summary="A summary."):
    return tool_call_reply(("save_triage", {
        "tip_id": tip_id, "desk": desk, "urgency": urgency,
        "duplicate_of": duplicate_of, "summary": summary,
    }))


def run_agent(app, replies, tip_id, dry_run=False):
    with app.app_context():
        run = TriageRun(get_db(), FakeModel(replies), dry_run=dry_run)
        return run, run.triage_tip(tip_id)


def row(app, sql, *args):
    with app.app_context():
        return get_db().execute(sql, args).fetchone()


def log_events(app):
    with app.app_context():
        return [(r["event"], r["name"]) for r in get_db().execute("SELECT * FROM agent_log ORDER BY id")]


def test_agent_reads_tip_and_saves_triage(app):
    tip = add_tip(app, "Bus late")
    _, result = run_agent(app, [
        tool_call_reply(("get_tip", {"tip_id": tip})),
        save(tip, desk="local", urgency="low", summary="Bus line 12 is late."),
    ], tip)

    assert result["desk"] == "local"
    saved = row(app, "SELECT * FROM triage WHERE tip_id = ?", tip)
    assert (saved["desk"], saved["urgency"], saved["model"]) == ("local", "low", "fake")
    assert row(app, "SELECT status FROM tips WHERE id = ?", tip)["status"] == "triaged"


def test_high_urgency_escalates_the_tip(app):
    tip = add_tip(app, "School roof")
    run_agent(app, [save(tip, desk="politics", urgency="high")], tip)
    assert row(app, "SELECT status FROM tips WHERE id = ?", tip)["status"] == "escalated"


def test_dry_run_saves_nothing(app):
    tip = add_tip(app, "Bus late")
    _, result = run_agent(app, [save(tip)], tip, dry_run=True)
    assert result["desk"] == "local"
    assert row(app, "SELECT * FROM triage WHERE tip_id = ?", tip) is None
    assert row(app, "SELECT status FROM tips WHERE id = ?", tip)["status"] == "new"


def test_search_finds_earlier_tips_only(app):
    first = add_tip(app, "Trucks at warehouse 7")
    tip = add_tip(app, "Again at warehouse 7")
    add_tip(app, "Later tip about warehouse 7")
    with app.app_context():
        run = TriageRun(get_db(), FakeModel([]))
        found = run.search_tips("Warehouse 7 trucks", current=tip)
    assert [t["id"] for t in found] == [first]


def test_duplicate_of_is_saved(app):
    first = add_tip(app, "Trucks at warehouse 7")
    tip = add_tip(app, "Again at warehouse 7")
    run_agent(app, [
        tool_call_reply(("search_tips", {"query": "warehouse"})),
        save(tip, desk="environment", duplicate_of=first),
    ], tip)
    assert row(app, "SELECT duplicate_of FROM triage WHERE tip_id = ?", tip)[0] == first


def test_invalid_answer_goes_back_to_the_model(app):
    tip = add_tip(app, "Bus late")
    model_replies = [save(tip, desk="sports"), save(tip, desk="local")]
    run, result = run_agent(app, model_replies, tip)

    assert result["desk"] == "local"
    second_call = run.model.calls[1]["messages"]
    assert "Unknown desk 'sports'" in second_call[-1]["content"]
    assert ("error", "save_triage") in log_events(app)


def test_duplicate_must_be_an_earlier_tip(app):
    tip = add_tip(app, "Bus late")
    _, result = run_agent(app, [save(tip, duplicate_of=tip + 5), save(tip)], tip)
    assert result["duplicate_of"] is None


def test_agent_cannot_save_another_tip(app):
    other = add_tip(app, "Someone else's tip")
    tip = add_tip(app, "Bus late")
    run_agent(app, [save(other), save(tip)], tip)
    assert row(app, "SELECT * FROM triage WHERE tip_id = ?", other) is None


def test_agent_is_nudged_when_it_only_talks(app):
    tip = add_tip(app, "Bus late")
    run, result = run_agent(app, [text_reply("This looks local."), save(tip)], tip)
    assert result is not None
    assert run.model.calls[1]["messages"][-1]["content"] == "Finish by calling save_triage."


def test_agent_stops_after_max_model_calls(app):
    tip = add_tip(app, "Bus late")
    looping = [tool_call_reply(("get_tip", {"tip_id": tip}))] * (triage.MAX_MODEL_CALLS + 5)
    run, result = run_agent(app, looping, tip)
    assert result is None
    assert len(run.model.calls) == triage.MAX_MODEL_CALLS
    assert log_events(app)[-1] == ("error", None)


def test_every_step_is_logged(app):
    tip = add_tip(app, "Bus late")
    run_agent(app, [tool_call_reply(("get_tip", {"tip_id": tip})), save(tip)], tip)
    assert log_events(app) == [
        ("model_call", None), ("tool_call", "get_tip"),
        ("model_call", None), ("tool_call", "save_triage"),
    ]


def test_triage_command_only_handles_new_tips(app, monkeypatch):
    done = add_tip(app, "Already triaged")
    with app.app_context():
        get_db().execute("UPDATE tips SET status = 'triaged' WHERE id = ?", (done,))
        get_db().commit()
    tip = add_tip(app, "New tip")
    monkeypatch.setattr(triage, "get_model", lambda: FakeModel([save(tip)]))

    result = app.test_cli_runner().invoke(args=["triage"])
    assert f"Tip {tip}: local" in result.output
    assert f"Tip {done}" not in result.output


def test_triage_command_without_model_key_explains(app):
    # conftest hides the key, as on a laptop where it was never saved
    add_tip(app, "New tip")
    result = app.test_cli_runner().invoke(args=["triage"])
    assert result.exit_code != 0
    assert "key.txt" in result.output


def test_eval_scores_against_expected(app):
    with app.app_context():
        seed_db()
        expected = [
            {"tip": 1, "desk": ["environment"], "urgency": ["high"], "duplicate_of": [None]},
            {"tip": 2, "desk": ["environment"], "urgency": ["high"], "duplicate_of": [1]},
        ]
        model = FakeModel([
            save(1, desk="environment", urgency="high"),
            save(2, desk="local", urgency="high", duplicate_of=1),
        ])
        rows, scores = evaluate(get_db(), model, expected)
        assert get_db().execute("SELECT COUNT(*) FROM triage").fetchone()[0] == 0  # dry run
    assert scores == {"desk": 50, "urgency": 100, "duplicate_of": 100}
    assert rows[1]["match"]["desk"] is False


def test_eval_command_prints_table_and_scores(app, monkeypatch):
    with app.app_context():
        seed_db()
    replies = [save(i, desk="environment", urgency="high") for i in range(1, 11)]
    monkeypatch.setattr(triage, "get_model", lambda: FakeModel(replies))
    result = app.test_cli_runner().invoke(args=["triage-eval"])
    lines = result.output.splitlines()
    assert lines[0].split() == ["tip", "desk", "urgency", "duplicate_of"]
    assert "ok environment (environment)" in lines[1]
    assert "Correct: desk 30%" in result.output


def test_editor_shows_triage(client, app):
    first = add_tip(app, "Trucks at warehouse 7")
    tip = add_tip(app, "Again at warehouse 7")
    run_agent(app, [save(tip, desk="environment", urgency="high", duplicate_of=first,
                         summary="New dumping reported.")], tip)
    page = client.get("/editor").get_data(as_text=True)
    assert "New dumping reported." in page
    assert f'href="#tip-{first}"' in page
    assert "Not triaged yet" in page  # the first tip


def test_log_page_shows_tool_calls_escaped(client, app):
    tip = add_tip(app, "<script>alert(1)</script>")
    run_agent(app, [tool_call_reply(("get_tip", {"tip_id": tip})), save(tip)], tip)
    page = client.get("/editor/log").get_data(as_text=True)
    assert "get_tip" in page and "save_triage" in page
    assert "<script>alert(1)</script>" not in page


def test_log_page_keeps_text_readable(client, app):
    tip = add_tip(app, "Østerby school's roof")
    run_agent(app, [tool_call_reply(("search_tips", {"query": "Østerby"})), save(tip)], tip)
    page = client.get("/editor/log").get_data(as_text=True)
    assert "Østerby" in page
    assert "\\u00d8" not in page


def test_expected_file_covers_all_seed_tips():
    expected = json.loads(triage.EXPECTED_FILE.read_text(encoding="utf8"))
    assert [e["tip"] for e in expected] == list(range(1, 11))
    for e in expected:
        assert set(e["desk"]) <= set(triage.DESKS)
        assert set(e["urgency"]) <= set(triage.URGENCIES)
