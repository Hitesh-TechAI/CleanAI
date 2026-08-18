def format_execution_summary(action_name, summary):

    if not summary:
        return "• Operation completed."

    lines = []

    # -------------------------
    # HANDLE MISSING
    # -------------------------
    if action_name == "handle_missing":

        before = summary.get("missing_before", {})
        after = summary.get("missing_after", {})

        for col in before:
            if col in after:
                if before[col] > 0:
                    lines.append(
                        f"• '{col}' missing values reduced from {round(before[col],2)}% → {round(after[col],2)}%."
                    )

        dropped_cols = summary.get("dropped_columns", [])
        if dropped_cols:
            lines.append(f"• Dropped columns due to excessive missing values: {dropped_cols}")

        if not lines:
            lines.append("• Missing values handled successfully.")

    # -------------------------
    # HANDLE DUPLICATES
    # -------------------------
    elif action_name == "remove_duplicates":

        found = summary.get("duplicates_found", 0)
        removed = summary.get("duplicates_removed", 0)

        if removed > 0:
            lines.append(f"• Removed {removed} duplicate rows.")
        else:
            lines.append("• No duplicate rows found.")

    # -------------------------
    # HANDLE OUTLIERS
    # -------------------------
    elif action_name == "remove_outliers":

        total_removed = summary.get("total_outliers_removed", 0)

        if total_removed > 0:
            lines.append(f"• Removed {total_removed} rows containing outliers.")
        else:
            lines.append("• No significant outliers detected.")

    # -------------------------
    # HANDLE TYPES
    # -------------------------
    elif action_name == "handle_types":

        lines.append("• Text columns normalized.")
        lines.append("• Numeric conversion attempted.")
        lines.append("• Date format standardization attempted.")

    else:
        lines.append("• Operation completed.")

    return "\n".join(lines)