import os
import pandas as pd
import pytest
from engine import loaders
from engine.loaders import load, export, list_sheets, LoadError, ExportError
from engine.profiler import suggest, profile
from engine.history import History


def test_csv_roundtrip(tmp_path):
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", None, "z"], "c": [1.5, None, 3.0]})
    p = str(tmp_path / "t.csv")
    export(df, p)
    pd.testing.assert_frame_equal(load(p), df, check_dtype=False)


def test_excel_roundtrip_types(tmp_path):
    df = pd.DataFrame({
        "i": [1, 2, 3], "f": [1.5, None, 3.5], "s": ["a", None, "c"],
        "d": pd.to_datetime(["2024-01-05", "2024-02-10", "2024-03-15"]),
        "b": [True, False, True],
    })
    p = str(tmp_path / "t.xlsx")
    export(df, p)
    out = load(p)
    pd.testing.assert_frame_equal(out, df, check_dtype=False)
    assert pd.api.types.is_datetime64_any_dtype(out["d"])
    assert pd.api.types.is_bool_dtype(out["b"])


def test_excel_sheet_selection(tmp_path):
    p = str(tmp_path / "w.xlsx")
    with pd.ExcelWriter(p) as w:
        pd.DataFrame({"x": [1]}).to_excel(w, sheet_name="First", index=False)
        pd.DataFrame({"y": [2]}).to_excel(w, sheet_name="Second", index=False)
    assert list(load(p).columns) == ["x"]
    assert list(load(p, sheet="Second").columns) == ["y"]


def test_list_sheets(tmp_path):
    p = str(tmp_path / "w.xlsx")
    with pd.ExcelWriter(p) as w:
        pd.DataFrame({"x": [1]}).to_excel(w, sheet_name="A", index=False)
        pd.DataFrame({"y": [2]}).to_excel(w, sheet_name="B", index=False)
    assert list_sheets(p) == ["A", "B"]


def test_bad_sheet(tmp_path):
    p = str(tmp_path / "w.xlsx")
    pd.DataFrame({"x": [1]}).to_excel(p, index=False)
    with pytest.raises(LoadError):
        load(p, sheet="Nope")


def test_semicolon_delimiter(tmp_path):
    p = tmp_path / "s.csv"
    p.write_text("name;age\nAnn;10\nBob;20\nCy;30\n")
    assert list(load(str(p)).columns) == ["name", "age"]


def test_tsv(tmp_path):
    p = tmp_path / "s.tsv"
    p.write_text("name\tage\nAnn\t10\nBob\t20\n")
    assert list(load(str(p)).columns) == ["name", "age"]


def test_latin1_encoding(tmp_path):
    p = tmp_path / "l.csv"
    p.write_bytes("name,city\nJosé,Zürich\n".encode("cp1252"))
    out = load(str(p))
    assert out["name"].iloc[0] == "José" and out["city"].iloc[0] == "Zürich"


def test_utf8_bom(tmp_path):
    p = tmp_path / "b.csv"
    p.write_bytes("\ufeffname,age\nAnn,10\n".encode("utf-8"))
    assert list(load(str(p)).columns) == ["name", "age"]


def test_leading_zeros_need_all_text(tmp_path):
    p = tmp_path / "z.csv"
    p.write_text("zip\n00123\n04567\n")
    assert load(str(p))["zip"].tolist() == [123, 4567]
    assert load(str(p), all_text=True)["zip"].tolist() == ["00123", "04567"]


def test_header_cleanup(tmp_path):
    p = tmp_path / "h.csv"
    p.write_text("a,a, \n1,2,3\n")
    cols = list(load(str(p)).columns)
    assert len(set(cols)) == 3 and "column_3" in cols


def test_empty_file(tmp_path):
    p = tmp_path / "e.csv"
    p.write_text("")
    with pytest.raises(LoadError):
        load(str(p))


def test_missing_file(tmp_path):
    with pytest.raises(LoadError):
        load(str(tmp_path / "nope.csv"))


def test_unsupported_load(tmp_path):
    p = tmp_path / "x.pdf"
    p.write_text("hi")
    with pytest.raises(LoadError):
        load(str(p))


def test_failed_export_keeps_existing_file(tmp_path, monkeypatch):
    p = tmp_path / "keep.csv"
    p.write_text("original")

    def boom(*a, **k):
        raise RuntimeError("disk full")

    monkeypatch.setattr(pd.DataFrame, "to_csv", boom)
    with pytest.raises(ExportError):
        export(pd.DataFrame({"a": [1]}), str(p))
    assert p.read_text() == "original"
    assert not os.path.exists(str(p) + ".tmp")


def test_excel_row_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(loaders, "MAX_EXCEL_ROWS", 2)
    with pytest.raises(ExportError):
        export(pd.DataFrame({"a": [1, 2, 3]}), str(tmp_path / "big.xlsx"))


def test_unsupported_export(tmp_path):
    with pytest.raises(ExportError):
        export(pd.DataFrame({"a": [1]}), str(tmp_path / "x.pdf"))


def test_load_clean_export_reload(tmp_path):
    p = tmp_path / "messy.csv"
    p.write_text("name,age,score\n Ann,10,1.0\nann,20,2.0\nBob ,30,\nBob ,30,\n,40,5.0\nCy,,6.0\n")
    df = load(str(p))
    h = History(df)
    for s in suggest(df):
        if s["op"] is not None:
            h.apply(s["op"])
    out_path = str(tmp_path / "clean.xlsx")
    export(h.df, out_path)
    back = load(out_path)
    q = profile(back)
    assert q["null_cells"] == 0 and q["duplicate_rows"] == 0