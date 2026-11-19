"""
Page 4: Maintenance Work Orders, Reliability & Failure Trends
Author: Aklilu Abera Dana | Supply Chain Data Analyst
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from utils import configure_page, load_processed_datasets, load_raw_datasets, render_sidebar_footer

configure_page(title="Maintenance Trends", icon="")

# Load datasets
processed_data = load_processed_datasets()
raw_data = load_raw_datasets()

risk_df = processed_data["risk_summary"]
wo_full = raw_data["work_orders"]

# ---------------------------------------------------------------------------
# Sidebar Filters
# ---------------------------------------------------------------------------
st.sidebar.header("Maintenance Filters")
selected_veh_types = st.sidebar.multiselect(
    "Vehicle Classes",
    options=sorted(wo_full["vehicle_type"].unique()),
    default=sorted(wo_full["vehicle_type"].unique()),
)
render_sidebar_footer()

wo_filt = wo_full[wo_full["vehicle_type"].isin(selected_veh_types)].copy()

# ---------------------------------------------------------------------------
# Header & Executive KPIs
# ---------------------------------------------------------------------------
st.title("Maintenance Trends & Reliability Diagnostics")
st.markdown(
    "Analyze preventive maintenance (PM) versus corrective repair (CM) workloads, "
    "vehicle downtime hours, and repeat-failure components driving reactive replenishment."
)

total_wos = len(wo_filt)
pm_wos = len(wo_filt[wo_filt["maintenance_type"] == "Preventive Maintenance"])
cm_wos = len(wo_filt[wo_filt["maintenance_type"] == "Corrective Repair"])
pm_pct = (pm_wos / total_wos * 100) if total_wos > 0 else 0.0
cm_pct = (cm_wos / total_wos * 100) if total_wos > 0 else 0.0

repeat_fail_count = int(wo_filt["is_repeat_failure"].sum())
total_downtime = wo_filt["downtime_hours"].sum()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Work Orders", f"{total_wos:,}")
k2.metric("Preventive Maintenance", f"{pm_wos:,} ({pm_pct:.1f}%)")
k3.metric("Corrective Repairs", f"{cm_wos:,} ({cm_pct:.1f}%)")
k4.metric("Repeat Failure Events", f"{repeat_fail_count:,}", help="Work orders logged as recurring breakdowns.")
k5.metric("Total Vehicle Downtime", f"{total_downtime:,.1f} hrs")

st.markdown("---")

# ---------------------------------------------------------------------------
# Row 1: Monthly Work Orders (PM vs CM) & Downtime by Vehicle Type
# ---------------------------------------------------------------------------
c1, c2 = st.columns([1.25, 1])

with c1:
    st.subheader("Monthly Work Order Volume: Preventive vs. Corrective")
    wo_filt["month"] = pd.to_datetime(wo_filt["work_order_date"]).dt.to_period("M").dt.to_timestamp()
    monthly_wo = (
        wo_filt.groupby(["month", "maintenance_type"], as_index=False)
        .size()
        .rename(columns={"size": "work_order_count"})
    )

    fig_wo = px.bar(
        monthly_wo,
        x="month",
        y="work_order_count",
        color="maintenance_type",
        barmode="group",
        labels={"month": "Month", "work_order_count": "Work Orders", "maintenance_type": "Type"},
        color_discrete_map={"Preventive Maintenance": "#2ca02c", "Corrective Repair": "#d62728"},
    )
    fig_wo.update_layout(
        height=390,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig_wo, use_container_width=True)

with c2:
    st.subheader("Total Vehicle Downtime Hours by Vehicle Class")
    dt_agg = (
        wo_filt.groupby("vehicle_type", as_index=False)["downtime_hours"]
        .sum()
        .sort_values("downtime_hours", ascending=False)
    )
    fig_dt = px.bar(
        dt_agg,
        x="downtime_hours",
        y="vehicle_type",
        orientation="h",
        color="downtime_hours",
        color_continuous_scale="Reds",
        labels={"downtime_hours": "Downtime (Hours)", "vehicle_type": ""},
        text_auto=".0f",
    )
    fig_dt.update_layout(
        height=390,
        template="plotly_white",
        showlegend=False,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig_dt, use_container_width=True)

# ---------------------------------------------------------------------------
# Row 2: Top Repeat Failures & PM Demand Share Scatter
# ---------------------------------------------------------------------------
c3, c4 = st.columns([1, 1])

with c3:
    st.subheader("Top 10 Parts by Repeat Failures")
    top_repeat = risk_df.nlargest(10, "repeat_failure_count").sort_values(
        "repeat_failure_count", ascending=True
    )
    fig_rep = px.bar(
        top_repeat,
        x="repeat_failure_count",
        y="part_name",
        orientation="h",
        color="repeat_failure_rate_pct",
        color_continuous_scale="YlOrRd",
        labels={
            "repeat_failure_count": "Repeat Failures",
            "part_name": "",
            "repeat_failure_rate_pct": "Failure Rate (%)",
        },
        text_auto=".0f",
    )
    fig_rep.update_layout(
        height=400,
        template="plotly_white",
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig_rep, use_container_width=True)

with c4:
    st.subheader("Preventive Maintenance (PM) Demand Share by Part")
    fig_pm = px.scatter(
        risk_df,
        x="pm_demand_share_pct",
        y="total_demand_36m",
        color="demand_pattern",
        size="total_spend_aed",
        hover_name="part_name",
        hover_data=["part_number", "repeat_failure_rate_pct"],
        labels={
            "pm_demand_share_pct": "PM Demand Share (%)",
            "total_demand_36m": "36M Total Demand",
            "demand_pattern": "Pattern",
        },
    )
    fig_pm.add_vline(
        x=50.0, line_dash="dash", line_color="gray", annotation_text="50% PM / CM Split"
    )
    fig_pm.update_layout(
        height=400,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig_pm, use_container_width=True)

# ---------------------------------------------------------------------------
# Row 3: Maintenance & Reliability Scorecard Table
# ---------------------------------------------------------------------------
st.subheader("Maintenance & Reliability Scorecard")
maint_table_cols = [
    "part_number",
    "part_name",
    "category",
    "demand_pattern",
    "pm_demand_share_pct",
    "repeat_failure_count",
    "repeat_failure_rate_pct",
    "criticality",
    "recommended_action",
]
st.dataframe(
    risk_df[maint_table_cols].sort_values("repeat_failure_rate_pct", ascending=False),
    use_container_width=True,
    hide_index=True,
)