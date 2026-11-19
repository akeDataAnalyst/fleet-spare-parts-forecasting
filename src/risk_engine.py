"""
Spare-Parts Risk Scoring & Planning Recommendation Engine
Author: Aklilu Abera Dana | Supply Chain Data Analyst
"""

import os
import numpy as np
import pandas as pd


def run_risk_pipeline(processed_dir: str = "data/processed") -> pd.DataFrame:
    """
    Combines demand classification metrics with champion forecast accuracy
    to flag high-risk parts and assign clear planning recommendations:
      - Increase Stock
      - Maintain Current Stock
      - Reduce Stock
      - Review Demand & Master Data
    """
    class_df = pd.read_csv(os.path.join(processed_dir, "part_demand_classification.csv"))
    comp_df = pd.read_csv(os.path.join(processed_dir, "model_comparison.csv"))
    forecasts_df = pd.read_csv(os.path.join(processed_dir, "part_forecasts.csv"))

    # Extract champion model metrics per part
    champions = comp_df[comp_df["is_champion"]][
        [
            "part_number",
            "champion_model",
            "mae",
            "wape_pct",
            "mape_pct",
            "forecast_accuracy_pct",
            "forecast_bias_pct",
        ]
    ]

    # Summarize next 3-month and 6-month forecasted demand & spend
    future_df = forecasts_df[forecasts_df["record_type"] == "Forecast"].sort_values(
        ["part_number", "month"]
    )
    forecast_summary = (
        future_df.groupby("part_number", as_index=False)
        .agg(
            forecast_next_3m_qty=("forecast_qty", lambda s: round(float(s.iloc[:3].sum()), 1)),
            forecast_next_6m_qty=("forecast_qty", lambda s: round(float(s.sum()), 1)),
            forecast_next_6m_spend_aed=("forecast_spend_aed", lambda s: round(float(s.sum()), 2)),
        )
    )

    df = class_df.merge(champions, on="part_number", how="left").merge(
        forecast_summary, on="part_number", how="left"
    )

    # -----------------------------------------------------------------------
    # Individual Operational Risk Flags
    # -----------------------------------------------------------------------
    df["flag_rising_demand"] = df["demand_growth_pct"] > 10.0
    df["flag_falling_demand"] = df["demand_growth_pct"] < -15.0
    df["flag_high_forecast_error"] = df["wape_pct"] > 25.0
    df["flag_repeat_failures"] = df["repeat_failure_rate_pct"] >= 15.0
    df["flag_high_cost_or_critical"] = (df["unit_cost_aed"] >= 1000.0) | (
        df["criticality"] == "High"
    )
    df["flag_intermittent"] = df["intermittency_rate_pct"] > 50.0

    # Composite Risk Score (0 to 100 scale for prioritization)
    score = (
        df["flag_rising_demand"].astype(int) * 25
        + df["flag_high_forecast_error"].astype(int) * 25
        + df["flag_repeat_failures"].astype(int) * 25
        + df["flag_high_cost_or_critical"].astype(int) * 15
        + df["flag_intermittent"].astype(int) * 10
    )
    df["risk_score"] = score

    def assign_risk_tier(s: int) -> str:
        if s >= 65:
            return "Critical Risk"
        elif s >= 40:
            return "High Risk"
        elif s >= 20:
            return "Moderate Risk"
        return "Low Risk"

    df["risk_tier"] = df["risk_score"].apply(assign_risk_tier)

    # -----------------------------------------------------------------------
    # Planning Recommendation Rules (Forecasting & Demand Insight Scope)
    # -----------------------------------------------------------------------
    def recommend_action(row: pd.Series) -> str:
        if row["flag_high_forecast_error"] and row["flag_intermittent"]:
            return "Review Demand & Master Data"
        if row["flag_rising_demand"] or row["flag_repeat_failures"]:
            return "Increase Stock"
        if row["flag_falling_demand"] and not row["flag_high_cost_or_critical"]:
            return "Reduce Stock"
        if row["flag_high_forecast_error"]:
            return "Review Demand & Master Data"
        return "Maintain Current Stock"

    df["recommended_action"] = df.apply(recommend_action, axis=1)

    # Human-readable list of active triggers
    def summarize_triggers(row: pd.Series) -> str:
        triggers = []
        if row["flag_rising_demand"]:
            triggers.append(f"Rising Demand (+{row['demand_growth_pct']}%)")
        if row["flag_repeat_failures"]:
            triggers.append(f"Repeat Failures ({row['repeat_failure_rate_pct']}%)")
        if row["flag_high_forecast_error"]:
            triggers.append(f"High WAPE ({row['wape_pct']}%)")
        if row["flag_intermittent"]:
            triggers.append(f"Intermittent ({row['intermittency_rate_pct']}% zero mos)")
        if row["flag_falling_demand"]:
            triggers.append(f"Falling Demand ({row['demand_growth_pct']}%)")
        return " | ".join(triggers) if triggers else "Stable Usage"

    df["risk_drivers"] = df.apply(summarize_triggers, axis=1)

    df = df.sort_values(["risk_score", "forecast_next_6m_spend_aed"], ascending=[False, False]).reset_index(drop=True)
    df.to_csv(os.path.join(processed_dir, "part_risk_summary.csv"), index=False)
    return df


if __name__ == "__main__":
    risk_df = run_risk_pipeline()
    print(risk_df[["part_number", "part_name", "risk_tier", "risk_score", "recommended_action", "risk_drivers"]].head(10))