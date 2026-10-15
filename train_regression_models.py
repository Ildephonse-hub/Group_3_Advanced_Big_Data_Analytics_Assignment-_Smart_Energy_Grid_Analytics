
#Section 8.3 - Train and compare Random Forest regression configurations.

#We train two configurations using the SAME common training rows:

    #Configuration A:
        #lag_24h

    #Configuration B:
        #lag_24h + lag_48h + lag_168h

#The validation period is used only to compare the configurations.

#After selecting the best configuration by validation MAE,
#we freeze that choice before using the test period.


from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error


# ============================================================
# 1. FILE LOCATIONS
# ============================================================

BASE_DIR = Path(r"D:\smart_energy_grid_analytics\code")

FORECAST_DIR = BASE_DIR / "forecasting"

DATA_FILE = FORECAST_DIR / "forecast_region_hour_dataset.csv"
FEATURE_FILE = FORECAST_DIR / "forecast_common_training_features.csv"

OUTPUT_DIR = FORECAST_DIR

VALIDATION_OUTPUT = OUTPUT_DIR / "regression_validation_results.csv"


# ============================================================
# 2. TIME PERIODS
# ============================================================

# Training period:
# September 1 through September 14.
TRAIN_START = pd.Timestamp(
    "2026-09-01 00:00:00",
    tz="Africa/Kigali"
)

TRAIN_END = pd.Timestamp(
    "2026-09-15 00:00:00",
    tz="Africa/Kigali"
)


# Validation period:
# September 15 through September 21.
VALIDATION_START = pd.Timestamp(
    "2026-09-15 00:00:00",
    tz="Africa/Kigali"
)

VALIDATION_END = pd.Timestamp(
    "2026-09-22 00:00:00",
    tz="Africa/Kigali"
)


# ============================================================
# 3. MODEL CONFIGURATIONS
# ============================================================

CONFIGURATIONS = {
    "A": {
        "features": [
            "lag_24h"
        ]
    },

    "B": {
        "features": [
            "lag_24h",
            "lag_48h",
            "lag_168h"
        ]
    }
}


# ============================================================
# 4. RANDOM FOREST SETTINGS
# ============================================================

# n_estimators = number of decision trees.
#
# More trees generally make the prediction more stable,
# although they require more computation.
#
# random_state makes the experiment reproducible.
MODEL_SETTINGS = {
    "n_estimators": 200,
    "random_state": 42,
    "n_jobs": -1
}


# ============================================================
# 5. LOAD THE COMMON TRAINING FEATURES
# ============================================================

print("=" * 70)
print("LOADING COMMON TRAINING FEATURES")
print("=" * 70)

features = pd.read_csv(FEATURE_FILE)

# Convert target_time into a timezone-aware CAT timestamp.
features["target_time"] = pd.to_datetime(
    features["target_time"],
    utc=True
).dt.tz_convert("Africa/Kigali")

print(f"Loaded rows: {len(features):,}")


# ============================================================
# 6. LOAD THE COMPLETE FORECAST DATASET
# ============================================================

print("\n" + "=" * 70)
print("LOADING COMPLETE FORECAST DATASET")
print("=" * 70)

dataset = pd.read_csv(DATA_FILE)

dataset["target_time"] = pd.to_datetime(
    dataset["target_time"],
    utc=True
).dt.tz_convert("Africa/Kigali")

dataset = dataset.sort_values(
    ["region", "target_time"]
).reset_index(drop=True)

print(f"Complete dataset rows: {len(dataset):,}")


# ============================================================
# 7. CREATE VALIDATION FEATURES
# ============================================================

print("\n" + "=" * 70)
print("CREATING VALIDATION FEATURES")
print("=" * 70)

# We calculate the lag values from the complete chronological
# dataset.
#
# This is important because the validation period needs
# previous-day and previous-week information.

for lag_hours in [24, 48, 168]:

    column_name = f"lag_{lag_hours}h"

    dataset[column_name] = (
        dataset
        .groupby("region")["observed_energy_kwh"]
        .shift(lag_hours)
    )


# Select only validation-period rows.
validation = dataset[
    (dataset["target_time"] >= VALIDATION_START)
    & (dataset["target_time"] < VALIDATION_END)
].copy()


print(f"Validation rows: {len(validation):,}")

print(
    f"Validation start: "
    f"{validation['target_time'].min()}"
)

print(
    f"Validation end:   "
    f"{validation['target_time'].max()}"
)


# ============================================================
# 8. TRAIN AND VALIDATE EACH CONFIGURATION
# ============================================================

results = []

