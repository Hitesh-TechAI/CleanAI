import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api import main
from engine import loaders


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("CLEANAI_TOKEN", raising=False)
    main._sessions.clear()
    yield TestClient(main.app)
    main._sessions.clear()


@pytest.fixture
def csv_path(tmp_path):
    p = tmp_path / "m.csv"
    p.write_text("name,age,score\n Ann,10,1.0\nann,20,2.0\nBob ,30,\nBob ,30,\n,40,5.0\nCy,,6.0\n")
    return str(p)


def do_load(client, path, **kw):
    r = client.post("/load", json={"path": path, **kw})
    assert r.status_code == 200, r.text
    return r.json()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_load_and_state(client, csv_path):
    d = do_load(client, csv_path)
    assert d["state"]["rows"] == 6 and d["state"]["cols"] == 3
    assert not d["state"]["can_undo"] and not d["state"]["can_redo"]


def test_load_missing_file_400(client, tmp_path):
    r = client.post("/load", json={"path": str(tmp_path / "nope.csv")})
    assert r.status_code == 400


def test_load_unsupported_400(client, tmp_path):
    p = tmp_path / "x.pdf"
    p.write_text("hi")
    assert client.post("/load", json={"path": str(p)}).status_code == 400


def test_sheets(client, tmp_path):
    p = str(tmp_path / "w.xlsx")
    with pd.ExcelWriter(p) as w:
        pd.DataFrame({"x": [1]}).to_excel(w, sheet_name="A", index=False)
        pd.DataFrame({"y": [2]}).to_excel(w, sheet_name="B", index=False)
    assert client.post("/sheets", json={"path": p}).json() == {"sheets": ["A", "B"]}
    d = do_load(client, p, sheet="B")
    r = client.get(f"/sessions/{d['session_id']}/preview").json()
    assert r["columns"] == ["y"]


def test_unknown_session_404(client):
    assert client.get("/sessions/nope/profile").status_code == 404
    assert client.post("/sessions/nope/undo").status_code == 404


def test_profile(client, csv_path):
    sid = do_load(client, csv_path)["session_id"]
    p = client.get(f"/sessions/{sid}/profile").json()
    assert p["rows"] == 6 and "score" in p["quality"]


def test_preview_paging_and_nulls(client, csv_path):
    sid = do_load(client, csv_path)["session_id"]
    r = client.get(f"/sessions/{sid}/preview", params={"offset": 2, "limit": 2}).json()
    assert len(r["rows"]) == 2 and r["total_rows"] == 6 and r["offset"] == 2
    last = client.get(f"/sessions/{sid}/preview", params={"offset": 5, "limit": 10}).json()
    assert len(last["rows"]) == 1
    assert last["rows"][0][1] is None  # NaN becomes JSON null


def test_preview_limit_validation(client, csv_path):
    sid = do_load(client, csv_path)["session_id"]
    assert client.get(f"/sessions/{sid}/preview", params={"limit": 0}).status_code == 422
    assert client.get(f"/sessions/{sid}/preview", params={"limit": 9999}).status_code == 422


def test_apply_and_state(client, csv_path):
    sid = do_load(client, csv_path)["session_id"]
    r = client.post(f"/sessions/{sid}/apply", json={"op": {"op": "drop_duplicates"}})
    assert r.status_code == 200
    body = r.json()
    assert body["result"]["rows_after"] == 5
    assert body["state"]["can_undo"] and len(body["state"]["steps"]) == 1


def test_invalid_op_400_state_unchanged(client, csv_path):
    sid = do_load(client, csv_path)["session_id"]
    r = client.post(f"/sessions/{sid}/apply",
                    json={"op": {"op": "rename_column", "column": "nope", "new_name": "x"}})
    assert r.status_code == 400
    r = client.post(f"/sessions/{sid}/apply", json={"op": {"op": "explode"}})
    assert r.status_code == 400
    st = client.get(f"/sessions/{sid}/state").json()
    assert st["rows"] == 6 and st["steps"] == [] and not st["can_undo"]


