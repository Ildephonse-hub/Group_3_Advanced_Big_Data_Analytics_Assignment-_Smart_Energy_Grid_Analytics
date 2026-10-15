
#Section 8.4 - Compare the previous-day baseline
#with the frozen Random Forest regression model.

#This script:
#1. Loads baseline predictions.
#2. Loads frozen Random Forest predictions.
#3. Compares overall MAE/RMSE.
#4. Compares MAE/RMSE by region.
#5. Calculates improvement.
#6. Finds the highest actual test hour for each region.
#7. Reports the prediction and absolute error at each peak.
#8. Saves comparison tables.
#9. Saves data for the actual-vs-predicted graph.


from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, mean_squared_error


# ============================================================
# 1. PATHS
# ============================================================

CODE_DIR = Path(
    r"D:\smart_energy_grid_analytics\code"
)

FORECAST_DIR = CODE_DIR / "forecasting"

BASELINE_FILE = (
    FORECAST_DIR
    / "previous_day_baseline_predictions.csv"
)

REGRESSION_FILE = (
    FORECAST_DIR
    / "frozen_regression_test_predictions.csv"
)

OVERALL_OUTPUT = (
    FORECAST_DIR
    / "forecast_model_comparison.csv"
)

REGION_OUTPUT = (
    FORECAST_DIR
    / "forecast_model_comparison_by_region.csv"
)

PEAK_OUTPUT = (
    FORECAST_DIR
    / "forecast_regional_peak_comparison.csv"
)

GRAPH_DATA_OUTPUT = (
    FORECAST_DIR
    / "forecast_actual_baseline_model_graph_data.csv"
)

GRAPH_OUTPUT = (
    FORECAST_DIR
    / "forecast_actual_baseline_model.png"
)


# ============================================================
# 2. LOAD BASELINE
# ============================================================

print("=" * 70)
print("LOADING PREVIOUS-DAY BASELINE")
print("=" * 70)

baseline = pd.read_csv(
    BASELINE_FILE
)

baseline["target_time"] = pd.to_datetime(
    baseline["target_time"],
    utc=True
).dt.tz_convert("Africa/Kigali")


print(
    f"Baseline rows: {len(baseline):,}"
)


# ============================================================
# 3. LOAD FROZEN RANDOM FOREST
# ============================================================

print("\n" + "=" * 70)
print("LOADING FROZEN RANDOM FOREST")
print("=" * 70)

model = pd.read_csv(
    REGRESSION_FILE
)

model["target_time"] = pd.to_datetime(
    model["target_time"],
    utc=True
).dt.tz_convert("Africa/Kigali")


print(
    f"Regression rows: {len(model):,}"
)


# ============================================================
# 4. CHECK EXPECTED TEST SIZE
# ============================================================

expected_rows = 7 * 24 * 10

if len(baseline) != expected_rows:

    raise ValueError(
        f"Baseline should contain {expected_rows:,} "
        f"rows, but contains {len(baseline):,}."
    )


if len(model) != expected_rows:

    raise ValueError(
        f"Regression should contain {expected_rows:,} "
        f"rows, but contains {len(model):,}."
    )


print(
    f"Expected 1,680 rows confirmed for both models."
)


# ============================================================
# 5. SELECT REQUIRED COLUMNS
# ============================================================

baseline = baseline[
    [
        "target_time",
        "region",
        "observed_energy_kwh",
        "baseline_prediction"
    ]
].copy()


model = model[
    [
        "target_time",
        "region",
        "observed_energy_kwh",
        "prediction"
    ]
].copy()


# ============================================================
# 6. RENAME REGRESSION PREDICTION
# ============================================================

model = model.rename(
    columns={
        "prediction": "model_prediction"
    }
)


# ============================================================
# 7. MERGE THE TWO MODELS
# ============================================================

comparison = pd.merge(
    baseline,
    model,
    on=[
        "target_time",
        "region",
        "observed_energy_kwh"
    ],
    how="inner"
)


if len(comparison) != expected_rows:

    raise ValueError(
        f"Expected {expected_rows:,} matched rows, "
        f"but found {len(comparison):,}."
    )


# ============================================================
# 8. CALCULATE ERRORS
# ============================================================

comparison["baseline_error"] = (
    comparison["baseline_prediction"]
    - comparison["observed_energy_kwh"]
)

