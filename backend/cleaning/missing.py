import pandas as pd


def analyze_missing(df):
    """
    Analyze missing values in the dataframe.
    Returns a dictionary with missing percentage per column.
    """
    missing_percent = (df.isnull().sum() / len(df)) * 100
    return missing_percent.to_dict()


def handle_missing(
    df,
    column=None,
    strategy="median",
    threshold=None,
    return_removed=False
):
    """
    Handle missing values with dynamic control.

    Parameters:
        column (str or None): Specific column to handle.
        strategy (str): mean / median / mode / drop
        threshold (float or None): Drop columns above this % missing.
        return_removed (bool): If True, return removed rows separately.

    Returns:
        df_cleaned, summary (and optionally removed_rows)
    """

    df = df.copy()
    summary = {}
    removed_rows = pd.DataFrame()

    # -------------------------------
    # 1️⃣ Analyze Missing
    # -------------------------------
    missing_info = analyze_missing(df)
    summary["missing_before"] = missing_info

    # -------------------------------
    # 2️⃣ Drop Columns by Threshold
    # -------------------------------
    if threshold is not None:
        cols_to_drop = [
            col for col, percent in missing_info.items()
            if percent > threshold
        ]
        df = df.drop(columns=cols_to_drop)
        summary["dropped_columns"] = cols_to_drop
    else:
        summary["dropped_columns"] = []

    # -------------------------------
    # 3️⃣ Decide Columns to Process
    # -------------------------------
    if column:
        columns_to_process = [column]
    else:
        columns_to_process = df.columns

    # -------------------------------
    # 4️⃣ Apply Strategy
    # -------------------------------
    for col in columns_to_process:

        if col not in df.columns:
            continue

        missing_count = df[col].isnull().sum()

        if missing_count == 0:
            continue

        # Drop rows strategy
        if strategy == "drop":
            mask = df[col].isnull()
            removed_rows = pd.concat([removed_rows, df[mask]])
            df = df[~mask]
            summary[col] = f"Dropped {missing_count} rows"

        else:
            # Numeric columns
            if pd.api.types.is_numeric_dtype(df[col]):

                if strategy == "mean":
                    value = df[col].mean()
                elif strategy == "median":
                    value = df[col].median()
                elif strategy == "mode":
                    value = df[col].mode()[0]
                else:
                    value = df[col].median()

            # Categorical columns
            else:
                value = df[col].mode()[0]

            df[col] = df[col].fillna(value)
            summary[col] = f"Filled with {strategy}"

    # -------------------------------
    # 5️⃣ After Analysis
    # -------------------------------
    summary["missing_after"] = analyze_missing(df)

    if return_removed:
        return df, summary, removed_rows

    return df, summary