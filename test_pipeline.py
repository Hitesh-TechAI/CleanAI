import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from cleaning.missing import handle_missing
from cleaning.duplicates import remove_duplicates
from cleaning.outliers import remove_outliers
from cleaning.types import handle_types
from utils.quality_score import calculate_quality_score
from report.report_generator import generate_report



df = pd.read_csv("test_data.csv")

original_df = df.copy()

print("Original Data:")
print(df)

df, missing_summary = handle_missing(df)

df, type_summary = handle_types(df)

df, duplicate_summary = remove_duplicates(df)


df, outlier_summary = remove_outliers(df)

before_score = calculate_quality_score(
    original_df,
    missing_summary=missing_summary,
    duplicate_summary=duplicate_summary,
    outlier_summary=outlier_summary
)

after_score = calculate_quality_score(
    df,
    missing_summary={"missing_before": {"dummy": 0}},
    duplicate_summary={"duplicates_found": 0},
    outlier_summary={"total_outliers_removed": 0}
)

report = generate_report(
    missing_summary,
    duplicate_summary,
    outlier_summary,
    before_score,
    after_score
)

print("\n")
print(report)



print("\nDuplicate_ummary:")
print(duplicate_summary)

print("\nMissing Summary:")
print(missing_summary)

print("\nOutlier Summary:")
print(outlier_summary )

print("\nCleaned Data:")
print(df)

print("\nQuality Score Before Cleaning:", before_score)
print("Quality Score After Cleaning:", after_score)