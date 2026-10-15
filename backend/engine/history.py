import pandas as pd
from .ops import apply, OpError


class HistoryError(Exception):
    pass


class History:
    """
    Undo/redo over validated ops.
    - Original data is never modified.
    - A failed op changes nothing.
    - A new op after undo discards the redo stack.
    - Snapshots every `checkpoint_every` steps keep undo fast.
    """

    def __init__(self, df: pd.DataFrame, checkpoint_every: int = 5):
        if checkpoint_every < 1:
            raise ValueError("checkpoint_every must be >= 1")
        self._n = checkpoint_every
        self._ops: list[dict] = []
        self._cursor = 0
        self._checkpoints = {0: df.copy()}
        self._current = df.copy()

    # --- state ---
    @property
    def df(self) -> pd.DataFrame:
        return self._current  # treat as read-only; apply() never mutates it

    @property
    def original(self) -> pd.DataFrame:
        return self._checkpoints[0]

    @property
    def can_undo(self) -> bool:
        return self._cursor > 0

    @property
    def can_redo(self) -> bool:
        return self._cursor < len(self._ops)

    def steps(self) -> list[dict]:
        return [
            {"index": i, "op": op, "applied": i < self._cursor}
            for i, op in enumerate(self._ops)
        ]

    # --- actions ---
    def apply(self, op: dict):
        new_df, result = apply(self._current, op)  # raises OpError, state untouched
        self._ops = self._ops[: self._cursor]  # discard redo branch
        self._checkpoints = {k: v for k, v in self._checkpoints.items() if k <= self._cursor}
        self._ops.append(op)
        self._cursor += 1
        self._current = new_df
        self._maybe_checkpoint()
        return result

    def undo(self):
        if not self.can_undo:
            raise HistoryError("Nothing to undo.")
        target = self._cursor - 1
        self._current = self._rebuild(target)
        self._cursor = target
        return self._current

    def redo(self):
        if not self.can_redo:
            raise HistoryError("Nothing to redo.")
        new_df, _ = apply(self._current, self._ops[self._cursor])
        self._current = new_df
        self._cursor += 1
        self._maybe_checkpoint()
        return self._current

    def reset(self):
        """Back to the original data and clear all history."""
        original = self._checkpoints[0]
        self._ops = []
        self._cursor = 0
        self._checkpoints = {0: original}
        self._current = original.copy()
        return self._current

    # --- internals ---
    def _maybe_checkpoint(self):
        if self._cursor % self._n == 0 and self._cursor not in self._checkpoints:
            self._checkpoints[self._cursor] = self._current.copy()

    def _rebuild(self, target: int) -> pd.DataFrame:
        base = max(k for k in self._checkpoints if k <= target)
        df = self._checkpoints[base]
        for op in self._ops[base:target]:
            df, _ = apply(df, op)
        return df.copy() if base == target else df