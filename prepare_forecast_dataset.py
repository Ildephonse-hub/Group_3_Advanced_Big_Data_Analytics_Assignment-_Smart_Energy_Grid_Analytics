
#AUCA Advanced Big Data Analytics
#Section 8.1 - Forecasting Dataset Preparation

#This script:

#1. Reads cleaned hourly regional energy data from PostgreSQL.
#2. Creates one row for every CAT hour and region.
#3. Preserves the observed energy totals as forecasting targets.
#4. Reports reading completeness.
#5. Splits the data chronologically into:
      #- Training   : September 1-14, 2026
      #- Validation : September 15-21, 2026
      #- Test       : September 22-28, 2026
#6. Verifies that the three periods do not overlap.
#7. Saves the datasets as CSV files.

#IMPORTANT:
#- The data is NOT randomly shuffled.
#- Future observations must not enter the training data.
#- Missing readings are NOT replaced by zero.
#- The observed energy remains the evaluation target.


# ============================================================
# 1. IMPORT LIBRARIES
# ============================================================

from pathlib import Path

import pandas as pd
import psycopg


# ============================================================
# 2. DATABASE CONNECTION SETTINGS
# ============================================================

# PostgreSQL is running in Docker and exposed on localhost:5432.
DB_HOST = "localhost"
DB_PORT = 5432

# Database containing the Smart Energy Grid data.
DB_NAME = "smart_energy"

# PostgreSQL username.
DB_USER = "Ildephonse"

# Current PostgreSQL password.
#
# IMPORTANT:
# Do NOT commit this password to GitHub.
# Before final submission, replace this with an environment
# variable or another secure method.
DB_PASSWORD = "GrafanaTest2026"


# ============================================================
# 3. OUTPUT DIRECTORY
# ============================================================

# All forecasting datasets will be saved here.
OUTPUT_DIR = Path(
    r"D:\smart_energy_grid_analytics\code\forecasting"
)

# Create the directory if it does not already exist.
OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 4. SQL QUERY
# ============================================================
#
# We convert the 15-minute readings into hourly regional data.
#
# Each row produced by this query represents:
#
#     one CAT hour
#     +
#     one region
#
# For example:
#
#     2026-09-01 08:00 CAT
#     Region 1
#     421.52 kWh
#
# There are:
#
#     28 days
#     × 24 hours
#     × 10 regions
#     = 6,720 rows
#
# IMPORTANT:
# We use the CLEANED energy_readings table.
#
# The cleaned table contains one unique reading for each:
#
#     meter_id + event_time
#
# Therefore duplicate readings do not artificially increase
# the forecasting target.

SQL = """
SELECT
    time_bucket(
        '1 hour',
        e.event_time,
        'Africa/Kigali'
    ) AS target_time,

    m.region,

    SUM(e.energy_kwh) AS observed_energy_kwh,

    COUNT(*) AS reading_count

FROM energy_readings AS e

JOIN meters AS m
    ON e.meter_id = m.meter_id

WHERE e.event_time >=
      TIMESTAMPTZ '2026-09-01 00:00:00+02'

  AND e.event_time <
      TIMESTAMPTZ '2026-09-29 00:00:00+02'

GROUP BY
    target_time,
    m.region

ORDER BY
    target_time,
    m.region;
"""


# ============================================================
# 5. CONNECT TO POSTGRESQL
# ============================================================

print("Connecting to PostgreSQL...")

with psycopg.connect(
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
) as connection:

    print("Reading cleaned hourly regional data...")

    # pandas reads the SQL result directly into a DataFrame.
    dataframe = pd.read_sql(
        SQL,
        connection
    )


# ============================================================
# 6. CONVERT TIMESTAMPS TO AFRICA/KIGALI
# ============================================================
#
# PostgreSQL returns the timestamp with timezone information.
#
# We explicitly convert it to Africa/Kigali so that the
# forecasting dates are displayed in CAT.
#
# For example:
#
#     2026-08-31 22:00 UTC
#
# is the same instant as:
#
#     2026-09-01 00:00 CAT
#
# Keeping Africa/Kigali here makes the forecasting boundaries
# much easier to understand.

dataframe["target_time"] = (
    pd.to_datetime(
        dataframe["target_time"],
        utc=True
    )
    .dt.tz_convert("Africa/Kigali")
)


# ============================================================
# 7. SORT THE DATA CHRONOLOGICALLY
# ============================================================
#
# Forecasting depends on time order.
#
# We therefore sort:
#
#     first by target_time
#     then by region
#
# reset_index() gives the DataFrame a clean 0,1,2,3... index.

dataframe = (
    dataframe
    .sort_values(
        ["target_time", "region"]
    )
    .reset_index(drop=True)
)


# ============================================================
# 8. BASIC DATASET INFORMATION
# ============================================================

print()
print("============================================================")
print("                 DATASET PREPARATION")
print("============================================================")

print()
print(f"Rows: {len(dataframe):,}")

print(
    "Columns:",
    list(dataframe.columns)
)

print()
print("First 10 rows:")

print(
    dataframe
    .head(10)
    .to_string(index=False)
)

