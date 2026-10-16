import operator
import numpy as np
import pandas as pd
from pydantic import ValidationError
from .schema import parse_op, OpResult


class OpError(Exception):
    """Raised for any invalid or failed operation. Input data is never modified."""


def _need_col(df, col):
    if col not in df.columns:
        raise OpError(f"Column '{col}' not found.")


def _fill_nulls(df, op):
    _need_col(df, op.column)
    s = df[op.column]
    before = int(s.isna().sum())
    if before == 0:
        return df, 0
    if op.strategy in ("mean", "median"):
        if not pd.api.types.is_numeric_dtype(s):
            raise OpError(f"'{op.strategy}' needs a numeric column; '{op.column}' is {s.dtype}.")
        vals = s.dropna().astype("float64")
        vals = vals[np.isfinite(vals)]
        if vals.empty:
            raise OpError(f"Column '{op.column}' has no finite values; cannot compute {op.strategy}.")
        fill = vals.mean() if op.strategy == "mean" else vals.median()
        
    elif op.strategy == "mode":
        m = s.mode(dropna=True)
        if m.empty:
            raise OpError(f"Column '{op.column}' has no values to compute mode.")
        fill = m.iloc[0]
    else:  # constant
        if op.value is None:
            raise OpError("Strategy 'constant' requires a 'value'.")
        fill = op.value
        if pd.api.types.is_numeric_dtype(s):
            try:
                fill = pd.to_numeric(fill)
            except (ValueError, TypeError):
                raise OpError(f"Value '{op.value}' is not numeric for column '{op.column}'.")
    df[op.column] = s.fillna(fill)
    return df, before - int(df[op.column].isna().sum())


def _drop_duplicates(df, op):
    if op.columns:
        for c in op.columns:
            _need_col(df, c)
    out = df.drop_duplicates(subset=op.columns, keep=op.keep).reset_index(drop=True)
    return out, 0


def _rename_column(df, op):
    _need_col(df, op.column)
    new = op.new_name.strip()
    if not new:
        raise OpError("New column name cannot be empty.")
    if new != op.column and new in df.columns:
        raise OpError(f"Column '{new}' already exists.")
    return df.rename(columns={op.column: new}), 0
def _drop_nulls(df, op):
    if op.columns:
        for c in op.columns:
            _need_col(df, c)
    return df.dropna(subset=op.columns, how=op.how).reset_index(drop=True), 0


def _cast_type(df, op):
    _need_col(df, op.column)
    s, t = df[op.column], op.to
    try:
        if t in ("int", "float"):
            num = pd.to_numeric(s, errors="raise")
            if t == "int":
                if (num.dropna() % 1 != 0).any():
                    raise OpError(f"Column '{op.column}' has non-integer values.")
                new = num.astype("Int64")
            else:
                new = num.astype("float64")
        elif t == "str":
            new = s.astype("string")
        elif t == "bool":
            m = {"true": True, "false": False, "1": True, "0": False,
                 "yes": True, "no": False}
            mapped = s.astype("string").str.strip().str.lower().map(m)
            if (mapped.isna() & s.notna()).any():
                raise OpError(f"Column '{op.column}' has values that are not boolean.")
            new = mapped.astype("boolean")
        else:
            new = pd.to_datetime(s, errors="raise")
    except OpError:
        raise
    except (ValueError, TypeError) as e:
        raise OpError(f"Cannot convert '{op.column}' to {t}: {e}")
    df[op.column] = new
    return df, int(s.notna().sum())


def _text_series(df, col):
    _need_col(df, col)
    s = df[col]
    if not (s.dtype == object or pd.api.types.is_string_dtype(s)):
        raise OpError(f"Column '{col}' is not text.")
    return s


def _text_apply(df, col, fn):
    s = _text_series(df, col)
    new = fn(s.str)
    changed = int(((s != new).fillna(False) & s.notna()).sum())
    df[col] = new
    return df, changed


def _trim_text(df, op):
    return _text_apply(df, op.column, lambda x: x.strip())


def _change_case(df, op):
    return _text_apply(df, op.column, lambda x: getattr(x, op.case)())


_CMP = {"eq": operator.eq, "ne": operator.ne, "gt": operator.gt,
        "gte": operator.ge, "lt": operator.lt, "lte": operator.le}


def _filter_rows(df, op):
    _need_col(df, op.column)
    s = df[op.column]
    if op.operator == "is_null":
        mask = s.isna()
    elif op.operator == "not_null":
        mask = s.notna()
    else:
        if op.value is None:
            raise OpError(f"Operator '{op.operator}' requires a 'value'.")
        if op.operator == "contains":
            _text_series(df, op.column)
            mask = s.astype("string").str.contains(str(op.value), regex=False, na=False)
        else:
            v = op.value
            if pd.api.types.is_numeric_dtype(s):
                try:
                    v = pd.to_numeric(v)
                except (ValueError, TypeError):
                    raise OpError(f"Value '{op.value}' is not numeric for '{op.column}'.")
            mask = (_CMP[op.operator](s, v)) & s.notna()
            mask = mask.fillna(False).astype(bool)
    return df[mask].reset_index(drop=True), 0


def _sort(df, op):
    _need_col(df, op.column)
    out = df.sort_values(op.column, ascending=op.ascending,
                         na_position="last", kind="stable").reset_index(drop=True)
    return out, 0


def _drop_column(df, op):
    _need_col(df, op.column)
    if df.shape[1] == 1:
        raise OpError("Cannot drop the only column.")
    return df.drop(columns=[op.column]), 0


HANDLERS = {
    "fill_nulls": _fill_nulls,
    "drop_duplicates": _drop_duplicates,
    "rename_column": _rename_column,
    "drop_nulls": _drop_nulls,
    "cast_type": _cast_type,
    "trim_text": _trim_text,
    "change_case": _change_case,
    "filter_rows": _filter_rows,
    "sort": _sort,
    "drop_column": _drop_column,
}



def apply(df: pd.DataFrame, op_dict: dict):
    """Returns (new_df, OpResult). Never mutates df. Raises OpError on any failure."""
    try:
        op = parse_op(op_dict)
    except ValidationError as e:
        raise OpError(f"Invalid operation: {e.errors()[0]['msg']}")
    work = df.copy()
    try:
        new_df, cells = HANDLERS[op.op](work, op)
    except OpError:
        raise
    except Exception as e:  # any unexpected failure: original stays untouched
        raise OpError(f"Operation failed: {e}")
    removed = len(df) - len(new_df)
    result = OpResult(
        op=op.op,
        rows_before=len(df), rows_after=len(new_df),
        cols_before=df.shape[1], cols_after=new_df.shape[1],
        cells_changed=cells,
        message=f"{op.op}: {cells} cells changed, {removed} rows removed.",
    )
    return new_df, result