comparison["baseline_absolute_error"] = (
    comparison["baseline_error"].abs()
)

comparison["baseline_squared_error"] = (
    comparison["baseline_error"] ** 2
)


comparison["model_error"] = (
    comparison["model_prediction"]
    - comparison["observed_energy_kwh"]
)

comparison["model_absolute_error"] = (
    comparison["model_error"].abs()
)

comparison["model_squared_error"] = (
    comparison["model_error"] ** 2
)


# ============================================================
# 9. OVERALL METRICS
# ============================================================

baseline_mae = mean_absolute_error(
    comparison["observed_energy_kwh"],
    comparison["baseline_prediction"]
)

baseline_rmse = (
    mean_squared_error(
        comparison["observed_energy_kwh"],
        comparison["baseline_prediction"]
    )
    ** 0.5
)


model_mae = mean_absolute_error(
    comparison["observed_energy_kwh"],
    comparison["model_prediction"]
)

model_rmse = (
    mean_squared_error(
        comparison["observed_energy_kwh"],
        comparison["model_prediction"]
    )
    ** 0.5
)


# ============================================================
# 10. CALCULATE IMPROVEMENT
# ============================================================

mae_improvement = (
    baseline_mae - model_mae
)

rmse_improvement = (
    baseline_rmse - model_rmse
)


mae_improvement_percent = (
    mae_improvement
    / baseline_mae
    * 100
)


rmse_improvement_percent = (
    rmse_improvement
    / baseline_rmse
    * 100
)


# ============================================================
# 11. DISPLAY OVERALL COMPARISON
# ============================================================

print("\n" + "=" * 70)
print("OVERALL FORECAST COMPARISON")
print("=" * 70)

print(
    f"Test predictions: {len(comparison):,}"
)

print("\nPrevious-day baseline:")
print(
    f"  MAE:  {baseline_mae:.6f}"
)
print(
    f"  RMSE: {baseline_rmse:.6f}"
)

print("\nFrozen Random Forest:")
print(
    f"  MAE:  {model_mae:.6f}"
)
print(
    f"  RMSE: {model_rmse:.6f}"
)

print("\nImprovement:")
print(
    f"  MAE improvement:  "
    f"{mae_improvement:.6f} "
    f"({mae_improvement_percent:.2f}%)"
)

print(
    f"  RMSE improvement: "
    f"{rmse_improvement:.6f} "
    f"({rmse_improvement_percent:.2f}%)"
)


# ============================================================
# 12. CREATE OVERALL RESULT TABLE
# ============================================================

overall_results = pd.DataFrame(
    [
        {
            "method": "Previous-day baseline",
            "test_predictions": len(comparison),
            "mae": baseline_mae,
            "rmse": baseline_rmse
        },
        {
            "method": "Frozen Random Forest",
            "test_predictions": len(comparison),
            "mae": model_mae,
            "rmse": model_rmse
        }
    ]
)

overall_results.to_csv(
    OVERALL_OUTPUT,
    index=False
)


# ============================================================
# 13. REGIONAL COMPARISON
# ============================================================

regional_results = []


for region, group in comparison.groupby(
    "region"
):

    region_baseline_mae = mean_absolute_error(
        group["observed_energy_kwh"],
        group["baseline_prediction"]
    )

    region_baseline_rmse = (
        mean_squared_error(
            group["observed_energy_kwh"],
            group["baseline_prediction"]
        )
        ** 0.5
    )

    region_model_mae = mean_absolute_error(
        group["observed_energy_kwh"],
        group["model_prediction"]
    )

    region_model_rmse = (
        mean_squared_error(
            group["observed_energy_kwh"],
            group["model_prediction"]
        )
        ** 0.5
    )

    regional_results.append(
        {
            "region": region,
            "test_predictions": len(group),

            "baseline_mae":
                region_baseline_mae,

            "baseline_rmse":
                region_baseline_rmse,

            "model_mae":
                region_model_mae,

            "model_rmse":
                region_model_rmse,

            "mae_improvement":
                region_baseline_mae
                - region_model_mae,

            "rmse_improvement":
                region_baseline_rmse
                - region_model_rmse
        }
    )


regional_df = pd.DataFrame(
    regional_results
).sort_values(
    "region"
)


# ============================================================
# 14. DISPLAY REGIONAL RESULTS
# ============================================================

