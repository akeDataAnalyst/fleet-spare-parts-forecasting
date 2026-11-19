"""
Data Cleaning, Monthly Panel Construction & Demand Pattern Classification
Author: Aklilu Abera Dana | Supply Chain Data Analyst
"""

import os
import numpy as np
import pandas as pd


def load_raw_data(raw_dir: str = "data/raw") -> dict[str, pd.DataFrame]:
    """Loads raw CSV datasets from data/raw/."""
    return {
        "fleet": pd.read_csv(os.path.join(raw_dir, "fleet_master.csv")),
        "parts": pd.read_csv(os.path.join(raw_dir, "parts_master.csv")),
        "work_orders": pd.read_csv(
            os.path.join(raw_dir, "maintenance_work_orders.csv"),
            parse_dates=["work_order_date"],
        ),
        "issues": pd.read_csv(
            os.path.join(raw_dir, "spare_parts_issues.csv"),
            parse_dates=["issue_date"],
        ),
    }


def build_monthly_part_panel(
    issues_df: pd.DataFrame, parts_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Creates a complete balanced monthly panel (all parts x all months),
    filling months with zero transactions as 0 demand so time-series
    and intermittency metrics remain accurate.
    """
    df = issues_df.copy()
    df["month"] = df["issue_date"].dt.to_period("M").dt.to_timestamp()

    all_months = pd.date_range(
        start=df["month"].min(), end=df["month"].max(), freq="MS"
    )
    all_parts = parts_df["part_number"].unique()

    # Create full Cartesian grid (Part x Month)
    grid = pd.MultiIndex.from_product(
        [all_parts, all_months], names=["part_number", "month"]
    ).to_frame(index=False)

    # Aggregate actual monthly consumption & maintenance splits
    df["pm_qty"] = np.where(
        df["maintenance_type"] == "Preventive Maintenance", df["quantity_issued"], 0
    )
    df["cm_qty"] = np.where(
        df["maintenance_type"] == "Corrective Repair", df["quantity_issued"], 0
    )
    df["repeat_fail_events"] = df["is_repeat_failure"].astype(int)

    monthly_agg = (
        df.groupby(["part_number", "month"], as_index=False)
        .agg(
            demand_qty=("quantity_issued", "sum"),
            total_cost_aed=("total_cost_aed", "sum"),
            work_order_count=("work_order_id", "nunique"),
            pm_qty=("pm_qty", "sum"),
            cm_qty=("cm_qty", "sum"),
            repeat_fail_events=("repeat_fail_events", "sum"),
        )
    )

    panel = grid.merge(monthly_agg, on=["part_number", "month"], how="left")

    fill_cols = [
        "demand_qty",
        "total_cost_aed",
        "work_order_count",
        "pm_qty",
        "cm_qty",
        "repeat_fail_events",
    ]
    panel[fill_cols] = panel[fill_cols].fillna(0)
    panel["demand_qty"] = panel["demand_qty"].astype(int)
    panel["work_order_count"] = panel["work_order_count"].astype(int)
    panel["pm_qty"] = panel["pm_qty"].astype(int)
    panel["cm_qty"] = panel["cm_qty"].astype(int)
    panel["repeat_fail_events"] = panel["repeat_fail_events"].astype(int)

    # Merge master attributes
    panel = panel.merge(
        parts_df[
            [
                "part_number",
                "part_name",
                "category",
                "unit_cost_aed",
                "supplier",
                "lead_time_days",
                "criticality",
            ]
        ],
        on="part_number",
        how="left",
    )

    return panel.sort_values(["part_number", "month"]).reset_index(drop=True)


def build_monthly_vehicle_panel(issues_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregates monthly spare-parts consumption and spend by vehicle type."""
    df = issues_df.copy()
    df["month"] = df["issue_date"].dt.to_period("M").dt.to_timestamp()

    veh_monthly = (
        df.groupby(["month", "vehicle_type", "category"], as_index=False)
        .agg(
            demand_qty=("quantity_issued", "sum"),
            total_cost_aed=("total_cost_aed", "sum"),
            work_order_count=("work_order_id", "nunique"),
            repeat_fail_events=("is_repeat_failure", "sum"),
        )
        .sort_values(["month", "vehicle_type"])
        .reset_index(drop=True)
    )
    return veh_monthly


def classify_demand_patterns(panel_df: pd.DataFrame) -> pd.DataFrame:
    """
    Classifies each spare part using Syntetos-Boylan demand segmentation
    (ADI: Average Demand Interval & CV2: Squared Coefficient of Variation)
    and computes historical KPIs (Growth Rate, Intermittency Rate, PM Share).
    """
    summary_rows = []

    for part_num, grp in panel_df.groupby("part_number"):
        grp = grp.sort_values("month")
        demand = grp["demand_qty"].values
        total_months = len(demand)
        zero_months = int((demand == 0).sum())
        non_zero_demand = demand[demand > 0]

        total_demand = int(demand.sum())
        avg_monthly_demand = float(demand.mean())
        intermittency_rate = round((zero_months / total_months) * 100, 2)

        # Average Demand Interval (ADI)
        adi = total_months / len(non_zero_demand) if len(non_zero_demand) > 0 else np.inf

        # Squared Coefficient of Variation (CV^2) on non-zero demand periods
        if len(non_zero_demand) > 1 and non_zero_demand.mean() > 0:
            cv2 = (non_zero_demand.std(ddof=1) / non_zero_demand.mean()) ** 2
        else:
            cv2 = 0.0

        # Demand Pattern Classification (Syntetos-Boylan Matrix)
        if adi < 1.32 and cv2 < 0.49:
            # Distinguish Fast-Moving vs Slow-Moving by monthly volume threshold
            pattern = "Fast-Moving" if avg_monthly_demand >= 15 else "Slow-Moving"
        elif adi >= 1.32 and cv2 < 0.49:
            pattern = "Intermittent"
        elif adi >= 1.32 and cv2 >= 0.49:
            pattern = "Lumpy"
        else:
            # Smooth-but-erratic high-volume items
            pattern = "Lumpy" if cv2 >= 0.65 else "Fast-Moving"

        # Demand Growth Rate: Last 6 months vs Prior 6 months
        recent_6m = demand[-6:].sum()
        prev_6m = demand[-12:-6].sum()
        if prev_6m > 0:
            growth_rate_pct = round(((recent_6m - prev_6m) / prev_6m) * 100, 2)
        else:
            growth_rate_pct = 0.0

        # Maintenance KPIs
        pm_share_pct = (
            round((grp["pm_qty"].sum() / total_demand) * 100, 2)
            if total_demand > 0
            else 0.0
        )
        repeat_failures = int(grp["repeat_fail_events"].sum())
        total_wos = int(grp["work_order_count"].sum())
        repeat_failure_rate_pct = (
            round((repeat_failures / total_wos) * 100, 2) if total_wos > 0 else 0.0
        )

        meta = grp.iloc[0]
        summary_rows.append(
            {
                "part_number": part_num,
                "part_name": meta["part_name"],
                "category": meta["category"],
                "supplier": meta["supplier"],
                "lead_time_days": int(meta["lead_time_days"]),
                "unit_cost_aed": float(meta["unit_cost_aed"]),
                "criticality": meta["criticality"],
                "total_demand_36m": total_demand,
                "total_spend_aed": round(float(grp["total_cost_aed"].sum()), 2),
                "avg_monthly_demand": round(avg_monthly_demand, 2),
                "zero_demand_months": zero_months,
                "intermittency_rate_pct": intermittency_rate,
                "adi": round(adi, 2),
                "cv2": round(cv2, 2),
                "demand_pattern": pattern,
                "recent_6m_demand": int(recent_6m),
                "prev_6m_demand": int(prev_6m),
                "demand_growth_pct": growth_rate_pct,
                "pm_demand_share_pct": pm_share_pct,
                "repeat_failure_count": repeat_failures,
                "repeat_failure_rate_pct": repeat_failure_rate_pct,
            }
        )

    return (
        pd.DataFrame(summary_rows)
        .sort_values("total_demand_36m", ascending=False)
        .reset_index(drop=True)
    )


def run_preprocessing_pipeline(
    raw_dir: str = "data/raw", processed_dir: str = "data/processed"
) -> dict[str, pd.DataFrame]:
    """Executes full preprocessing and saves processed tables to data/processed/."""
    os.makedirs(processed_dir, exist_ok=True)
    raw = load_raw_data(raw_dir)

    monthly_part_panel = build_monthly_part_panel(raw["issues"], raw["parts"])
    monthly_vehicle_panel = build_monthly_vehicle_panel(raw["issues"])
    part_classification = classify_demand_patterns(monthly_part_panel)

    monthly_part_panel.to_csv(
        os.path.join(processed_dir, "monthly_part_demand.csv"), index=False
    )
    monthly_vehicle_panel.to_csv(
        os.path.join(processed_dir, "monthly_vehicle_demand.csv"), index=False
    )
    part_classification.to_csv(
        os.path.join(processed_dir, "part_demand_classification.csv"), index=False
    )

    return {
        "monthly_part_panel": monthly_part_panel,
        "monthly_vehicle_panel": monthly_vehicle_panel,
        "part_classification": part_classification,
    }


if __name__ == "__main__":
    results = run_preprocessing_pipeline()
    for name, df in results.items():
        print(f"Saved {name}: {df.shape[0]:,} rows x {df.shape[1]} columns")