print()
print("Last 10 rows:")

print(
    dataframe
    .tail(10)
    .to_string(index=False)
)


# ============================================================
# 9. REGION CHECK
# ============================================================

print()
print("Regions:")

print(
    sorted(
        dataframe["region"].unique()
    )
)


# ============================================================
# 10. TIME RANGE CHECK
# ============================================================

print()
print("Earliest target hour:")

print(
    dataframe["target_time"].min()
)

print()
print("Latest target hour:")

print(
    dataframe["target_time"].max()
)


# ============================================================
# 11. DUPLICATE REGION-HOUR CHECK
# ============================================================
#
# There should be exactly one row for:
#
#     target_time + region
#
# If the same combination appeared twice, our hourly dataset
# would contain duplicate forecasting targets.

duplicate_count = dataframe.duplicated(
    subset=[
        "target_time",
        "region"
    ]
).sum()

print()
print(
    "Duplicate region-hour rows:",
    duplicate_count
)


# ============================================================
# 12. MISSING VALUE CHECK
# ============================================================

print()
print("Missing values:")

print(
    dataframe.isna().sum()
)


# ============================================================
# 13. READING COMPLETENESS
# ============================================================
#
# Each region contains 400 meters.
#
# Each meter normally produces:
#
#     4 readings per hour
#
# because readings occur every 15 minutes:
#
#     00
#     15
#     30
#     45
#
# Therefore a completely observed region-hour should contain:
#
#     400 × 4 = 1,600 readings
#
# However, the assignment deliberately contains missing readings.
#
# We DO NOT replace those missing readings with zero.
#
# Instead, we preserve the actual observed energy and report
# how many readings contributed to each hourly total.

EXPECTED_READINGS_PER_REGION_HOUR = 400 * 4


print()
print("Reading-count distribution:")

print(
    dataframe["reading_count"].describe()
)


# Find all region-hour combinations that have fewer than
# the expected 1,600 readings.

incomplete_hours = dataframe[
    dataframe["reading_count"]
    < EXPECTED_READINGS_PER_REGION_HOUR
]


print()

print(
    "Region-hour rows with fewer than 1,600 readings:",
    len(incomplete_hours)
)


print()
print("Examples of incomplete hours:")

if len(incomplete_hours) > 0:

    print(
        incomplete_hours
        .head(10)
        .to_string(index=False)
    )

else:

    print("None")


# ============================================================
# 14. EXPECTED DATASET SIZE
# ============================================================
#
# 28 days × 24 hours × 10 regions
#
# = 6,720 region-hour observations.

EXPECTED_ROWS = 28 * 24 * 10


print()
print("Expected rows:", EXPECTED_ROWS)


# ============================================================
# 15. CHRONOLOGICAL TRAIN / VALIDATION / TEST SPLIT
# ============================================================
#
# We MUST NOT randomly split time-series data.
#
# Instead:
#
# TRAINING
#     Sep 01 00:00
#     through
#     Sep 14 23:00
#
# VALIDATION
#     Sep 15 00:00
#     through
#     Sep 21 23:00
#
# TEST
#     Sep 22 00:00
#     through
#     Sep 28 23:00
#
# The end timestamp is EXCLUSIVE.
#
# This means:
#
# TRAIN_END = Sep 15 00:00
#
# so Sep 15 observations do NOT enter training.

TRAIN_START = pd.Timestamp(
    "2026-09-01 00:00:00",
    tz="Africa/Kigali"
)

TRAIN_END = pd.Timestamp(
    "2026-09-15 00:00:00",
    tz="Africa/Kigali"
)


VALIDATION_START = pd.Timestamp(
    "2026-09-15 00:00:00",
    tz="Africa/Kigali"
)

VALIDATION_END = pd.Timestamp(
    "2026-09-22 00:00:00",
    tz="Africa/Kigali"
)


TEST_START = pd.Timestamp(
    "2026-09-22 00:00:00",
    tz="Africa/Kigali"
)

TEST_END = pd.Timestamp(
    "2026-09-29 00:00:00",
    tz="Africa/Kigali"
)


# ============================================================
# 16. CREATE TRAINING DATASET
# ============================================================

train_df = dataframe[
    (dataframe["target_time"] >= TRAIN_START)
    &
    (dataframe["target_time"] < TRAIN_END)
].copy()


# ============================================================
# 17. CREATE VALIDATION DATASET
# ============================================================

validation_df = dataframe[
    (dataframe["target_time"] >= VALIDATION_START)
    &
    (dataframe["target_time"] < VALIDATION_END)
].copy()


# ============================================================
# 18. CREATE TEST DATASET
# ============================================================

test_df = dataframe[
    (dataframe["target_time"] >= TEST_START)
    &
    (dataframe["target_time"] < TEST_END)
].copy()


# ============================================================
# 19. REPORT TRAINING DATA
# ============================================================

print()
print("============================================================")
print("                  TRAINING DATA")
print("============================================================")

print(
    "Rows:",
    len(train_df)
)

print(
    "Earliest:",
    train_df["target_time"].min()
)

print(
    "Latest:",
    train_df["target_time"].max()
)

