"""
Synthetic Fleet Spare-Parts & Maintenance Data Generator
Author: Aklilu Abera Dana | Supply Chain Data Analyst
Period: Jan 2023 - Dec 2025 (36 Months)
"""

import os
import numpy as np
import pandas as pd


def generate_fleet_master(seed: int = 42) -> pd.DataFrame:
    """Generates a realistic commercial vehicle fleet master table."""
    rng = np.random.default_rng(seed)

    vehicle_specs = [
        ("Heavy-Duty Truck", "Mercedes-Benz Actros", 35),
        ("Medium-Duty Box Truck", "Isuzu NPR", 40),
        ("Delivery Van", "Toyota HiAce", 45),
        ("Refrigerated Chiller Truck", "Mitsubishi Fuso Canter", 20),
        ("Utility Pickup", "Toyota Hilux", 30),
    ]

    hubs = ["Jebel Ali Hub (Dubai)", "Mussafah Depot (Abu Dhabi)", "Sajaa Yard (Sharjah)"]
    records = []
    veh_idx = 1

    for v_type, model, count in vehicle_specs:
        for _ in range(count):
            records.append(
                {
                    "vehicle_id": f"VEH-{veh_idx:04d}",
                    "vehicle_type": v_type,
                    "vehicle_model": model,
                    "operating_hub": rng.choice(hubs, p=[0.45, 0.35, 0.20]),
                    "model_year": int(rng.integers(2018, 2025)),
                    "avg_monthly_km": int(
                        rng.normal(
                            8500 if "Heavy" in v_type else 5200,
                            800,
                        )
                    ),
                }
            )
            veh_idx += 1

    return pd.DataFrame(records)


def generate_parts_master() -> pd.DataFrame:
    """
    Creates 24 commercial fleet spare parts across 4 demand archetypes:
    Fast-Moving, Slow-Moving, Intermittent, and Lumpy, with UAE AED pricing.
    """
    parts_data = [
        # Fast-Moving (High PM linkage)
        ("PRT-001", "Heavy-Duty Engine Oil Filter", "Filters & Fluids", 65.0, "Al-Futtaim Auto Parts", 3, "Fast-Moving", "Medium", 0.85, "none", "none"),
        ("PRT-002", "Primary Fuel Water Separator Filter", "Filters & Fluids", 110.0, "Al-Futtaim Auto Parts", 4, "Fast-Moving", "High", 0.80, "none", "none"),
        ("PRT-003", "Engine Air Intake Filter Element", "Filters & Fluids", 145.0, "Gargash Commercial Supply", 5, "Fast-Moving", "Medium", 0.82, "summer", "none"),
        ("PRT-004", "Cabin & A/C Pollen Filter", "HVAC & Cooling", 75.0, "Jebel Ali Fleet Spares", 3, "Fast-Moving", "Low", 0.78, "summer", "none"),
        ("PRT-005", "Front Disc Brake Pad Set", "Braking System", 420.0, "Brembo Gulf Distributors", 7, "Fast-Moving", "High", 0.60, "none", "rising"),
        ("PRT-006", "Rear Brake Shoe & Lining Kit", "Braking System", 380.0, "Brembo Gulf Distributors", 7, "Fast-Moving", "High", 0.65, "none", "none"),

        # Slow-Moving (Steady low volume)
        ("PRT-007", "Heavy-Duty Wiper Blade Pair", "Body & Exterior", 55.0, "Jebel Ali Fleet Spares", 2, "Slow-Moving", "Low", 0.70, "winter", "none"),
        ("PRT-008", "Heated Side View Mirror Assembly", "Body & Exterior", 310.0, "Gargash Commercial Supply", 6, "Slow-Moving", "Medium", 0.25, "none", "none"),
        ("PRT-009", "LED Rear Combination Tail Lamp", "Electrical & Lighting", 190.0, "Jebel Ali Fleet Spares", 4, "Slow-Moving", "Medium", 0.30, "none", "none"),
        ("PRT-010", "Serpentine Drive Belt", "Engine & Drivetrain", 135.0, "Al-Futtaim Auto Parts", 5, "Slow-Moving", "High", 0.75, "summer", "none"),
        ("PRT-011", "Radiator Upper & Lower Hose Kit", "HVAC & Cooling", 210.0, "Gargash Commercial Supply", 6, "Slow-Moving", "High", 0.55, "summer", "none"),
        ("PRT-012", "Wheel Hub Oil Seal", "Suspension & Axles", 95.0, "SKF Middle East", 5, "Slow-Moving", "Medium", 0.60, "none", "none"),

        # Intermittent (Many zero-demand months, high corrective share)
        ("PRT-013", "12V/24V Heavy Commercial Alternator", "Electrical & Lighting", 1450.0, "Bosch Automotive ME", 14, "Intermittent", "High", 0.15, "summer", "none"),
        ("PRT-014", "Electronic Turbocharger Actuator", "Engine & Drivetrain", 2350.0, "Gargash Commercial Supply", 18, "Intermittent", "High", 0.10, "none", "repeat_failure"),
        ("PRT-015", "High-Torque Starter Motor", "Electrical & Lighting", 1180.0, "Bosch Automotive ME", 12, "Intermittent", "High", 0.12, "none", "none"),
        ("PRT-016", "A/C Compressor Assembly", "HVAC & Cooling", 1890.0, "Denso Gulf Trading", 15, "Intermittent", "High", 0.20, "summer", "rising"),
        ("PRT-017", "Air Suspension Solenoid Valve", "Suspension & Axles", 680.0, "WABCO Emirates", 10, "Intermittent", "Medium", 0.25, "none", "none"),
        ("PRT-018", "NOx Exhaust Gas Sensor", "Engine & Drivetrain", 920.0, "Bosch Automotive ME", 14, "Intermittent", "Medium", 0.20, "none", "repeat_failure"),

        # Lumpy (Occasional bulk orders / major overhauls)
        ("PRT-019", "315/80 R22.5 All-Position Radial Tyre", "Tyres & Wheels", 1320.0, "Bridgestone MEA", 10, "Lumpy", "High", 0.50, "summer", "none"),
        ("PRT-020", "245/70 R17.5 Light Commercial Tyre", "Tyres & Wheels", 640.0, "Bridgestone MEA", 7, "Lumpy", "High", 0.55, "summer", "none"),
        ("PRT-021", "Heavy-Duty 150Ah AGM Fleet Battery", "Electrical & Lighting", 780.0, "ACDelco Gulf", 5, "Lumpy", "High", 0.40, "summer", "rising"),
        ("PRT-022", "Complete Clutch Pressure Plate & Disc Kit", "Engine & Drivetrain", 2650.0, "ZF Services Middle East", 21, "Lumpy", "High", 0.30, "none", "none"),
        ("PRT-023", "Front Shock Absorber Strut Pair", "Suspension & Axles", 840.0, "ZF Services Middle East", 12, "Lumpy", "Medium", 0.45, "none", "none"),
        ("PRT-024", "Refrigeration Unit Evaporator Fan Motor", "HVAC & Cooling", 1120.0, "Thermo King Gulf", 16, "Lumpy", "High", 0.35, "summer", "repeat_failure"),
    ]

    columns = [
        "part_number",
        "part_name",
        "category",
        "unit_cost_aed",
        "supplier",
        "lead_time_days",
        "expected_pattern",
        "criticality",
        "pm_ratio",
        "seasonality_profile",
        "anomaly_flag",
    ]
    return pd.DataFrame(parts_data, columns=columns)


