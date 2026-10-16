import numpy as np
import pandas as pd
import warnings
import pytest
from engine.ops import apply, OpError
from engine.history import History


# ---- drop_nulls ----
def test_drop_nulls_any_and_subset():
    d = pd.DataFrame({"a": [1, None, 3], "b": ["x", "y", None]})
    out, _ = apply(d, {"op": "drop_nulls"})
    assert len(out) == 1
    out, _ = apply(d, {"op": "drop_nulls", "columns": ["a"]})
    assert len(out) == 2


def test_drop_nulls_all():
    d = pd.DataFrame({"a": [1, None, None], "b": ["x", None, "z"]})
    out, _ = apply(d, {"op": "drop_nulls", "how": "all"})
    assert len(out) == 2


def test_drop_nulls_bad_column():
    with pytest.raises(OpError):
        apply(pd.DataFrame({"a": [1]}), {"op": "drop_nulls", "columns": ["zz"]})


# ---- cast_type ----
def test_cast_int_float_with_null():
    d = pd.DataFrame({"a": ["1", "2", None]})
    out, _ = apply(d, {"op": "cast_type", "column": "a", "to": "int"})
    assert out["a"].iloc[:2].tolist() == [1, 2] and out["a"].isna().iloc[2]
    out, _ = apply(d, {"op": "cast_type", "column": "a", "to": "float"})
    assert out["a"].dtype == "float64"


def test_cast_int_fails_on_text_and_decimals():
    with pytest.raises(OpError):
        apply(pd.DataFrame({"a": ["1", "x"]}), {"op": "cast_type", "column": "a", "to": "int"})
    with pytest.raises(OpError):
        apply(pd.DataFrame({"a": ["1.5", "2"]}), {"op": "cast_type", "column": "a", "to": "int"})


def test_cast_bool():
    d = pd.DataFrame({"a": ["yes", "no", "TRUE"]})
    out, _ = apply(d, {"op": "cast_type", "column": "a", "to": "bool"})
    assert out["a"].tolist() == [True, False, True]
    with pytest.raises(OpError):
        apply(pd.DataFrame({"a": ["maybe"]}), {"op": "cast_type", "column": "a", "to": "bool"})


def test_cast_datetime():
    d = pd.DataFrame({"a": ["2024-01-05", "2024-02-10"]})
    out, _ = apply(d, {"op": "cast_type", "column": "a", "to": "datetime"})
    assert pd.api.types.is_datetime64_any_dtype(out["a"])
    with pytest.raises(OpError):
        apply(pd.DataFrame({"a": ["not a date"]}), {"op": "cast_type", "column": "a", "to": "datetime"})


def test_cast_failure_leaves_input_untouched():
    d = pd.DataFrame({"a": ["1", "x"]})
    snap = d.copy()
    with pytest.raises(OpError):
        apply(d, {"op": "cast_type", "column": "a", "to": "int"})
    pd.testing.assert_frame_equal(d, snap)


# ---- trim_text / change_case ----
def test_trim_text():
    d = pd.DataFrame({"a": [" a ", "b  ", " c", None]})
    out, r = apply(d, {"op": "trim_text", "column": "a"})
    assert out["a"].iloc[:3].tolist() == ["a", "b", "c"]
    assert r.cells_changed == 3


def test_text_ops_reject_numeric():
    d = pd.DataFrame({"a": [1, 2]})
    with pytest.raises(OpError):
        apply(d, {"op": "trim_text", "column": "a"})
    with pytest.raises(OpError):
        apply(d, {"op": "change_case", "column": "a", "case": "lower"})


def test_change_case():
    d = pd.DataFrame({"a": ["aB", "hello world"]})
    assert apply(d, {"op": "change_case", "column": "a", "case": "lower"})[0]["a"].tolist() == ["ab", "hello world"]
    assert apply(d, {"op": "change_case", "column": "a", "case": "upper"})[0]["a"].tolist() == ["AB", "HELLO WORLD"]
    assert apply(d, {"op": "change_case", "column": "a", "case": "title"})[0]["a"].tolist() == ["Ab", "Hello World"]


