import pandas as pd


def detect_outliers_iqr(df, column=None):
    """
    Detect outliers using IQR method.
    If column provided, check only that column.
    Returns dictionary with outlier counts.
    """

    summary = {}
    df = df.copy()

    if column:
        numeric_cols = [column]
    else:
        numeric_cols = df.select_dtypes(include="number").columns

    for col in numeric_cols:

        if col not in df.columns:
            continue

        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1

        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
        summary[col] = len(outliers)

    return summary


def remove_outliers(
    df,
    column=None,
    method="remove",
    return_removed=False
):
    """
    Handle outliers dynamically.

    Parameters:
        column (str or None): Specific column to process.
        method (str): "remove" or "cap"
        return_removed (bool): If True, return removed rows separately.

    Returns:
        df_cleaned, summary (and optionally removed_rows)
    """

    df = df.copy()
    summary = {}
    removed_rows = pd.DataFrame()

    if column:
        numeric_cols = [column]
    else:
        numeric_cols = df.select_dtypes(include="number").columns

    total_removed = 0

    for col in numeric_cols:

        if col not in df.columns:
            continue

        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1

        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        if method == "remove":

            mask = (df[col] < lower_bound) | (df[col] > upper_bound)

            removed = df[mask]
            removed_rows = pd.concat([removed_rows, removed])

            df = df[~mask]

            summary[col] = int(len(removed))
            total_removed += int(len(removed))

        elif method == "cap":

            df[col] = df[col].clip(lower_bound, upper_bound)
            summary[col] = "Capped"

    summary["total_outliers_removed"] = total_removed

    if return_removed:
        return df, summary, removed_rows

    return df, summary