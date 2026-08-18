import pandas as pd


# -------------------------------
# Text Normalization
# -------------------------------

def normalize_text_columns(df, column=None):
    df = df.copy()

    if column:
        columns = [column]
    else:
        columns = df.select_dtypes(include="object").columns

    for col in columns:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower()

    return df


# -------------------------------
# Numeric Conversion
# -------------------------------

def convert_numeric_columns(df, column=None):
    df = df.copy()

    if column:
        columns = [column]
    else:
        columns = df.columns

    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="ignore")

    return df


# -------------------------------
# Date Conversion
# -------------------------------

def convert_date_columns(df, column=None, standardize_format=None):
    df = df.copy()

    if column:
        columns = [column]
    else:
        columns = df.select_dtypes(include="object").columns

    for col in columns:
        if col not in df.columns:
            continue

        try:
            converted = pd.to_datetime(df[col], errors="coerce")

            if converted.notnull().sum() > len(df) * 0.5:
                df[col] = converted

                if standardize_format:
                    df[col] = df[col].dt.strftime(standardize_format)

        except:
            continue

    return df


# -------------------------------
# Main Type Handler
# -------------------------------

def handle_types(
    df,
    column=None,
    normalize_text=True,
    convert_numeric=True,
    convert_dates=True,
    date_format=None
):
    """
    Dynamic type handler.

    Parameters:
        column (str or None): Specific column to process.
        normalize_text (bool)
        convert_numeric (bool)
        convert_dates (bool)
        date_format (str or None): e.g. "%Y-%m-%d"

    Returns:
        df_cleaned, summary
    """

    df = df.copy()
    summary = {}

    if normalize_text:
        df = normalize_text_columns(df, column=column)
        summary["text_normalized"] = True

    if convert_numeric:
        df = convert_numeric_columns(df, column=column)
        summary["numeric_conversion_attempted"] = True

    if convert_dates:
        df = convert_date_columns(
            df,
            column=column,
            standardize_format=date_format
        )
        summary["date_conversion_attempted"] = True

    return df, summary