print("\n" + "=" * 70)
print("REGIONAL COMPARISON")
print("=" * 70)

print(
    regional_df.to_string(
        index=False,
        float_format=lambda x: f"{x:.6f}"
    )
)


regional_df.to_csv(
    REGION_OUTPUT,
    index=False
)


# ============================================================
# 15. FIND HIGHEST ACTUAL HOUR FOR EACH REGION
# ============================================================

print("\n" + "=" * 70)
print("REGIONAL PEAK-HOUR COMPARISON")
print("=" * 70)


peak_rows = []


for region, group in comparison.groupby(
    "region"
):

    # Sort by:
    # 1. highest actual energy
    # 2. earliest timestamp if there is a tie
    peak = (
        group
        .sort_values(
            [
                "observed_energy_kwh",
                "target_time"
            ],
            ascending=[
                False,
                True
            ]
        )
        .iloc[0]
    )


    baseline_peak_error = (
        peak["baseline_prediction"]
        - peak["observed_energy_kwh"]
    )

    model_peak_error = (
        peak["model_prediction"]
        - peak["observed_energy_kwh"]
    )


    peak_rows.append(
        {
            "region": region,
            "peak_time": peak["target_time"],
            "actual_energy_kwh":
                peak["observed_energy_kwh"],

            "baseline_prediction":
                peak["baseline_prediction"],

            "baseline_absolute_error":
                abs(baseline_peak_error),

            "model_prediction":
                peak["model_prediction"],

            "model_absolute_error":
                abs(model_peak_error)
        }
    )


peak_df = pd.DataFrame(
    peak_rows
).sort_values(
    "region"
)


print(
    peak_df.to_string(
        index=False,
        float_format=lambda x: f"{x:.6f}"
    )
)


peak_df.to_csv(
    PEAK_OUTPUT,
    index=False
)


# ============================================================
# 16. PREPARE GRAPH DATA
# ============================================================

# For the required graph, use Region 1.
#
# We plot seven test days × 24 hours = 168 points.

graph_region = (
    comparison["region"]
    .sort_values()
    .unique()[0]
)

graph_data = comparison[
    comparison["region"] == graph_region
].copy()

graph_data = graph_data.sort_values(
    "target_time"
)


graph_data[
    [
        "target_time",
        "region",
        "observed_energy_kwh",
        "baseline_prediction",
        "model_prediction"
    ]
].to_csv(
    GRAPH_DATA_OUTPUT,
    index=False
)


# ============================================================
# 17. CREATE ACTUAL VS BASELINE VS MODEL GRAPH
# ============================================================

plt.figure(
    figsize=(14, 6)
)

plt.plot(
    graph_data["target_time"],
    graph_data["observed_energy_kwh"],
    label="Actual"
)

plt.plot(
    graph_data["target_time"],
    graph_data["baseline_prediction"],
    label="Previous-day baseline"
)

plt.plot(
    graph_data["target_time"],
    graph_data["model_prediction"],
    label="Random Forest"
)

plt.title(
    f"Actual vs Forecasts — {graph_region}"
)

plt.xlabel(
    "CAT time"
)

plt.ylabel(
    "Hourly energy (kWh)"
)

plt.legend()

plt.xticks(
    rotation=45
)

plt.tight_layout()

plt.savefig(
    GRAPH_OUTPUT,
    dpi=200
)

plt.close()


# ============================================================
# 18. FINAL CONCLUSION
# ============================================================

print("\n" + "=" * 70)
print("USEFULNESS CONCLUSION")
print("=" * 70)

if model_mae < baseline_mae:

    print(
        "The Random Forest improves MAE over "
        "the previous-day baseline."
    )

else:

    print(
        "The Random Forest does NOT improve MAE "
        "over the previous-day baseline."
    )


if model_rmse < baseline_rmse:

    print(
        "The Random Forest improves RMSE over "
        "the previous-day baseline."
    )

else:

    print(
        "The Random Forest does NOT improve RMSE "
        "over the previous-day baseline."
    )


# ============================================================
# 19. OUTPUT FILES
# ============================================================

print("\n" + "=" * 70)
print("FILES SAVED")
print("=" * 70)

print(OVERALL_OUTPUT)
print(REGION_OUTPUT)
print(PEAK_OUTPUT)
print(GRAPH_DATA_OUTPUT)
print(GRAPH_OUTPUT)

print("\nDone.")