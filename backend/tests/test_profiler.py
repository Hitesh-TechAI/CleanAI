import json
import numpy as np
import pandas as pd
from engine.profiler import profile, suggest, compare
from engine.schema import parse_op
from engine.history import History


def messy():
    return pd.DataFrame({
        "name": [" Ann", "ann", "Bob ", "Bob ", None, "Cy"],
        "age": ["10", "20", "30", "30", "40", None],
        "score": [1.0, 2.0, None, None, 5.0, 6.0],
    })


def test_clean_scores_100():
    d = pd.DataFrame({"a": [1, 2, 3, 4], "b": ["x", "y", "z", "w"]})
    assert profile(d)["quality"]["score"] == 100.0
    assert suggest(d) == []


def test_null_and_duplicate_counts():
    d = pd.DataFrame({"a": [1, 1, None], "b": ["x", "x", "y"]})
    p = profile(d)
    assert p["rows"] == 3 and p["null_cells"] == 1 and p["duplicate_rows"] == 1
    assert p["quality"]["completeness"] < 1 and p["quality"]["uniqueness"] < 1


def test_outlier_detection():
    d = pd.DataFrame({"a": [1, 2, 3, 4, 5, 6, 7, 8, 9, 1000]})
    p = profile(d)
    assert p["columns"][0]["outliers"] == 1
    assert p["quality"]["validity"] < 1


def test_text_issue_detection():
    d = pd.DataFrame({"t": [" a", "b ", "B"], "n": ["1", "2", "3"]})
    c = {x["name"]: x for x in profile(d)["columns"]}
    assert c["t"]["whitespace"] == 2 and c["t"]["case_variants"] == 1
    assert c["n"]["numeric_like"] and c["n"]["numeric_all_int"]


def test_json_serializable():
    json.dumps(profile(messy()))
    json.dumps(suggest(messy()))


def test_profile_does_not_mutate():
    d = messy()
    snap = d.copy()
    profile(d); suggest(d)
    pd.testing.assert_frame_equal(d, snap)


def test_empty_df():
    assert profile(pd.DataFrame())["quality"]["score"] == 0.0
    assert suggest(pd.DataFrame()) == []


def test_suggestions_are_valid_ops():
    for s in suggest(messy()):
        if s["op"] is not None:
            parse_op(s["op"])


def test_all_null_column():
    d = pd.DataFrame({"a": [1, 2], "b": [None, None]})
    s = suggest(d)
    assert s[0]["issue"] == "all_null" and s[0]["op"]["op"] == "drop_column"


def test_outliers_are_info_only():
    d = pd.DataFrame({"a": [1, 2, 3, 4, 5, 6, 7, 8, 9, 1000]})
    s = [x for x in suggest(d) if x["issue"] == "outliers"]
    assert len(s) == 1 and s[0]["op"] is None


def test_apply_all_suggestions_in_order():
    d = messy()
    before = profile(d)["quality"]["score"]
    h = History(d)
    for s in suggest(d):
        if s["op"] is not None:
            h.apply(s["op"])          # must never raise
    p = profile(h.df)
    assert p["null_cells"] == 0 and p["duplicate_rows"] == 0
    assert p["quality"]["score"] > before


def test_compare():
    d = messy()
    h = History(d)
    for s in suggest(d):
        if s["op"] is not None:
            h.apply(s["op"])
    r = compare(d, h.df)
    assert r["rows_removed"] == r["rows_before"] - r["rows_after"] == 1
    assert r["null_cells_after"] == 0 and r["score_after"] > r["score_before"]

def test_inf_values_json_safe():
    d = pd.DataFrame({"a": [1.0, float("inf"), 3.0]})
    json.dumps(profile(d), allow_nan=False)