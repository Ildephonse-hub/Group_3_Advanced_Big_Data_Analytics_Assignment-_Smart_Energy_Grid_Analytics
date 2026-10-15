
#Section 8.3 - Evaluate the frozen regression model on the test period.

#The best configuration has already been selected using validation MAE.

#This script:
#1. Reads the validation comparison.
#2. Identifies the frozen best configuration.
#3. Rebuilds that model using the common training data.
#4. Creates test-period lag features.
#5. Generates exactly 1,680 test predictions.
#6. Calculates test MAE and RMSE.
#7. Saves predictions and overall results.


from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error


# ============================================================
# 1. PATHS
# ============================================================

BASE_DIR = Path(r"D:\smart_energy_grid_analytics\code")

FORECAST_DIR = BASE_DIR / "forecasting"

DATA_FILE = FORECAST_DIR / "forecast_region_hour_dataset.csv"

COMMON_FEATURE_FILE = (
    FORECAST_DIR / "forecast_common_training_features.csv"
)

VALIDATION_RESULTS_FILE = (
    FORECAST_DIR / "regression_validation_results.csv"
)

PREDICTIONS_FILE = (
    FORECAST_DIR / "frozen_regression_test_predictions.csv"
)

RESULT_FILE = (
    FORECAST_DIR / "frozen_regression_test_results.csv"
)


# ============================================================
# 2. TIME PERIODS
# ============================================================

TRAIN_START = pd.Timestamp(
    "2026-09-01 00:00:00",
    tz="Africa/Kigali"
)