print(
    "Regions:",
    train_df["region"].nunique()
)

print(
    "Unique hourly timestamps:",
    train_df["target_time"].nunique()
)


# ============================================================
# 20. REPORT VALIDATION DATA
# ============================================================

print()
print("============================================================")
print("                 VALIDATION DATA")
print("============================================================")

print(
    "Rows:",
    len(validation_df)
)

print(
    "Earliest:",
    validation_df["target_time"].min()
)

print(
    "Latest:",
    validation_df["target_time"].max()
)

print(
    "Regions:",
    validation_df["region"].nunique()
)

print(
    "Unique hourly timestamps:",
    validation_df["target_time"].nunique()
)


# ============================================================
# 21. REPORT TEST DATA
# ============================================================

print()
print("============================================================")
print("                     TEST DATA")
print("============================================================")

print(
    "Rows:",
    len(test_df)
)

print(
    "Earliest:",
    test_df["target_time"].min()
)

print(
    "Latest:",
    test_df["target_time"].max()
)

print(
    "Regions:",
    test_df["region"].nunique()
)

print(
    "Unique hourly timestamps:",
    test_df["target_time"].nunique()
)


# ============================================================
# 22. CHECK TEMPORAL OVERLAP
# ============================================================
#
# We check whether the timestamps appearing in one dataset
# also appear in another dataset.
#
# Every result should be ZERO.

train_times = set(
    train_df["target_time"]
)

validation_times = set(
    validation_df["target_time"]
)

test_times = set(
    test_df["target_time"]
)


train_validation_overlap = (
    train_times
    .intersection(validation_times)
)

train_test_overlap = (
    train_times
    .intersection(test_times)
)

validation_test_overlap = (
    validation_times
    .intersection(test_times)
)


print()
print("============================================================")
print("                    OVERLAP CHECK")
print("============================================================")

print(
    "Train ∩ Validation:",
    len(train_validation_overlap)
)

print(
    "Train ∩ Test:",
    len(train_test_overlap)
)

print(
    "Validation ∩ Test:",
    len(validation_test_overlap)
)


# ============================================================
# 23. VERIFY EXPECTED SPLIT SIZES
# ============================================================
#
# Training:
#
#     14 days × 24 hours × 10 regions
#     = 3,360
#
# Validation:
#
#     7 × 24 × 10
#     = 1,680
#
# Test:
#
#     7 × 24 × 10
#     = 1,680
#
# Total:
#
#     3,360 + 1,680 + 1,680
#     = 6,720

EXPECTED_TRAIN_ROWS = 14 * 24 * 10
EXPECTED_VALIDATION_ROWS = 7 * 24 * 10
EXPECTED_TEST_ROWS = 7 * 24 * 10


print()
print("============================================================")
print("                   SPLIT SIZE CHECK")
print("============================================================")

print(
    "Expected training rows:",
    EXPECTED_TRAIN_ROWS
)

print(
    "Actual training rows:",
    len(train_df)
)

print(
    "Expected validation rows:",
    EXPECTED_VALIDATION_ROWS
)

print(
    "Actual validation rows:",
    len(validation_df)
)

print(
    "Expected test rows:",
    EXPECTED_TEST_ROWS
)

print(
    "Actual test rows:",
    len(test_df)
)


# ============================================================
# 24. SAVE THE COMPLETE HOURLY DATASET
# ============================================================

full_dataset_file = (
    OUTPUT_DIR
    / "forecast_region_hour_dataset.csv"
)

dataframe.to_csv(
    full_dataset_file,
    index=False
)


# ============================================================
# 25. SAVE TRAINING DATASET
# ============================================================

train_file = (
    OUTPUT_DIR
    / "forecast_train.csv"
)

train_df.to_csv(
    train_file,
    index=False
)


# ============================================================
# 26. SAVE VALIDATION DATASET
# ============================================================

validation_file = (
    OUTPUT_DIR
    / "forecast_validation.csv"
)

validation_df.to_csv(
    validation_file,
    index=False
)


# ============================================================
# 27. SAVE TEST DATASET
# ============================================================

test_file = (
    OUTPUT_DIR
    / "forecast_test.csv"
)

test_df.to_csv(
    test_file,
    index=False
)


# ============================================================
# 28. FINAL SUMMARY
# ============================================================

print()
print("============================================================")
print("                    FINAL SUMMARY")
print("============================================================")

print(
    "Full dataset rows:",
    f"{len(dataframe):,}"
)

print(
    "Expected full dataset rows:",
    f"{EXPECTED_ROWS:,}"
)

print(
    "Unique regions:",
    dataframe["region"].nunique()
)

print(
    "Unique hourly timestamps:",
    dataframe["target_time"].nunique()
)

print()
print("Training rows:", f"{len(train_df):,}")
print("Validation rows:", f"{len(validation_df):,}")
print("Test rows:", f"{len(test_df):,}")

print()
print("Saved files:")

print(
    full_dataset_file
)

print(
    train_file
)

print(
    validation_file
)

print(
    test_file
)

print()
print("Dataset preparation and chronological splitting completed.")