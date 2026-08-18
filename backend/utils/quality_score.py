def calculate_quality_score(df, missing_summary=None, duplicate_summary=None, outlier_summary=None):
    """
    Calculate quality score out of 100 based on:
    - Missing values
    - Duplicates
    - Outliers
    """

    score = 100

    # Missing penalty
    if missing_summary and "missing_before" in missing_summary:
        total_missing_percent = sum(missing_summary["missing_before"].values())
        missing_penalty = min(total_missing_percent, 30)
        score -= missing_penalty

    # Duplicate penalty
    if duplicate_summary and "duplicates_found" in duplicate_summary:
        duplicate_penalty = duplicate_summary["duplicates_found"] * 5
        score -= min(duplicate_penalty, 20)

    # Outlier penalty
    if outlier_summary and "total_outliers_removed" in outlier_summary:
        outlier_penalty = outlier_summary["total_outliers_removed"] * 5
        score -= min(outlier_penalty, 20)

    if score < 0:
        score = 0

    return round(score, 2)