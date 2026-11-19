"""
Time-Series Forecasting & Model Benchmarking Engine
Author: Aklilu Abera Dana | Supply Chain Data Analyst
Models: Moving Average, Simple Exponential Smoothing, Holt-Winters, Croston's (SBA)
Metrics: WAPE, MAE, MAPE (non-zero), Forecast Bias
"""

import os
import warnings
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import SimpleExpSmoothing, ExponentialSmoothing

warnings.filterwarnings("ignore")


# ---------------------------------------------------------------------------
# 1. Forecasting Algorithms
# ---------------------------------------------------------------------------

def forecast_moving_average(train: np.ndarray, horizon: int = 6, window: int = 3) -> np.ndarray:
    """Simple Moving Average using the last `window` periods."""
    if len(train) == 0:
        return np.zeros(horizon)
    w = min(window, len(train))
    avg_val = float(np.mean(train[-w:]))
    return np.full(horizon, max(0.0, avg_val))


def forecast_ses(train: np.ndarray, horizon: int = 6) -> np.ndarray:
    """Simple Exponential Smoothing (optimized alpha)."""
    if np.all(train == 0) or len(train) < 3:
        return forecast_moving_average(train, horizon)
    try:
        model = SimpleExpSmoothing(train, initialization_method="estimated").fit(optimized=True)
        preds = model.forecast(horizon)
        return np.maximum(0.0, np.asarray(preds, dtype=float))
    except Exception:
        return forecast_moving_average(train, horizon)


def forecast_holt_winters(
    train: np.ndarray, horizon: int = 6, seasonal_periods: int = 12
) -> np.ndarray:
    """
    Additive Holt-Winters Exponential Smoothing for trend + 12-month seasonality.
    Falls back to damped trend or SES if series is too sparse for seasonal decomposition.
    """
    if len(train) < seasonal_periods * 2 or np.count_nonzero(train) < 12:
        return forecast_ses(train, horizon)
    try:
        model = ExponentialSmoothing(
            train,
            trend="add",
            seasonal="add",
            seasonal_periods=seasonal_periods,
            initialization_method="estimated",
        ).fit(optimized=True)
        preds = model.forecast(horizon)
        return np.maximum(0.0, np.asarray(preds, dtype=float))
    except Exception:
        return forecast_ses(train, horizon)


def forecast_croston_sba(
    train: np.ndarray, horizon: int = 6, alpha: float = 0.15
) -> np.ndarray:
    """
    Croston's Method with Syntetos-Boylan Approximation (SBA) bias correction.
    Separately smooths non-zero demand size (z) and inter-demand interval (p).
    Ideal for Intermittent and Lumpy spare parts.
    """
    n = len(train)
    non_zero_idx = np.where(train > 0)[0]

    if len(non_zero_idx) == 0:
        return np.zeros(horizon)
    if len(non_zero_idx) == 1:
        rate = float(train[non_zero_idx[0]]) / n
        return np.full(horizon, max(0.0, rate))

    # Initialize demand size (z) and interval (p) on first non-zero occurrence
    first_idx = non_zero_idx[0]
    z = float(train[first_idx])
    p = float(first_idx + 1)
    q = 1  # periods elapsed since last demand event

    for t in range(first_idx + 1, n):
        if train[t] > 0:
            z = alpha * float(train[t]) + (1.0 - alpha) * z
            p = alpha * float(q) + (1.0 - alpha) * p
            q = 1
        else:
            q += 1

    # SBA debiasing factor: (1 - alpha / 2)
    sba_forecast = (1.0 - alpha / 2.0) * (z / max(p, 1.0))
    return np.full(horizon, max(0.0, sba_forecast))


# ---------------------------------------------------------------------------
# 2. Accuracy & Bias Metrics
# ---------------------------------------------------------------------------

def evaluate_forecast_metrics(actual: np.ndarray, forecast: np.ndarray) -> dict[str, float]:
    """
    Computes MAE, WAPE, MAPE (over non-zero actuals), Forecast Accuracy (1 - WAPE),
    and Forecast Bias.
    """
    actual = np.asarray(actual, dtype=float)
    forecast = np.asarray(forecast, dtype=float)

    abs_errors = np.abs(actual - forecast)
    mae = float(np.mean(abs_errors))
    total_actual = float(np.sum(actual))

    if total_actual > 0:
        wape = float(np.sum(abs_errors) / total_actual) * 100.0
        bias = float(np.sum(forecast - actual) / total_actual) * 100.0
    else:
        wape = 0.0 if np.sum(forecast) == 0 else 100.0
        bias = 0.0 if np.sum(forecast) == 0 else 100.0

    # Non-zero MAPE (avoid division by zero on intermittent months)
    nz_mask = actual > 0
    if np.any(nz_mask):
        mape = float(np.mean(abs_errors[nz_mask] / actual[nz_mask])) * 100.0
    else:
        mape = np.nan

    forecast_accuracy = max(0.0, round(100.0 - wape, 2))

    return {
        "mae": round(mae, 2),
        "wape_pct": round(wape, 2),
        "mape_pct": round(mape, 2) if not np.isnan(mape) else np.nan,
        "forecast_accuracy_pct": forecast_accuracy,
        "forecast_bias_pct": round(bias, 2),
    }


# ---------------------------------------------------------------------------
# 3. Backtesting & Multi-Horizon Forecast Generation
# ---------------------------------------------------------------------------

