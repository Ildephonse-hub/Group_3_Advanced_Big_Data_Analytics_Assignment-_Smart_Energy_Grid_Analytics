
#AUCA Advanced Big Data Analytics
#Section 8.1.3 / 8.1.4

#Forecasting feature preparation.

#Forecasting rule:
    #At 00:00 CAT each day, forecast all 24 hours of that day.

#Configurations:

#A:
   # lag_24h

#B:
    #lag_24h
    #lag_48h

#C:
    #lag_24h
    #lag_48h
    #lag_168h

#All lag values are from the same region and corresponding
#hour on previous days.

#No information from the forecast day is used.


from pathlib import Path

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
# 2. READ DATA
# ============================================================

print("Reading hourly regional dataset...")

dataframe = pd.read_csv(
    INPUT_FILE
)


# ============================================================
# 3. RESTORE AFRICA/KIGALI TIMEZONE
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
#
# This is important because the lag calculations must happen
# within each region in chronological order.

dataframe = (
    dataframe
    .sort_values(
        ["region", "target_time"]
    )
    .reset_index(drop=True)
)


# ============================================================
# 5. CREATE LAG FEATURES
# ============================================================
#
# Each region has exactly one row per hour.
#
# Therefore:
#
# shift(24)  = previous day
# shift(48)  = two days earlier
# shift(168) = seven days earlier
#
# The grouping by region prevents one region from using
# another region's energy value.

dataframe["lag_24h"] = (
    dataframe
    .groupby("region")["observed_energy_kwh"]
    .shift(24)
)

dataframe["lag_48h"] = (
    dataframe
    .groupby("region")["observed_energy_kwh"]
    .shift(48)
)

dataframe["lag_168h"] = (
    dataframe
    .groupby("region")["observed_energy_kwh"]
    .shift(168)
)


# ============================================================
# 6. CREATE FORECAST ORIGIN
# ============================================================
#
# The forecast origin is midnight CAT at the beginning
# of the target day.

dataframe["forecast_origin"] = (
    dataframe["target_time"]
    .dt.normalize()
)


# ============================================================
# 7. CREATE SOURCE TIMESTAMPS
# ============================================================
#
# These columns tell us exactly where each predictor comes
# from in time.

dataframe["lag_24h_source_time"] = (
    dataframe["target_time"]
    - pd.Timedelta(hours=24)
)

dataframe["lag_48h_source_time"] = (
    dataframe["target_time"]
    - pd.Timedelta(hours=48)
)

dataframe["lag_168h_source_time"] = (
    dataframe["target_time"]
    - pd.Timedelta(hours=168)
)


# ============================================================
# 8. VERIFY INFORMATION-TIMING RULE
# ============================================================
#
# Every source timestamp must be earlier than the forecast
# origin.
#
# For example:
#
# target       = Sep 22 13:00
# origin       = Sep 22 00:00
# lag_24 source = Sep 21 13:00
#
# Sep 21 13:00 < Sep 22 00:00
#
# Therefore the feature is legally available.

dataframe["lag_24h_valid"] = (
    dataframe["lag_24h_source_time"]
    < dataframe["forecast_origin"]
)

dataframe["lag_48h_valid"] = (
    dataframe["lag_48h_source_time"]
    < dataframe["forecast_origin"]
)

dataframe["lag_168h_valid"] = (
    dataframe["lag_168h_source_time"]
    < dataframe["forecast_origin"]
)


# ============================================================
# 9. TRAINING PERIOD
# ============================================================

TRAIN_START = pd.Timestamp(
    "2026-09-01 00:00:00",
    tz="Africa/Kigali"
)

TRAIN_END = pd.Timestamp(
    "2026-09-15 00:00:00",
    tz="Africa/Kigali"
)


training = dataframe[
    (dataframe["target_time"] >= TRAIN_START)
    &
    (dataframe["target_time"] < TRAIN_END)
].copy()


# ============================================================
# 10. FUNCTION TO REPORT A CONFIGURATION
# ============================================================