TRAIN_END = pd.Timestamp(
    "2026-09-15 00:00:00",
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
# 3. AVAILABLE CONFIGURATIONS
# ============================================================

CONFIGURATIONS = {
    "A": ["lag_24h"],

    "B": [
        "lag_24h",
        "lag_48h",
        "lag_168h"
    ]
}


# ============================================================
# 4. MODEL SETTINGS
# ============================================================

N_ESTIMATORS = 200
RANDOM_STATE = 42


# ============================================================
# 5. LOAD VALIDATION RESULTS
# ============================================================

print("=" * 70)
print("LOADING FROZEN MODEL SELECTION")
print("=" * 70)

validation_results = pd.read_csv(
    VALIDATION_RESULTS_FILE
)

# The first row was sorted by lowest validation MAE
# in the previous script.
best_row = validation_results.sort_values(
    "validation_mae"
).iloc[0]

best_config = str(
    best_row["config_id"]
)

feature_columns = CONFIGURATIONS[best_config]

print(
    f"Frozen configuration: {best_config}"
)

print(
    "Features:",
    ", ".join(feature_columns)
)

print(
    f"Validation MAE: "
    f"{best_row['validation_mae']:.6f}"
)

print(
    f"Validation RMSE: "
    f"{best_row['validation_rmse']:.6f}"
)


# ============================================================
# 6. LOAD COMMON TRAINING FEATURES
# ============================================================

print("\n" + "=" * 70)
print("LOADING TRAINING DATA")
print("=" * 70)

train = pd.read_csv(
    COMMON_FEATURE_FILE
)

train["target_time"] = pd.to_datetime(
    train["target_time"],
    utc=True
).dt.tz_convert("Africa/Kigali")

train = train[
    (train["target_time"] >= TRAIN_START)
    & (train["target_time"] < TRAIN_END)
].copy()

train = train.dropna(
    subset=feature_columns + ["observed_energy_kwh"]
)

print(
    f"Training rows: {len(train):,}"
)

print(
    f"Training start: {train['target_time'].min()}"
)

print(
    f"Training end:   {train['target_time'].max()}"
)


# ============================================================
# 7. TRAIN THE FROZEN MODEL
# ============================================================

print("\n" + "=" * 70)
print("TRAINING FROZEN MODEL")
print("=" * 70)

X_train = train[feature_columns]

y_train = train["observed_energy_kwh"]

model = RandomForestRegressor(
    n_estimators=N_ESTIMATORS,
    random_state=RANDOM_STATE,
    n_jobs=-1
)

model.fit(
    X_train,
    y_train
)

print("Frozen model trained successfully.")


# ============================================================
# 8. LOAD COMPLETE DATASET
# ============================================================

print("\n" + "=" * 70)
print("CREATING TEST FEATURES")
print("=" * 70)

dataset = pd.read_csv(
    DATA_FILE
)

dataset["target_time"] = pd.to_datetime(
    dataset["target_time"],
    utc=True
).dt.tz_convert("Africa/Kigali")

dataset = dataset.sort_values(
    ["region", "target_time"]
).reset_index(drop=True)


# ============================================================
# 9. CREATE LAG FEATURES
# ============================================================

for lag_hours in [24, 48, 168]:

    dataset[f"lag_{lag_hours}h"] = (
        dataset
        .groupby("region")["observed_energy_kwh"]
        .shift(lag_hours)
    )


# ============================================================
# 10. SELECT TEST PERIOD
# ============================================================

test = dataset[
    (dataset["target_time"] >= TEST_START)
    & (dataset["target_time"] < TEST_END)
].copy()

print(
    f"Test rows: {len(test):,}"
)

print(
    f"Test start: {test['target_time'].min()}"
)

print(
    f"Test end:   {test['target_time'].max()}"
)


# ============================================================
# 11. VERIFY EXPECTED TEST SIZE
# ============================================================

expected_test_rows = 7 * 24 * 10

if len(test) != expected_test_rows:

    raise ValueError(
        f"Expected {expected_test_rows:,} test rows, "
        f"but found {len(test):,}."
    )

print(
    f"Expected test rows confirmed: "
    f"{expected_test_rows:,}"
)


# ============================================================
# 12. REMOVE ROWS WITH MISSING FEATURES
# ============================================================

test = test.dropna(
    subset=feature_columns
).copy()

if len(test) != expected_test_rows:

    raise ValueError(
        "Some test rows are missing required lag features. "
        "The assignment requires 1,680 test predictions."
    )


# ============================================================
# 13. GENERATE TEST PREDICTIONS
# ============================================================

print("\nGenerating test predictions...")

X_test = test[feature_columns]

test["prediction"] = model.predict(
    X_test
)


# ============================================================
# 14. CALCULATE ERRORS
# ============================================================

test["error"] = (
    test["prediction"]
    - test["observed_energy_kwh"]
)

test["absolute_error"] = (
    test["error"].abs()
)

test["squared_error"] = (
    test["error"] ** 2
)


# ============================================================
# 15. CALCULATE TEST METRICS
# ============================================================

test_mae = mean_absolute_error(
    test["observed_energy_kwh"],
    test["prediction"]
)

test_rmse = (
    mean_squared_error(
        test["observed_energy_kwh"],
        test["prediction"]
    )
    ** 0.5
)


# ============================================================
# 16. VERIFY PREDICTION COUNT
# ============================================================

prediction_count = len(test)

if prediction_count != 1680:

    raise ValueError(
        f"Expected 1,680 predictions, "
        f"but generated {prediction_count:,}."
    )


# ============================================================
# 17. DISPLAY FINAL TEST RESULTS
# ============================================================

print("\n" + "=" * 70)
print("FROZEN MODEL TEST RESULTS")
print("=" * 70)

print(
    f"Frozen configuration: {best_config}"
)

print(
    "Features:",
    ", ".join(feature_columns)
)

print(
    f"Training rows: {len(train):,}"
)

print(
    f"Test predictions: {prediction_count:,}"
)

print(
    f"Test MAE:  {test_mae:.6f}"
)

print(
    f"Test RMSE: {test_rmse:.6f}"
)


# ============================================================
# 18. SAVE PREDICTIONS
# ============================================================

prediction_columns = [
    "target_time",
    "region",
    "observed_energy_kwh",
    *feature_columns,
    "prediction",
    "error",
    "absolute_error",
    "squared_error"
]

test[
    prediction_columns
].to_csv(
    PREDICTIONS_FILE,
    index=False
)


# ============================================================
# 19. SAVE OVERALL RESULTS
# ============================================================

results = pd.DataFrame(
    [
        {
            "config_id": best_config,
            "features": ", ".join(feature_columns),
            "training_rows": len(train),
            "test_predictions": prediction_count,
            "validation_mae": best_row["validation_mae"],
            "validation_rmse": best_row["validation_rmse"],
            "test_mae": test_mae,
            "test_rmse": test_rmse
        }
    ]
)

results.to_csv(
    RESULT_FILE,
    index=False
)


# ============================================================
# 20. SHOW SAMPLE PREDICTIONS
# ============================================================

print("\n" + "=" * 70)
print("SAMPLE TEST PREDICTIONS")
print("=" * 70)

print(
    test[
        [
            "target_time",
            "region",
            "observed_energy_kwh",
            "prediction",
            "error",
            "absolute_error"
        ]
    ]
    .head(10)
    .to_string(index=False)
)


# ============================================================
# 21. OUTPUT FILES
# ============================================================

print("\n" + "=" * 70)
print("FILES SAVED")
print("=" * 70)

print(PREDICTIONS_FILE)
print(RESULT_FILE)

print("\nDone.")