MODEL_REGISTRY = {
    "Moving Average (3M)": forecast_moving_average,
    "Simple Exp Smoothing": forecast_ses,
    "Holt-Winters Seasonal": forecast_holt_winters,
    "Croston SBA": forecast_croston_sba,
}


def run_forecasting_pipeline(
    processed_dir: str = "data/processed",
    test_horizon: int = 6,
    forecast_horizon: int = 6,
) -> dict[str, pd.DataFrame]:
    """
    1. Splits 36-month history into Train (first 30M) and Test (last 6M).
    2. Benchmarks all 4 models per part using WAPE, MAE, MAPE, and Bias.
    3. Selects the lowest-WAPE champion model for each part.
    4. Refits the champion model on full 36-month history to forecast next 6 months.
    5. Saves model_comparison.csv and part_forecasts.csv to data/processed/.
    """
    panel_df = pd.read_csv(
        os.path.join(processed_dir, "monthly_part_demand.csv"),
        parse_dates=["month"],
    )
    class_df = pd.read_csv(os.path.join(processed_dir, "part_demand_classification.csv"))

    comparison_records = []
    forecast_records = []

    last_hist_month = panel_df["month"].max()
    future_months = pd.date_range(
        start=last_hist_month + pd.DateOffset(months=1),
        periods=forecast_horizon,
        freq="MS",
    )

    for part_num, grp in panel_df.groupby("part_number"):
        grp = grp.sort_values("month").reset_index(drop=True)
        series = grp["demand_qty"].values.astype(float)
        months = grp["month"].values
        part_name = grp["part_name"].iloc[0]
        unit_cost = float(grp["unit_cost_aed"].iloc[0])

        train_series = series[:-test_horizon]
        test_series = series[-test_horizon:]
        test_months = months[-test_horizon:]

        part_model_results = []
        test_preds_by_model = {}

        for model_name, model_fn in MODEL_REGISTRY.items():
            preds = model_fn(train_series, horizon=test_horizon)
            test_preds_by_model[model_name] = preds
            metrics = evaluate_forecast_metrics(test_series, preds)

            row = {
                "part_number": part_num,
                "part_name": part_name,
                "model_name": model_name,
                **metrics,
            }
            comparison_records.append(row)
            part_model_results.append(row)

        # Select champion model (lowest WAPE; tie-break by lowest MAE)
        best_model_row = sorted(
            part_model_results, key=lambda r: (r["wape_pct"], r["mae"])
        )[0]
        best_model_name = best_model_row["model_name"]
        best_model_fn = MODEL_REGISTRY[best_model_name]

        # Record historical + backtest rows for Forecast Explorer visualization
        best_test_preds = test_preds_by_model[best_model_name]
        for idx in range(len(series)):
            is_test = idx >= (len(series) - test_horizon)
            backtest_val = (
                round(float(best_test_preds[idx - (len(series) - test_horizon)]), 2)
                if is_test
                else np.nan
            )
            forecast_records.append(
                {
                    "part_number": part_num,
                    "part_name": part_name,
                    "month": pd.Timestamp(months[idx]),
                    "record_type": "Backtest" if is_test else "Historical",
                    "actual_qty": float(series[idx]),
                    "forecast_qty": backtest_val,
                    "forecast_spend_aed": (
                        round(backtest_val * unit_cost, 2)
                        if not np.isnan(backtest_val)
                        else np.nan
                    ),
                    "selected_model": best_model_name,
                    "model_wape_pct": best_model_row["wape_pct"],
                }
            )

        # Refit champion model on full 36 months for forward 6-month projection
        future_preds = best_model_fn(series, horizon=forecast_horizon)
        for f_month, f_val in zip(future_months, future_preds):
            f_clean = round(float(f_val), 2)
            forecast_records.append(
                {
                    "part_number": part_num,
                    "part_name": part_name,
                    "month": f_month,
                    "record_type": "Forecast",
                    "actual_qty": np.nan,
                    "forecast_qty": f_clean,
                    "forecast_spend_aed": round(f_clean * unit_cost, 2),
                    "selected_model": best_model_name,
                    "model_wape_pct": best_model_row["wape_pct"],
                }
            )

    comparison_df = pd.DataFrame(comparison_records)
    # Mark champion model per part
    best_models_map = (
        comparison_df.sort_values(["part_number", "wape_pct", "mae"])
        .groupby("part_number", as_index=False)
        .first()[["part_number", "model_name"]]
        .rename(columns={"model_name": "champion_model"})
    )
    comparison_df = comparison_df.merge(best_models_map, on="part_number", how="left")
    comparison_df["is_champion"] = comparison_df["model_name"] == comparison_df["champion_model"]

    forecasts_df = pd.DataFrame(forecast_records)

    # Save outputs to data/processed/
    comparison_df.to_csv(os.path.join(processed_dir, "model_comparison.csv"), index=False)
    forecasts_df.to_csv(os.path.join(processed_dir, "part_forecasts.csv"), index=False)

    return {
        "model_comparison": comparison_df,
        "part_forecasts": forecasts_df,
    }


if __name__ == "__main__":
    out = run_forecasting_pipeline()
    comp = out["model_comparison"]
    champions = comp[comp["is_champion"]]
    print("Champion Model Distribution Across 24 Spare Parts:")
    print(champions["model_name"].value_counts())
    print(f"\nFleet-Wide Median Champion WAPE: {champions['wape_pct'].median():.2f}%")
    print(f"Fleet-Wide Median Forecast Accuracy: {champions['forecast_accuracy_pct'].median():.2f}%")