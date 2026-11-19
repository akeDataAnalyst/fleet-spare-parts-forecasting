"""
Commercial Fleet Spare-Parts Demand Forecasting & Maintenance Trend Dashboard
Main Entry Point: Executive Overview
Author: Aklilu Abera Dana | Supply Chain Data Analyst
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils import configure_page, load_processed_datasets, render_sidebar_footer

configure_page(title="Executive Overview", icon="")

# Load processed pipeline outputs
data = load_processed_datasets()
risk_df = data["risk_summary"]
forecasts_df = data["forecasts"]
monthly_veh_df = data["monthly_vehicle"]
monthly_part_df = data["monthly_part"]

# ---------------------------------------------------------------------------
# Sidebar Filters
# ---------------------------------------------------------------------------
st.sidebar.header("Global Filters")
categories = ["All Categories"] + sorted(risk_df["category"].unique().tolist())
selected_category = st.sidebar.selectbox("Part Category", categories)

patterns = ["All Patterns"] + sorted(risk_df["demand_pattern"].unique().tolist())
selected_pattern = st.sidebar.selectbox("Demand Pattern", patterns)

render_sidebar_footer()

# Apply filters to risk/part summary
filtered_risk = risk_df.copy()
if selected_category != "All Categories":
    filtered_risk = filtered_risk[filtered_risk["category"] == selected_category]
if selected_pattern != "All Patterns":
    filtered_risk = filtered_risk[filtered_risk["demand_pattern"] == selected_pattern]

valid_parts = filtered_risk["part_number"].unique()
filtered_forecasts = forecasts_df[forecasts_df["part_number"].isin(valid_parts)]
filtered_monthly_part = monthly_part_df[monthly_part_df["part_number"].isin(valid_parts)]

# ---------------------------------------------------------------------------
# Header & Executive KPI Cards
# ---------------------------------------------------------------------------
st.title("Commercial Fleet Spare-Parts Demand Forecasting")
st.markdown(
    "Executive demand outlook, champion forecast accuracy, and maintenance risk prioritization "
    "across UAE commercial fleet operations."
)

# Compute Executive KPIs
next_3m_units = filtered_risk["forecast_next_3m_qty"].sum()
next_6m_units = filtered_risk["forecast_next_6m_qty"].sum()
next_6m_spend = filtered_risk["forecast_next_6m_spend_aed"].sum()

median_wape = filtered_risk["wape_pct"].median() if not filtered_risk.empty else 0.0
median_accuracy = max(0.0, 100.0 - median_wape)
high_risk_count = int(
    filtered_risk["risk_tier"].isin(["Critical Risk", "High Risk"]).sum()
)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric(
    label="Next 3M Forecast Demand",
    value=f"{next_3m_units:,.0f} units",
    help="Projected spare-parts consumption over the next 3 months.",
)
col2.metric(
    label="Next 6M Forecast Demand",
    value=f"{next_6m_units:,.0f} units",
    help="Projected spare-parts consumption over the next 6 months.",
)
col3.metric(
    label="Next 6M Projected Spend",
    value=f"AED {next_6m_spend:,.0f}",
    help="Estimated material value of 6-month forecasted demand.",
)
col4.metric(
    label="Median Forecast Accuracy",
    value=f"{median_accuracy:.1f}%",
    delta=f"WAPE: {median_wape:.1f}% (Target <25%)",
    delta_color="normal" if median_wape <= 25 else "inverse",
)
col5.metric(
    label="High / Critical Risk Parts",
    value=f"{high_risk_count} / {len(filtered_risk)}",
    help="Parts flagged for rising demand, repeat failures, or high forecast error.",
)

st.markdown("---")

# ---------------------------------------------------------------------------
# Row 1: Fleet-Wide Historical vs. Forecasted Demand & Top Forecasted Parts
# ---------------------------------------------------------------------------
left_col, right_col = st.columns([1.25, 1])

with left_col:
    st.subheader("Fleet-Wide Monthly Demand & 6-Month Projection")
    agg_timeline = (
        filtered_forecasts.groupby(["month", "record_type"], as_index=False)
        .agg(
            actual_qty=("actual_qty", "sum"),
            forecast_qty=("forecast_qty", "sum"),
        )
        .sort_values("month")
    )

    fig_overview = go.Figure()
    hist_actual = agg_timeline[agg_timeline["record_type"].isin(["Historical", "Backtest"])]
    fig_overview.add_trace(
        go.Scatter(
            x=hist_actual["month"],
            y=hist_actual["actual_qty"],
            mode="lines+markers",
            name="Actual Consumption",
            line=dict(color="#1f77b4", width=2.5),
        )
    )

    backtest_agg = agg_timeline[agg_timeline["record_type"] == "Backtest"]
    fig_overview.add_trace(
        go.Scatter(
            x=backtest_agg["month"],
            y=backtest_agg["forecast_qty"],
            mode="lines+markers",
            name="6M Backtest Validation",
            line=dict(color="#ff7f0e", width=2.5, dash="dash"),
        )
    )

    future_agg = agg_timeline[agg_timeline["record_type"] == "Forecast"]
    fig_overview.add_trace(
        go.Scatter(
            x=future_agg["month"],
            y=future_agg["forecast_qty"],
            mode="lines+markers",
            name="6M Forward Forecast",
            line=dict(color="#2ca02c", width=3, dash="dot"),
        )
    )

    fig_overview.update_layout(
        xaxis_title="Month",
        yaxis_title="Total Units",
        height=390,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig_overview, use_container_width=True)

with right_col:
    st.subheader("Top 10 Parts by Next 6M Forecasted Volume")
    top_forecast_parts = filtered_risk.nlargest(10, "forecast_next_6m_qty").sort_values(
        "forecast_next_6m_qty", ascending=True
    )
    fig_top = px.bar(
        top_forecast_parts,
        x="forecast_next_6m_qty",
        y="part_name",
        color="recommended_action",
        orientation="h",
        labels={
            "forecast_next_6m_qty": "6M Forecast (Units)",
            "part_name": "",
            "recommended_action": "Action",
        },
        color_discrete_map={
            "Increase Stock": "#d62728",
            "Maintain Current Stock": "#2ca02c",
            "Reduce Stock": "#1f77b4",
            "Review Demand & Master Data": "#ff7f0e",
        },
        text_auto=".0f",
    )
    fig_top.update_layout(
        height=390,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig_top, use_container_width=True)

# ---------------------------------------------------------------------------
# Row 2: Vehicle-Type Demand Breakdown & Planning Action Summary
# ---------------------------------------------------------------------------
col_v, col_a = st.columns([1, 1])

with col_v:
    st.subheader("Historical Consumption by Vehicle Type")
    veh_df = monthly_veh_df.copy()
    if selected_category != "All Categories":
        veh_df = veh_df[veh_df["category"] == selected_category]

    veh_agg = (
        veh_df.groupby("vehicle_type", as_index=False)
        .agg(
            total_units=("demand_qty", "sum"),
            total_spend_aed=("total_cost_aed", "sum"),
        )
        .sort_values("total_units", ascending=False)
    )

    fig_veh = px.bar(
        veh_agg,
        x="vehicle_type",
        y="total_units",
        color="total_spend_aed",
        color_continuous_scale="Blues",
        labels={
            "vehicle_type": "Vehicle Class",
            "total_units": "36M Units Issued",
            "total_spend_aed": "Spend (AED)",
        },
        text_auto=True,
    )
    fig_veh.update_layout(
        height=360,
        template="plotly_white",
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(fig_veh, use_container_width=True)

with col_a:
    st.subheader("Replenishment Planning Action Summary")
    action_summary = (
        filtered_risk.groupby("recommended_action", as_index=False)
        .agg(
            Parts=("part_number", "count"),
            Next_3M_Units=("forecast_next_3m_qty", "sum"),
            Next_6M_Units=("forecast_next_6m_qty", "sum"),
            Next_6M_Spend_AED=("forecast_next_6m_spend_aed", "sum"),
        )
        .sort_values("Next_6M_Spend_AED", ascending=False)
    )
    action_summary["Next_6M_Spend_AED"] = action_summary["Next_6M_Spend_AED"].map(
        lambda x: f"AED {x:,.2f}"
    )
    st.dataframe(action_summary, use_container_width=True, hide_index=True)

    st.info(
        "**Navigation Guide:** Use the left sidebar to drill into **Demand Analysis**, "
        "**Forecast Explorer**, **Forecast Accuracy**, **Maintenance Trends**, and **Risk Alerts**."
    )