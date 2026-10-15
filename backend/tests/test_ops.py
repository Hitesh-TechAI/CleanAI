import numpy as np
import pandas as pd
import pytest
from engine.ops import apply, OpError


@pytest.fixture
def df():
    return pd.DataFrame({
        "age": [10, np.nan, 30, np.nan, 30],
        "city": ["a", "b", None, "b", "a"],
    })


def test_input_never_mutated(df):
    snap = df.copy()
    apply(df, {"op": "fill_nulls", "column": "age", "strategy": "median"})
    pd.testing.assert_frame_equal(df, snap)


def test_fill_median(df):
    out, r = apply(df, {"op": "fill_nulls", "column": "age", "strategy": "median"})
    assert out["age"].isna().sum() == 0
    assert out["age"].tolist() == [10, 30, 30, 30, 30]
    assert r.cells_changed == 2


def test_fill_mode_text(df):
    out, r = apply(df, {"op": "fill_nulls", "column": "city", "strategy": "mode"})
    assert out["city"].isna().sum() == 0 and r.cells_changed == 1


def test_fill_constant(df):
    out, _ = apply(df, {"op": "fill_nulls", "column": "age", "strategy": "constant", "value": 0})
    assert out["age"].tolist() == [10, 0, 30, 0, 30]


def test_constant_requires_value(df):
    with pytest.raises(OpError):
        apply(df, {"op": "fill_nulls", "column": "age", "strategy": "constant"})


def test_mean_on_text_fails(df):
    with pytest.raises(OpError):
        apply(df, {"op": "fill_nulls", "column": "city", "strategy": "mean"})


def test_missing_column(df):
    with pytest.raises(OpError):
        apply(df, {"op": "fill_nulls", "column": "nope", "strategy": "mode"})


def test_unknown_op(df):
    with pytest.raises(OpError):
        apply(df, {"op": "explode"})


def test_all_null_column_mean():
    d = pd.DataFrame({"x": [np.nan, np.nan]})
    with pytest.raises(OpError):
        apply(d, {"op": "fill_nulls", "column": "x", "strategy": "mean"})


def test_drop_duplicates_all_cols():
    d = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    out, r = apply(d, {"op": "drop_duplicates"})
    assert len(out) == 2 and r.rows_before == 3 and r.rows_after == 2


def test_drop_duplicates_subset_keep_last():
    d = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "z", "y"]})
    out, _ = apply(d, {"op": "drop_duplicates", "columns": ["a"], "keep": "last"})
    assert out["b"].tolist() == ["z", "y"]


def test_rename(df):
    out, _ = apply(df, {"op": "rename_column", "column": "age", "new_name": "years"})
    assert "years" in out.columns and "age" not in out.columns


def test_rename_collision(df):
    with pytest.raises(OpError):
        apply(df, {"op": "rename_column", "column": "age", "new_name": "city"})


def test_rename_empty(df):
    with pytest.raises(OpError):
        apply(df, {"op": "rename_column", "column": "age", "new_name": "  "})