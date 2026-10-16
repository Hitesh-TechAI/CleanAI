import pandas as pd
import math
import numpy as np

WEIGHTS = {"completeness": 0.40, "uniqueness": 0.20, "consistency": 0.25, "validity": 0.15}


def _f(x):
    """JSON-safe float (None for NaN/inf/None)."""
    if x is None or pd.isna(x):
        return None
    x = float(x)
    return None if math.isinf(x) else x

def _kind(s: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(s):
        return "bool"
    if pd.api.types.is_numeric_dtype(s):
        return "numeric"
    if pd.api.types.is_datetime64_any_dtype(s):
        return "datetime"
    return "text"


def _numeric_stats(s: pd.Series) -> dict:
    v = s.dropna().astype("float64")

    # Count infinity before excluding non-finite values.
    infinite = int(np.isinf(v.to_numpy()).sum())

    # Only finite values are safe for statistical calculations.
    v = v[np.isfinite(v)]

    if v.empty:
        return {
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "std": None,
            "outliers": 0,
            "infinite": infinite,
        }

    outliers = 0
    if len(v) >= 4:
        q1, q3 = v.quantile(0.25), v.quantile(0.75)
        iqr = q3 - q1
        if iqr > 0:
            outliers = int(
                ((v < q1 - 1.5 * iqr) |
                 (v > q3 + 1.5 * iqr)).sum()
            )

    return {
        "min": _f(v.min()),
        "max": _f(v.max()),
        "mean": _f(v.mean()),
        "median": _f(v.median()),
        "std": _f(v.std()),
        "outliers": outliers,
        "infinite": infinite,
    }

def _text_stats(s: pd.Series) -> dict:
    t = s.dropna().astype("string")
    if t.empty:
        return {"whitespace": 0, "numeric_like": False, "numeric_all_int": False, "case_variants": 0}
    stripped = t.str.strip()
    nums = pd.to_numeric(stripped, errors="coerce")
    numeric_like = bool(nums.notna().all())
    return {
        "whitespace": int((t != stripped).sum()),
        "numeric_like": numeric_like,
        "numeric_all_int": numeric_like and bool((nums % 1 == 0).all()),
        "case_variants": int(stripped.nunique() - stripped.str.lower().nunique()),
    }


def profile(df: pd.DataFrame) -> dict:
    rows, cols = df.shape
    dup_rows = int(df.duplicated().sum()) if rows else 0
    columns, null_cells, outlier_cells, numeric_cells, flagged = [], 0, 0, 0, 0

    for name in df.columns:
        s = df[name]
        kind = _kind(s)
        n_null = int(s.isna().sum())
        null_cells += n_null
        info = {
            "name": str(name), "dtype": str(s.dtype), "kind": kind,
            "nulls": n_null,
            "null_pct": round(100 * n_null / rows, 2) if rows else 0.0,
            "unique": int(s.nunique(dropna=True)),
        }
        if kind == "numeric":
            st = _numeric_stats(s)
            info.update(st)
            outlier_cells += st["outliers"] + st["infinite"]
            numeric_cells += int(s.notna().sum())
        elif kind == "datetime":
            nn = s.dropna()
            info["min"] = nn.min().isoformat() if len(nn) else None
            info["max"] = nn.max().isoformat() if len(nn) else None
        elif kind == "text":
            st = _text_stats(s)
            info.update(st)
            if st["whitespace"] or st["numeric_like"] or st["case_variants"]:
                flagged += 1
        columns.append(info)

    if rows == 0 or cols == 0:
        quality = {"completeness": 0.0, "uniqueness": 0.0,
                   "consistency": 0.0, "validity": 0.0, "score": 0.0}
    else:
        comp = {
            "completeness": 1 - null_cells / (rows * cols),
            "uniqueness": 1 - dup_rows / rows,
            "consistency": 1 - flagged / cols,
            "validity": 1 - (outlier_cells / numeric_cells if numeric_cells else 0.0),
        }
        score = 100 * sum(WEIGHTS[k] * v for k, v in comp.items())
        quality = {**{k: round(v, 4) for k, v in comp.items()}, "score": round(score, 2)}

    return {"rows": rows, "cols": cols, "null_cells": null_cells,
            "duplicate_rows": dup_rows, "columns": columns, "quality": quality}


def _s(column, issue, message, op, priority):
    return {"id": f"{issue}:{column}", "column": column, "issue": issue,
            "message": message, "op": op, "priority": priority}


def suggest(df: pd.DataFrame) -> list[dict]:
    """
    Rule-based suggestions. op is a valid schema op, or None for info-only items
    (e.g. outliers are flagged but never auto-deleted). Sorted so applying them
    in order works: trim, case, cast, fill, then dedupe.
    """
    p = profile(df)
    rows = p["rows"]
    out = []
    if rows == 0:
        return out

    for c in p["columns"]:
        n = c["name"]
        if c["nulls"] == rows and p["cols"] > 1:
            out.append(_s(n, "all_null", f"'{n}' is entirely empty.",
                          {"op": "drop_column", "column": n}, 0))
            continue
        if c["kind"] == "text":
            if c["whitespace"]:
                out.append(_s(n, "whitespace", f"'{n}': {c['whitespace']} values have extra spaces.",
                              {"op": "trim_text", "column": n}, 1))
            if c["case_variants"]:
                out.append(_s(n, "case_variants",
                              f"'{n}': values differ only by letter case ({c['case_variants']} extra variants).",
                              {"op": "change_case", "column": n, "case": "lower"}, 2))
            if c["numeric_like"]:
                to = "int" if c["numeric_all_int"] else "float"
                out.append(_s(n, "numeric_as_text", f"'{n}' holds numbers stored as text.",
                              {"op": "cast_type", "column": n, "to": to}, 3))
        if c["nulls"]:
            strat = "median" if c["kind"] == "numeric" else "mode"
            out.append(_s(n, "nulls", f"'{n}': {c['nulls']} missing values ({c['null_pct']}%).",
                          {"op": "fill_nulls", "column": n, "strategy": strat}, 4))
        if c["kind"] == "numeric" and c.get("outliers"):
            out.append(_s(n, "outliers",
                          f"'{n}': {c['outliers']} possible outliers. Review manually.", None, 9))

    if p["duplicate_rows"]:
        out.append(_s("*", "duplicates", f"{p['duplicate_rows']} duplicate rows.",
                      {"op": "drop_duplicates"}, 5))
    return sorted(out, key=lambda x: x["priority"])


def compare(before: pd.DataFrame, after: pd.DataFrame) -> dict:
    """Before/after summary. Always read the score together with the row counts."""
    a, b = profile(before), profile(after)
    return {
        "rows_before": a["rows"], "rows_after": b["rows"],
        "rows_removed": a["rows"] - b["rows"],
        "cols_before": a["cols"], "cols_after": b["cols"],
        "null_cells_before": a["null_cells"], "null_cells_after": b["null_cells"],
        "duplicates_before": a["duplicate_rows"], "duplicates_after": b["duplicate_rows"],
        "score_before": a["quality"]["score"], "score_after": b["quality"]["score"],
    }