def generate_transactions_and_work_orders(
    fleet_df: pd.DataFrame,
    parts_df: pd.DataFrame,
    start_date: str = "2023-01-01",
    end_date: str = "2025-12-31",
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Simulates 36 months of maintenance work orders and spare-parts consumption
    aligned with real-world fleet failure & preventive maintenance behavior.
    """
    rng = np.random.default_rng(seed)
    months = pd.date_range(start=start_date, end=end_date, freq="MS")

    work_orders = []
    part_issues = []
    wo_counter = 10001
    issue_counter = 50001

    # Vehicle type consumption multipliers
    veh_type_weights = {
        "Heavy-Duty Truck": 0.34,
        "Medium-Duty Box Truck": 0.24,
        "Delivery Van": 0.20,
        "Refrigerated Chiller Truck": 0.12,
        "Utility Pickup": 0.10,
    }
    veh_types = list(veh_type_weights.keys())
    veh_probs = list(veh_type_weights.values())

    vehicles_by_type = {
        vt: fleet_df[fleet_df["vehicle_type"] == vt]["vehicle_id"].tolist()
        for vt in veh_types
    }

    for month_idx, month_start in enumerate(months):
        cal_month = month_start.month
        days_in_month = month_start.days_in_month

        for _, part in parts_df.iterrows():
            pattern = part["expected_pattern"]
            season = part["seasonality_profile"]
            anomaly = part["anomaly_flag"]

            # 1. Seasonal multiplier (UAE Peak Summer: May - Sep)
            season_mult = 1.0
            if season == "summer" and cal_month in [5, 6, 7, 8, 9]:
                season_mult = 1.45
            elif season == "winter" and cal_month in [12, 1, 2]:
                season_mult = 1.35

            # 2. Trend / Anomaly multiplier
            trend_mult = 1.0
            if anomaly == "rising":
                # +28% gradual growth over 36 months
                trend_mult = 1.0 + (0.28 * (month_idx / 35.0))
            elif anomaly == "repeat_failure" and month_idx >= 24:
                # Spike in year 3 due to batch defect / recurring failures
                trend_mult = 1.65

            # 3. Determine monthly event count & batch size based on demand archetype
            if pattern == "Fast-Moving":
                base_events = rng.poisson(lam=28 * season_mult * trend_mult)
                qty_range = (1, 3)
            elif pattern == "Slow-Moving":
                base_events = rng.poisson(lam=5 * season_mult * trend_mult)
                qty_range = (1, 2)
            elif pattern == "Intermittent":
                # ~65% zero-demand months
                if rng.random() < 0.35 * season_mult:
                    base_events = int(rng.integers(1, 4))
                else:
                    base_events = 0
                qty_range = (1, 2)
            else:  # Lumpy
                # ~55% zero-demand months, occasional bulk fleet replacements
                if rng.random() < 0.45 * season_mult:
                    base_events = int(rng.integers(1, 3))
                    qty_range = (4, 14)
                else:
                    base_events = 0
                    qty_range = (1, 2)

            for _ in range(base_events):
                # Chiller units consume evaporator fans heavily
                if part["part_number"] == "PRT-024":
                    chosen_vtype = "Refrigerated Chiller Truck"
                else:
                    chosen_vtype = rng.choice(veh_types, p=veh_probs)

                vehicle_id = rng.choice(vehicles_by_type[chosen_vtype])
                event_day = int(rng.integers(1, days_in_month + 1))
                event_date = month_start + pd.Timedelta(days=event_day - 1)

                is_pm = rng.random() < part["pm_ratio"]
                maint_type = "Preventive Maintenance" if is_pm else "Corrective Repair"

                # Repeat failure flag (higher if corrective & part has defect anomaly)
                is_repeat_failure = False
                if not is_pm:
                    fail_prob = 0.38 if anomaly == "repeat_failure" else 0.08
                    is_repeat_failure = bool(rng.random() < fail_prob)

                qty_issued = int(rng.integers(qty_range[0], qty_range[1] + 1))
                downtime_hrs = (
                    round(float(rng.uniform(1.5, 4.0)), 1)
                    if is_pm
                    else round(float(rng.uniform(4.0, 36.0)), 1)
                )

                wo_id = f"WO-{wo_counter}"
                wo_counter += 1

                work_orders.append(
                    {
                        "work_order_id": wo_id,
                        "work_order_date": event_date.strftime("%Y-%m-%d"),
                        "vehicle_id": vehicle_id,
                        "vehicle_type": chosen_vtype,
                        "maintenance_type": maint_type,
                        "is_repeat_failure": is_repeat_failure,
                        "downtime_hours": downtime_hrs,
                    }
                )

                part_issues.append(
                    {
                        "issue_id": f"ISS-{issue_counter}",
                        "issue_date": event_date.strftime("%Y-%m-%d"),
                        "work_order_id": wo_id,
                        "vehicle_id": vehicle_id,
                        "vehicle_type": chosen_vtype,
                        "part_number": part["part_number"],
                        "part_name": part["part_name"],
                        "category": part["category"],
                        "quantity_issued": qty_issued,
                        "unit_cost_aed": part["unit_cost_aed"],
                        "total_cost_aed": round(qty_issued * part["unit_cost_aed"], 2),
                        "maintenance_type": maint_type,
                        "is_repeat_failure": is_repeat_failure,
                    }
                )
                issue_counter += 1

    wo_df = pd.DataFrame(work_orders).sort_values("work_order_date").reset_index(drop=True)
    issues_df = pd.DataFrame(part_issues).sort_values("issue_date").reset_index(drop=True)
    return wo_df, issues_df


def build_and_save_dataset(output_dir: str = "data/raw", seed: int = 42) -> dict:
    """Runs full synthetic data generation pipeline and saves CSVs to data/raw."""
    os.makedirs(output_dir, exist_ok=True)

    fleet_df = generate_fleet_master(seed=seed)
    parts_df = generate_parts_master()
    wo_df, issues_df = generate_transactions_and_work_orders(
        fleet_df, parts_df, start_date="2023-01-01", end_date="2025-12-31", seed=seed
    )

    fleet_df.to_csv(os.path.join(output_dir, "fleet_master.csv"), index=False)
    parts_df.to_csv(os.path.join(output_dir, "parts_master.csv"), index=False)
    wo_df.to_csv(os.path.join(output_dir, "maintenance_work_orders.csv"), index=False)
    issues_df.to_csv(os.path.join(output_dir, "spare_parts_issues.csv"), index=False)

    return {
        "fleet": fleet_df,
        "parts": parts_df,
        "work_orders": wo_df,
        "issues": issues_df,
    }


if __name__ == "__main__":
    datasets = build_and_save_dataset()
    for name, df in datasets.items():
        print(f"Saved {name}: {df.shape[0]:,} rows x {df.shape[1]} columns")