for config_id, config in CONFIGURATIONS.items():

    feature_columns = config["features"]

    print("\n" + "=" * 70)
    print(f"CONFIGURATION {config_id}")
    print("=" * 70)

    print(
        "Features:",
        ", ".join(feature_columns)
    )

    # --------------------------------------------------------
    # TRAINING DATA
    # --------------------------------------------------------

    train = features[
        (features["target_time"] >= TRAIN_START)
        & (features["target_time"] < TRAIN_END)
    ].copy()

    # The common training feature file already contains only
    # rows where all three possible lags are available.
    #
    # Therefore both configurations use exactly the same
    # 1,680 training rows.
    train = train.dropna(
        subset=feature_columns + ["observed_energy_kwh"]
    )

    # --------------------------------------------------------
    # VALIDATION DATA
    # --------------------------------------------------------

    valid = validation.dropna(
        subset=feature_columns + ["observed_energy_kwh"]
    ).copy()

    # --------------------------------------------------------
    # INPUT FEATURES
    # --------------------------------------------------------

    X_train = train[feature_columns]

    # observed_energy_kwh is the value we want the model
    # to learn to predict.
    y_train = train["observed_energy_kwh"]

    X_valid = valid[feature_columns]
    y_valid = valid["observed_energy_kwh"]

    print(f"Training rows:   {len(train):,}")
    print(f"Validation rows: {len(valid):,}")

    # --------------------------------------------------------
    # CREATE RANDOM FOREST
    # --------------------------------------------------------

    model = RandomForestRegressor(
        n_estimators=MODEL_SETTINGS["n_estimators"],
        random_state=MODEL_SETTINGS["random_state"],
        n_jobs=MODEL_SETTINGS["n_jobs"]
    )

    # --------------------------------------------------------
    # TRAIN
    # --------------------------------------------------------

    print("Training model...")

    model.fit(
        X_train,
        y_train
    )

    # --------------------------------------------------------
    # VALIDATION PREDICTIONS
    # --------------------------------------------------------

    predictions = model.predict(X_valid)

    # --------------------------------------------------------
    # VALIDATION METRICS
    # --------------------------------------------------------

    mae = mean_absolute_error(
        y_valid,
        predictions
    )

    rmse = mean_squared_error(
        y_valid,
        predictions
    ) ** 0.5

    print(f"Validation MAE:  {mae:.6f}")
    print(f"Validation RMSE: {rmse:.6f}")

    # --------------------------------------------------------
    # SAVE RESULT
    # --------------------------------------------------------

    results.append(
        {
            "config_id": config_id,
            "features": ", ".join(feature_columns),
            "n_estimators": MODEL_SETTINGS["n_estimators"],
            "random_state": MODEL_SETTINGS["random_state"],
            "training_rows": len(train),
            "validation_rows": len(valid),
            "validation_mae": mae,
            "validation_rmse": rmse
        }
    )


# ============================================================
# 9. CREATE COMPARISON TABLE
# ============================================================

results_df = pd.DataFrame(results)

# Lowest MAE is considered the best configuration.
results_df = results_df.sort_values(
    "validation_mae"
).reset_index(drop=True)

# Rank configurations.
results_df["rank_by_mae"] = range(
    1,
    len(results_df) + 1
)


# ============================================================
# 10. DISPLAY RESULTS
# ============================================================

print("\n" + "=" * 70)
print("VALIDATION COMPARISON")
print("=" * 70)

print(
    results_df[
        [
            "config_id",
            "features",
            "training_rows",
            "validation_rows",
            "validation_mae",
            "validation_rmse",
            "rank_by_mae"
        ]
    ].to_string(index=False)
)


# ============================================================
# 11. SELECT BEST CONFIGURATION
# ============================================================

best = results_df.iloc[0]

print("\n" + "=" * 70)
print("SELECTED CONFIGURATION")
print("=" * 70)

print(f"Best configuration: {best['config_id']}")
print(f"Features:           {best['features']}")
print(f"Validation MAE:     {best['validation_mae']:.6f}")
print(f"Validation RMSE:    {best['validation_rmse']:.6f}")

print(
    "\nSelection rule: lowest validation MAE."
)

print(
    "\nIMPORTANT: The selected configuration is now frozen."
)
print(
    "The test period must NOT be used to choose between models."
)


# ============================================================
# 12. SAVE VALIDATION RESULTS
# ============================================================

results_df.to_csv(
    VALIDATION_OUTPUT,
    index=False
)

print("\nSaved:")
print(VALIDATION_OUTPUT)

print("\nDone.")