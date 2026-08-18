def generate_report(missing_summary,
                    duplicate_summary,
                    outlier_summary,
                    before_score,
                    after_score):
    """
    Generate a human-readable cleaning report.
    """

    report_lines = []

    report_lines.append("📊 CLEANING REPORT")
    report_lines.append("-" * 40)

    # Missing
    if missing_summary and "missing_before" in missing_summary:
        total_missing = sum(missing_summary["missing_before"].values())
        report_lines.append(f"• Total missing percentage handled: {round(total_missing, 2)}%")

    # Duplicates
    if duplicate_summary and "duplicates_removed" in duplicate_summary:
        report_lines.append(f"• Duplicate rows removed: {duplicate_summary['duplicates_removed']}")

    # Outliers
    if outlier_summary and "total_outliers_removed" in outlier_summary:
        report_lines.append(f"• Outlier rows removed: {outlier_summary['total_outliers_removed']}")

    report_lines.append("-" * 40)

    # Quality Score
    report_lines.append(f"• Quality Score Before Cleaning: {before_score}")
    report_lines.append(f"• Quality Score After Cleaning: {after_score}")

    improvement = after_score - before_score
    report_lines.append(f"• Improvement: +{round(improvement, 2)}")

    report_lines.append("-" * 40)

    if after_score >= 90:
        report_lines.append("✅ Dataset quality is excellent after cleaning.")
    elif after_score >= 70:
        report_lines.append("⚠ Dataset quality improved but may need review.")
    else:
        report_lines.append("❌ Dataset quality is still low.")

    return "\n".join(report_lines)