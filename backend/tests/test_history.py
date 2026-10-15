import numpy as np
import pandas as pd
import pytest
from engine.history import History, HistoryError
from engine.ops import OpError


@pytest.fixture
def df():
    return pd.DataFrame({
        "age": [10, np.nan, 30, np.nan, 30],
        "city": ["a", "b", None, "b", "a"],
    })


FILL = {"op": "fill_nulls", "column": "age", "strategy": "median"}
DEDUP = {"op": "drop_duplicates"}
REN = {"op": "rename_column", "column": "age", "new_name": "years"}


def test_original_never_modified(df):
    snap = df.copy()
    h = History(df)
    h.apply(FILL); h.apply(DEDUP)
    pd.testing.assert_frame_equal(df, snap)


def test_undo_redo_restores_exact_states(df):
    h = History(df, checkpoint_every=2)
    states = [h.df.copy()]
    for op in (FILL, DEDUP, REN):
        h.apply(op)
        states.append(h.df.copy())
    for i in range(2, -1, -1):          # undo back to start
        h.undo()
        pd.testing.assert_frame_equal(h.df, states[i])
    for i in range(1, 4):               # redo forward to end
        h.redo()
        pd.testing.assert_frame_equal(h.df, states[i])


def test_failed_op_changes_nothing(df):
    h = History(df)
    h.apply(FILL)
    before, steps = h.df.copy(), h.steps()
    with pytest.raises(OpError):
        h.apply({"op": "rename_column", "column": "nope", "new_name": "x"})
    pd.testing.assert_frame_equal(h.df, before)
    assert h.steps() == steps


def test_new_op_after_undo_discards_redo(df):
    h = History(df)
    h.apply(FILL); h.apply(DEDUP)
    h.undo()
    assert h.can_redo
    h.apply(REN)
    assert not h.can_redo
    assert len(h.steps()) == 2
    assert "years" in h.df.columns


def test_undo_redo_empty_raise(df):
    h = History(df)
    with pytest.raises(HistoryError):
        h.undo()
    with pytest.raises(HistoryError):
        h.redo()


def test_long_chain_with_checkpoints():
    d = pd.DataFrame({"c0": [1, 2, 3]})
    h = History(d, checkpoint_every=2)
    for i in range(7):
        h.apply({"op": "rename_column", "column": f"c{i}", "new_name": f"c{i+1}"})
    assert list(h.df.columns) == ["c7"]
    for _ in range(5):
        h.undo()
    assert list(h.df.columns) == ["c2"]
    h.redo()
    assert list(h.df.columns) == ["c3"]


def test_reset(df):
    h = History(df)
    h.apply(FILL); h.apply(DEDUP)
    h.reset()
    pd.testing.assert_frame_equal(h.df, df)
    assert not h.can_undo and not h.can_redo
    assert h.steps() == []


def test_steps_flags(df):
    h = History(df)
    h.apply(FILL); h.apply(DEDUP)
    h.undo()
    assert [s["applied"] for s in h.steps()] == [True, False]