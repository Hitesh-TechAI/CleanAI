import csv
import os
import pandas as pd

CSV_EXT = {".csv", ".tsv", ".txt"}
XLSX_EXT = {".xlsx", ".xlsm"}
MAX_EXCEL_ROWS = 1_048_575  # Excel limit minus the header row
ENCODINGS = ("utf-8-sig", "cp1252", "latin-1")


class LoadError(Exception):
    pass


class ExportError(Exception):
    pass


def _ext(path: str) -> str:
    return os.path.splitext(path)[1].lower()


def _check(path: str):
    if not os.path.isfile(path):
        raise LoadError(f"File not found: {path}")
    if os.path.getsize(path) == 0:
        raise LoadError("File is empty.")


def _clean_headers(df: pd.DataFrame) -> pd.DataFrame:
    """Headers become unique, non-empty strings."""
    seen, names = set(), []
    for i, c in enumerate(df.columns):
        n = str(c).strip()
        if not n or n.startswith("Unnamed:"):
            n = f"column_{i + 1}"
        base, k = n, 1
        while n in seen:
            k += 1
            n = f"{base}_{k}"
        seen.add(n)
        names.append(n)
    df.columns = names
    return df


def _sniff_sep(path: str) -> str:
    with open(path, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
        sample = f.read(65536)
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        return ","


def _load_csv(path: str, all_text: bool) -> pd.DataFrame:
    sep = "\t" if _ext(path) == ".tsv" else _sniff_sep(path)
    last = None
    for enc in ENCODINGS:
        try:
            return pd.read_csv(path, sep=sep, encoding=enc,
                               dtype=str if all_text else None)
        except UnicodeDecodeError as e:
            last = e
        except pd.errors.EmptyDataError:
            raise LoadError("File has no data.")
        except pd.errors.ParserError as e:
            raise LoadError(f"Could not parse file: {e}")
    raise LoadError(f"Could not decode file: {last}")


def list_sheets(path: str) -> list[str]:
    _check(path)
    if _ext(path) not in XLSX_EXT:
        raise LoadError("Not an Excel file.")
    try:
        with pd.ExcelFile(path, engine="openpyxl") as x:
            return list(x.sheet_names)
    except Exception as e:
        raise LoadError(f"Could not open workbook: {e}")


def load(path: str, sheet: str | None = None, all_text: bool = False) -> pd.DataFrame:
    """
    Load CSV/TSV/TXT or XLSX/XLSM. First sheet by default.
    all_text=True keeps every value as text (preserves leading zeros in IDs/zip codes).
    """
    _check(path)
    ext = _ext(path)
    if ext in CSV_EXT:
        df = _load_csv(path, all_text)
    elif ext in XLSX_EXT:
        names = list_sheets(path)
        if sheet is None:
            sheet = names[0]
        if sheet not in names:
            raise LoadError(f"Sheet '{sheet}' not found. Available: {names}")
        try:
            df = pd.read_excel(path, sheet_name=sheet, engine="openpyxl",
                               dtype=str if all_text else None)
        except Exception as e:
            raise LoadError(f"Could not read sheet '{sheet}': {e}")
    else:
        raise LoadError(f"Unsupported file type '{ext}'. Use CSV, TSV, TXT or XLSX.")
    if df.shape[1] == 0:
        raise LoadError("File has no columns.")
    return _clean_headers(df)


def export(df: pd.DataFrame, path: str) -> str:
    """Atomic write: temp file first, then replace. A failure never damages an existing file."""
    ext = _ext(path)
    if ext not in CSV_EXT | XLSX_EXT:
        raise ExportError(f"Unsupported export type '{ext}'.")
    if ext in XLSX_EXT and len(df) > MAX_EXCEL_ROWS:
        raise ExportError(f"Too many rows for Excel ({len(df)} > {MAX_EXCEL_ROWS}). Export as CSV.")
    root, _ = os.path.splitext(path)
    tmp = f"{root}.tmp{ext}"  # keeps the real extension, e.g. out.tmp.xlsx
    try:
        if ext in XLSX_EXT:
            with pd.ExcelWriter(tmp, engine="openpyxl") as w:
                df.to_excel(w, index=False)
        else:
            df.to_csv(tmp, index=False, sep="\t" if ext == ".tsv" else ",",
                      encoding="utf-8-sig")
        os.replace(tmp, path)
    except Exception as e:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise ExportError(f"Export failed: {e}")
    return path