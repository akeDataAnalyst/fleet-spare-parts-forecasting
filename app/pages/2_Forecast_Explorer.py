"""
Page 2: Interactive Part-Level Forecast Explorer
Author: Aklilu Abera Dana | Supply Chain Data Analyst
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import plotly.graph_objects as go
import streamlit as st
from utils import configure_page, load_processed_datasets, render_sidebar_footer

configure_page(title="Forecast Explorer", icon="")

data = load_processed_datasets()
forecasts_df = data["forecasts"]
risk_df = data["risk_summary"]
comp_df = data["model_comparison"]

# ---------------------------------------------------------------------------
# Sidebar Part Selector
# ---------------------------------------------------------------------------
st.sidebar.header("Select Spare Part")

part_options = risk_df.sort_values("part_number").apply(
    lambda r: f"{r['part_number']} — {r['part_name']}", axis=1
).tolist()

selected_label = st.sidebar.selectbox("Spare Part", part_options)
selected_part_num = selected_label.split(" — ")[0]

render_sidebar_footer()

# Extract part metadata & time series
part_meta = risk_df[risk_df["part_number"] == selected_part_num].iloc[0]
part_ts = forecasts_df[forecasts_df["part_number"] == selected_part_num].sort_values("month")
part_models = comp_df[comp_df["part_number"] == selected_part_num].sort_values("wape_pct")

# ---------------------------------------------------------------------------
# Header & Part Metadata Banner
# ---------------------------------------------------------------------------
st.title(f"Forecast Explorer: {part_meta['part_name']}")
st.markdown(
    f"**Part Number:** `{part_meta['part_number']}` | **Category:** {part_meta['category']} | "
    f"**Demand Pattern:** `{part_meta['demand_pattern']}` | **Supplier:** {part_meta['supplier']} "
    f"(Lead Time: {part_meta['lead_time_days']} days)"
)

# KPI Cards for Selected Part
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Champion Model", part_meta["champion_model"])
k2.metric(
    "Forecast Accuracy",
    f"{part_meta['forecast_accuracy_pct']:.1f}%",
    delta=f"WAPE: {part_meta['wape_pct']:.1f}%",
    delta_color="normal" if part_meta["wape_pct"] <= 25 else "inverse",
)
k3.metric("Next 3M Forecast", f"{part_meta['forecast_next_3m_qty']:.1f} units")
k4.metric("Next 6M Forecast", f"{part_meta['forecast_next_6m_qty']:.1f} units")
k5.metric("Recommended Action", part_meta["recommended_action"])

st.markdown("---")

# ---------------------------------------------------------------------------
# Main Time-Series Chart: Historical + Backtest Validation + 6M Forward Forecast
# ---------------------------------------------------------------------------
st.subheader("Historical Actuals vs. Backtest Validation & 6-Month Projection")

fig = go.Figure()

actuals = part_ts[part_ts["record_type"].isin(["Historical", "Backtest"])]
fig.add_trace(
    go.Scatter(
        x=actuals["month"],
        y=actuals["actual_qty"],
        mode="lines+markers",
        name="Actual Demand (36M)",
        line=dict(color="#1f77b4", width=2.5),
        marker=dict(size=6),
    )
)

backtest = part_ts[part_ts["record_type"] == "Backtest"]
fig.add_trace(
    go.Scatter(
        x=backtest["month"],
        y=backtest["forecast_qty"],
        mode="lines+markers",
        name=f"Holdout Backtest ({part_meta['champion_model']})",
        line=dict(color="#ff7f0e", width=2.5, dash="dash"),
        marker=dict(size=7, symbol="diamond"),
    )
)

future = part_ts[part_ts["record_type"] == "Forecast"]
fig.add_trace(
    go.Scatter(
        x=future["month"],
        y=future["forecast_qty"],
        mode="lines+markers",
        name="6-Month Forward Forecast",
        line=dict(color="#2ca02c", width=3, dash="dot"),
        marker=dict(size=8, symbol="star"),
    )
)

fig.update_layout(
    xaxis_title="Month",
    yaxis_title="Quantity (Units)",
    height=430,
    template="plotly_white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=10, r=10, t=30, b=10),
)
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Bottom Row: 6-Month Forward Forecast Table & All-Models Comparison for Part
# ---------------------------------------------------------------------------
left_col, right_col = st.columns([1, 1])

with left_col:
    st.subheader("Next 6-Month Replenishment Forecast Schedule")
    sched_df = future[["month", "forecast_qty", "forecast_spend_aed", "selected_model"]].copy()
    sched_df["month"] = sched_df["month"].dt.strftime("%Y-%m")
    sched_df.columns = ["Forecast Month", "Projected Qty", "Projected Spend (AED)", "Model"]
    st.dataframe(sched_df, use_container_width=True, hide_index=True)

with right_col:
    st.subheader("All Candidate Models Evaluated for This Part")
    mod_table = part_models[
        ["model_name", "wape_pct", "mae", "mape_pct", "forecast_bias_pct", "is_champion"]
    ].copy()
    mod_table.columns = ["Algorithm", "WAPE (%)", "MAE", "Non-Zero MAPE (%)", "Bias (%)", "Selected"]
    st.dataframe(mod_table, use_container_width=True, hide_index=True)