def report_configuration(
    configuration_name,
    feature_columns
):
    """
    Report the number of training rows available for a
    particular feature configuration.

    A row is usable only if ALL features required by the
    configuration are present.
    """

    training_rows = len(training)

    # Keep only rows where every selected feature is available.
    usable = training.dropna(
        subset=feature_columns
    ).copy()

    retained_rows = len(usable)

    excluded_rows = (
        training_rows
        - retained_rows
    )

    earliest_target = (
        usable["target_time"].min()
    )

    print()
    print("------------------------------------------------------------")
    print(configuration_name)
    print("------------------------------------------------------------")

    print(
        "Features:",
        ", ".join(feature_columns)
    )

    print(
        "Lookback hours:",
        max(
            int(
                feature.replace("lag_", "")
                .replace("h", "")
            )
            for feature in feature_columns
        )
    )

    print(
        "Training rows before lookback:",
        training_rows
    )

    print(
        "Excluded rows:",
        excluded_rows
    )

    print(
        "Retained rows:",
        retained_rows
    )

    print(
        "Earliest usable target:",
        earliest_target
    )

    return usable


# ============================================================
# 11. CONFIGURATION A
# ============================================================

config_a = report_configuration(
    "CONFIGURATION A",
    [
        "lag_24h"
    ]
)


# ============================================================
# 12. CONFIGURATION B
# ============================================================

config_b = report_configuration(
    "CONFIGURATION B",
    [
        "lag_24h",
        "lag_48h"
    ]
)


# ============================================================
# 13. CONFIGURATION C
# ============================================================

config_c = report_configuration(
    "CONFIGURATION C",
    [
        "lag_24h",
        "lag_48h",
        "lag_168h"
    ]
)


# ============================================================
# 14. INFORMATION-TIMING VERIFICATION
# ============================================================
#
# Check every configuration's source timestamps.
#
# There should be ZERO invalid rows.

invalid_24h = dataframe[
    dataframe["lag_24h"].notna()
    &
    ~dataframe["lag_24h_valid"]
]

invalid_48h = dataframe[
    dataframe["lag_48h"].notna()
    &
    ~dataframe["lag_48h_valid"]
]

invalid_168h = dataframe[
    dataframe["lag_168h"].notna()
    &
    ~dataframe["lag_168h_valid"]
]


print()
print("============================================================")
print("             INFORMATION-TIMING CHECK")
print("============================================================")

print(
    "Invalid lag_24h sources:",
    len(invalid_24h)
)

print(
    "Invalid lag_48h sources:",
    len(invalid_48h)
)

print(
    "Invalid lag_168h sources:",
    len(invalid_168h)
)


# ============================================================
# 15. SHOW FEATURE EXAMPLES
# ============================================================

print()
print("============================================================")
print("                    FEATURE EXAMPLES")
print("============================================================")

example_columns = [
    "target_time",
    "region",
    "observed_energy_kwh",
    "lag_24h",
    "lag_48h",
    "lag_168h",
    "forecast_origin",
    "lag_24h_source_time",
    "lag_48h_source_time",
    "lag_168h_source_time"
]

print(
    config_c[
        example_columns
    ]
    .head(10)
    .to_string(index=False)
)


# ============================================================
# 16. VERIFY SAME TRAINING ROWS ACROSS CONFIGURATIONS
# ============================================================
#
# The assignment asks us to use the same usable training rows
# across model configurations when comparing models.
#
# Configuration C has the longest lookback, so it determines
# the common usable training period.

common_training = config_c.copy()


print()
print("============================================================")
print("                 COMMON TRAINING DATA")
print("============================================================")

print(
    "Common usable rows:",
    len(common_training)
)

print(
    "Earliest common target:",
    common_training["target_time"].min()
)

print(
    "Latest common target:",
    common_training["target_time"].max()
)


# ============================================================
# 17. SAVE FEATURE DATASETS
# ============================================================

config_a_file = (
    OUTPUT_DIR
    / "forecast_features_config_A.csv"
)

config_b_file = (
    OUTPUT_DIR
    / "forecast_features_config_B.csv"
)

config_c_file = (
    OUTPUT_DIR
    / "forecast_features_config_C.csv"
)

common_file = (
    OUTPUT_DIR
    / "forecast_common_training_features.csv"
)


config_a.to_csv(
    config_a_file,
    index=False
)

config_b.to_csv(
    config_b_file,
    index=False
)

config_c.to_csv(
    config_c_file,
    index=False
)

common_training.to_csv(
    common_file,
    index=False
)


# ============================================================
# 18. FINAL SUMMARY
# ============================================================

print()
print("============================================================")
print("                     FINAL SUMMARY")
print("============================================================")

print(
    "Configuration A rows:",
    len(config_a)
)

print(
    "Configuration B rows:",
    len(config_b)
)

print(
    "Configuration C rows:",
    len(config_c)
)

print(
    "Common training rows:",
    len(common_training)
)

print()
print("Files saved:")

print(config_a_file)
print(config_b_file)
print(config_c_file)
print(common_file)

print()
print("Forecast feature preparation completed successfully.")