# ---- filter_rows ----
def test_filter_numeric():
    d = pd.DataFrame({"a": [1, 2, 3, None]})
    assert apply(d, {"op": "filter_rows", "column": "a", "operator": "gt", "value": 2})[0]["a"].tolist() == [3]
    assert len(apply(d, {"op": "filter_rows", "column": "a", "operator": "gte", "value": "2"})[0]) == 2
    assert len(apply(d, {"op": "filter_rows", "column": "a", "operator": "ne", "value": 1})[0]) == 2  # null excluded


def test_filter_text():
    d = pd.DataFrame({"a": ["apple", "banana", "apricot", None]})
    assert apply(d, {"op": "filter_rows", "column": "a", "operator": "eq", "value": "banana"})[0]["a"].tolist() == ["banana"]
    assert len(apply(d, {"op": "filter_rows", "column": "a", "operator": "contains", "value": "ap"})[0]) == 2


def test_filter_null_ops():
    d = pd.DataFrame({"a": [1, None, 3]})
    assert len(apply(d, {"op": "filter_rows", "column": "a", "operator": "is_null"})[0]) == 1
    assert len(apply(d, {"op": "filter_rows", "column": "a", "operator": "not_null"})[0]) == 2


def test_filter_errors():
    d = pd.DataFrame({"a": [1, 2]})
    with pytest.raises(OpError):
        apply(d, {"op": "filter_rows", "column": "a", "operator": "gt"})
    with pytest.raises(OpError):
        apply(d, {"op": "filter_rows", "column": "a", "operator": "gt", "value": "abc"})
    with pytest.raises(OpError):
        apply(d, {"op": "filter_rows", "column": "a", "operator": "like", "value": 1})
    with pytest.raises(OpError):
        apply(d, {"op": "filter_rows", "column": "a", "operator": "contains", "value": "1"})


# ---- sort ----
def test_sort_nulls_last():
    d = pd.DataFrame({"a": [3, 1, None, 2]})
    out, _ = apply(d, {"op": "sort", "column": "a"})
    assert out["a"].iloc[:3].tolist() == [1, 2, 3] and out["a"].isna().iloc[3]
    out, _ = apply(d, {"op": "sort", "column": "a", "ascending": False})
    assert out["a"].iloc[:3].tolist() == [3, 2, 1] and out["a"].isna().iloc[3]


# ---- drop_column ----
def test_drop_column():
    d = pd.DataFrame({"a": [1], "b": [2]})
    assert list(apply(d, {"op": "drop_column", "column": "a"})[0].columns) == ["b"]
    with pytest.raises(OpError):
        apply(d, {"op": "drop_column", "column": "zz"})
    with pytest.raises(OpError):
        apply(pd.DataFrame({"a": [1]}), {"op": "drop_column", "column": "a"})


# ---- full chain through History ----
def test_full_chain_undo_redo():
    d = pd.DataFrame({"name": [" Ann ", "bob", "bob", None], "age": ["10", "20", "20", "30"]})
    h = History(d, checkpoint_every=2)
    states = [h.df.copy()]
    for op in (
        {"op": "trim_text", "column": "name"},
        {"op": "change_case", "column": "name", "case": "title"},
        {"op": "cast_type", "column": "age", "to": "int"},
        {"op": "drop_duplicates"},
        {"op": "drop_nulls"},
        {"op": "sort", "column": "age", "ascending": False},
    ):
        h.apply(op)
        states.append(h.df.copy())
    assert h.df["name"].tolist() == ["Bob", "Ann"]
    for i in range(5, -1, -1):
        h.undo()
        pd.testing.assert_frame_equal(h.df, states[i])
    for i in range(1, 7):
        h.redo()
        pd.testing.assert_frame_equal(h.df, states[i])

def test_fill_mean_ignores_inf_no_warning():
    d = pd.DataFrame({"a": [1.0, 3.0, float("inf"), float("-inf"), None]})
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        out, _ = apply(d, {"op": "fill_nulls", "column": "a", "strategy": "mean"})
    assert out["a"].iloc[4] == 2.0


def test_fill_mean_only_inf_fails():
    d = pd.DataFrame({"a": [float("inf"), None]})
    with pytest.raises(OpError):
        apply(d, {"op": "fill_nulls", "column": "a", "strategy": "mean"})