def find_duplicates(df, subset=None):
    """
    Returns number of duplicate rows in dataframe.
    If subset provided, checks duplicates based on those columns.
    """
    if subset:
        return int(df.duplicated(subset=[subset]).sum())
    return int(df.duplicated().sum())


def remove_duplicates(df, subset=None, return_removed=False):
    """
    Removes duplicate rows.
    
    Parameters:
        subset (str or None): Column name to check duplicates on.
        return_removed (bool): If True, also returns removed rows.
    
    Returns:
        df_cleaned, summary (and optionally removed_rows)
    """

    df = df.copy()
    summary = {}

    # Count duplicates
    duplicate_count = find_duplicates(df, subset=subset)
    summary["duplicates_found"] = duplicate_count

    if subset:
        duplicated_mask = df.duplicated(subset=[subset])
    else:
        duplicated_mask = df.duplicated()

    removed_rows = df[duplicated_mask]

    df_cleaned = df[~duplicated_mask]

    summary["duplicates_removed"] = int(len(removed_rows))

    if return_removed:
        return df_cleaned, summary, removed_rows

    return df_cleaned, summary