def test_undo_redo(client, csv_path):
    sid = do_load(client, csv_path)["session_id"]
    client.post(f"/sessions/{sid}/apply",
                json={"op": {"op": "rename_column", "column": "name", "new_name": "full_name"}})
    assert client.get(f"/sessions/{sid}/preview").json()["columns"][0] == "full_name"
    assert client.post(f"/sessions/{sid}/undo").json()["can_redo"]
    assert client.get(f"/sessions/{sid}/preview").json()["columns"][0] == "name"
    client.post(f"/sessions/{sid}/redo")
    assert client.get(f"/sessions/{sid}/preview").json()["columns"][0] == "full_name"


def test_undo_empty_409(client, csv_path):
    sid = do_load(client, csv_path)["session_id"]
    assert client.post(f"/sessions/{sid}/undo").status_code == 409
    assert client.post(f"/sessions/{sid}/redo").status_code == 409


def test_reset(client, csv_path):
    sid = do_load(client, csv_path)["session_id"]
    client.post(f"/sessions/{sid}/apply", json={"op": {"op": "drop_duplicates"}})
    client.post(f"/sessions/{sid}/apply", json={"op": {"op": "drop_nulls"}})
    st = client.post(f"/sessions/{sid}/reset").json()
    assert st["rows"] == 6 and st["steps"] == [] and not st["can_undo"]


def test_compare(client, csv_path):
    sid = do_load(client, csv_path)["session_id"]
    client.post(f"/sessions/{sid}/apply", json={"op": {"op": "drop_duplicates"}})
    c = client.get(f"/sessions/{sid}/compare").json()
    assert c["rows_before"] == 6 and c["rows_after"] == 5 and c["rows_removed"] == 1


def test_export_roundtrip(client, csv_path, tmp_path):
    sid = do_load(client, csv_path)["session_id"]
    client.post(f"/sessions/{sid}/apply", json={"op": {"op": "drop_duplicates"}})
    out = str(tmp_path / "out.xlsx")
    r = client.post(f"/sessions/{sid}/export", json={"path": out})
    assert r.status_code == 200 and r.json()["rows"] == 5
    assert len(loaders.load(out)) == 5


def test_export_bad_path_400(client, csv_path, tmp_path):
    sid = do_load(client, csv_path)["session_id"]
    r = client.post(f"/sessions/{sid}/export", json={"path": str(tmp_path / "nodir" / "o.csv")})
    assert r.status_code == 400


def test_close_session(client, csv_path):
    sid = do_load(client, csv_path)["session_id"]
    assert client.delete(f"/sessions/{sid}").status_code == 200
    assert client.get(f"/sessions/{sid}/state").status_code == 404
    assert client.delete(f"/sessions/{sid}").status_code == 404


def test_session_cap(client, csv_path, monkeypatch):
    monkeypatch.setattr(main, "MAX_SESSIONS", 1)
    do_load(client, csv_path)
    assert client.post("/load", json={"path": csv_path}).status_code == 429


def test_token_enforced(client, csv_path, monkeypatch):
    monkeypatch.setenv("CLEANAI_TOKEN", "secret")
    assert client.get("/health").status_code == 401
    assert client.get("/health", headers={"X-CleanAI-Token": "wrong"}).status_code == 401
    assert client.get("/health", headers={"X-CleanAI-Token": "secret"}).status_code == 200


def test_apply_all_suggestions_via_api(client, csv_path):
    sid = do_load(client, csv_path)["session_id"]
    sugg = client.get(f"/sessions/{sid}/suggestions").json()["suggestions"]
    assert sugg
    for s in sugg:
        if s["op"] is not None:
            r = client.post(f"/sessions/{sid}/apply", json={"op": s["op"]})
            assert r.status_code == 200, r.text
    p = client.get(f"/sessions/{sid}/profile").json()
    assert p["null_cells"] == 0 and p["duplicate_rows"] == 0
    c = client.get(f"/sessions/{sid}/compare").json()
    assert c["rows_removed"] == 1 and c["score_after"] > c["score_before"]