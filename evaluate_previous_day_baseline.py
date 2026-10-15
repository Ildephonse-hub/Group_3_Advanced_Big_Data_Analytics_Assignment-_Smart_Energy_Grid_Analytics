
#AUCA Advanced Big Data Analytics
#Section 8.2 - Previous-Day Baseline

#Forecasting rule:
    #At 00:00 CAT each day, forecast all 24 hours.

#Baseline:
    #Predict each target hour using the same region and same
    #hour from the previous day.

#Example:

    #Target:
        #2026-09-22 13:00, Region 1

    #Prediction:
        #2026-09-21 13:00, Region 1

#Test period:
    #September 22-28, 2026

#Expected predictions:
    #7 days × 24 hours × 10 regions = 1,680


from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# 1. FILE SETTINGS
# ============================================================

INPUT_FILE = Path(
    r"D:\smart_energy_grid_analytics\code\forecasting"
    r"\forecast_region_hour_dataset.csv"
)

OUTPUT_DIR = Path(
    r"D:\smart_energy_grid_analytics\code\forecasting"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 2. READ THE HOURLY DATASET
# ============================================================

print("Reading hourly regional dataset...")

dataframe = pd.read_csv(
    INPUT_FILE
)


# ============================================================
# 3. RESTORE AFRICA/KIGALI TIME
# ============================================================

dataframe["target_time"] = (
    pd.to_datetime(
        dataframe["target_time"],
        utc=True
    )
    .dt.tz_convert("Africa/Kigali")
)


# ============================================================
# 4. SORT BY REGION AND TIME
# ============================================================

dataframe = (
    dataframe
    .sort_values(
        ["region", "target_time"]
    )
    .reset_index(drop=True)
)


# ============================================================
# 5. CREATE PREVIOUS-DAY BASELINE
# ============================================================
#
# Each region has one observation per hour.
#
# Therefore shift(24) gives the value from exactly 24 hours
# earlier for the same region.
#
# Example:
#
# Sep 22 13:00
#     ↓ shift 24 hours
# Sep 21 13:00
#
# This is exactly the previous-day same-hour baseline.

dataframe["baseline_prediction"] = (
    dataframe
    .groupby("region")["observed_energy_kwh"]
    .shift(24)
)


# ============================================================
# 6. DEFINE THE TEST PERIOD
# ============================================================
#
# Test:
#
#     Sep 22 00:00 CAT
#     through
#     Sep 28 23:00 CAT
#
# End is exclusive.

TEST_START = pd.Timestamp(
    "2026-09-22 00:00:00",
    tz="Africa/Kigali"
)

TEST_END = pd.Timestamp(
    "2026-09-29 00:00:00",
    tz="Africa/Kigali"
)


test = dataframe[
    (dataframe["target_time"] >= TEST_START)
    &
    (dataframe["target_time"] < TEST_END)
].copy()


# ============================================================
# 7. CHECK FOR MISSING BASELINE VALUES
# ============================================================
#
# Every test hour should have a previous-day value because
# September 21 data exists.

missing_baseline = test[
    test["baseline_prediction"].isna()
]


print()
print("============================================================")
print("                 BASELINE DATA CHECK")
print("============================================================")

print(
    "Test rows:",
    len(test)
)

print(
    "Missing baseline predictions:",
    len(missing_baseline)
)


# ============================================================
# 8. KEEP ONLY USABLE PREDICTIONS
# ============================================================

test = test[
    test["baseline_prediction"].notna()
].copy()


# ============================================================
# 9. CALCULATE FORECAST ERROR
# ============================================================
#
# Error is:
#
#     prediction - actual
#
# Positive error:
#     model over-predicted.
#
# Negative error:
#     model under-predicted.

test["baseline_error"] = (
    test["baseline_prediction"]
    -
    test["observed_energy_kwh"]
)


# Absolute error ignores direction.

test["baseline_absolute_error"] = (
    test["baseline_error"]
    .abs()
)


# Squared error gives greater weight to large errors.

test["baseline_squared_error"] = (
    test["baseline_error"]
    ** 2
)


# ============================================================
# 10. CALCULATE MAE
# ============================================================

mae = (
    test["baseline_absolute_error"]
    .mean()
)


# ============================================================
# 11. CALCULATE RMSE
# ============================================================

rmse = np.sqrt(
    test["baseline_squared_error"]
    .mean()
)


# ============================================================
# 12. REPORT OVERALL RESULTS
# ============================================================

print()
print("============================================================")
print("             PREVIOUS-DAY BASELINE RESULTS")
print("============================================================")

print(
    "Prediction rows:",
    len(test)
)

print(
    "Expected predictions:",
    7 * 24 * 10
)

print(
    "MAE:",
    f"{mae:.6f}",
    "kWh"
)

print(
    "RMSE:",
    f"{rmse:.6f}",
    "kWh"
)


# ============================================================
# 13. CALCULATE RESULTS BY REGION
# ============================================================
#
# This is required later in Section 8.4.
#
# It is useful to calculate it now so that we can compare
# regions individually.

regional_results = (
    test
    .groupby("region")
    .agg(
        mae=(
            "baseline_absolute_error",
            "mean"
        ),
        rmse=(
            "baseline_squared_error",
            lambda values: np.sqrt(
                values.mean()
            )
        ),
        predictions=(
            "baseline_prediction",
            "count"
        )
    )
    .reset_index()
)


print()
print("============================================================")
print("               BASELINE RESULTS BY REGION")
print("============================================================")

print(
    regional_results
    .to_string(index=False)
)


# ============================================================
# 14. SHOW FIRST PREDICTIONS
# ============================================================

print()
print("============================================================")
print("                 SAMPLE PREDICTIONS")
print("============================================================")

sample_columns = [
    "target_time",
    "region",
    "baseline_prediction",
    "observed_energy_kwh",
    "baseline_error",
    "baseline_absolute_error"
]

print(
    test[
        sample_columns
    ]
    .head(20)
    .to_string(index=False)
)


# ============================================================
# 15. SAVE ALL BASELINE PREDICTIONS
# ============================================================

prediction_file = (
    OUTPUT_DIR
    / "previous_day_baseline_predictions.csv"
)

test[
    [
        "target_time",
        "region",
        "baseline_prediction",
        "observed_energy_kwh",
        "baseline_error",
        "baseline_absolute_error"
    ]
].to_csv(
    prediction_file,
    index=False
)


# ============================================================
# 16. SAVE REGIONAL RESULTS
# ============================================================

regional_file = (
    OUTPUT_DIR
    / "previous_day_baseline_by_region.csv"
)

regional_results.to_csv(
    regional_file,
    index=False
)


# ============================================================
# 17. FINAL SUMMARY
# ============================================================

print()
print("============================================================")
print("                    FINAL SUMMARY")
print("============================================================")

print(
    "Test predictions:",
    f"{len(test):,}"
)

print(
    "Expected:",
    f"{7 * 24 * 10:,}"
)

print(
    "MAE:",
    f"{mae:.6f}",
    "kWh"
)

print(
    "RMSE:",
    f"{rmse:.6f}",
    "kWh"
)

print()
print("Prediction file:")
print(prediction_file)

print()
print("Regional results:")
print(regional_file)

print()
print("Previous-day baseline evaluation completed.")