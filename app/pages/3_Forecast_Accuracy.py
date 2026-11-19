"""
Page 3: Forecasting Accuracy & Algorithm Benchmarking
Author: Aklilu Abera Dana | Supply Chain Data Analyst
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import plotly.express as px
import streamlit as st
from utils import configure_page, load_processed_datasets, render_sidebar_footer

configure_page(title="Forecast Accuracy", icon="")

data = load_processed_datasets()
comp_df = data["model_comparison"]
risk_df = data["risk_summary"]

# Enrich model comparison with demand pattern & criticality
comp_enriched = comp_df.merge(
    risk_df[["part_number", "category", "demand_pattern", "intermittency_rate_pct", "total_spend_aed"]],
    on="part_number",
    how="left",
)

# ---------------------------------------------------------------------------
# Sidebar Filters
# ---------------------------------------------------------------------------
st.sidebar.header("Accuracy Filters")
selected_pattern = st.sidebar.selectbox(
    "Filter by Demand Pattern",
    ["All Patterns"] + sorted(risk_df["demand_pattern"].unique().tolist()),
)
render_sidebar_footer()

if selected_pattern != "All Patterns":
    comp_filt = comp_enriched[comp_enriched["demand_pattern"] == selected_pattern]
    risk_filt = risk_df[risk_df["demand_pattern"] == selected_pattern]
else:
    comp_filt = comp_enriched
    risk_filt = risk_df

# ---------------------------------------------------------------------------
# Header & Fleet-Wide Accuracy KPIs
# ---------------------------------------------------------------------------
st.title("Forecast Accuracy & Algorithm Benchmarking")
st.markdown(
    "Validate 6-month holdout backtest performance across **Moving Average**, "
    "**Simple Exponential Smoothing**, **Holt-Winters**, and **Croston's SBA Method**."
)

within_target = int((risk_filt["wape_pct"] <= 25.0).sum())
total_parts = len(risk_filt)
target_pct = (within_target / total_parts * 100) if total_parts > 0 else 0.0

k1, k2, k3, k4 = st.columns(4)
k1.metric(
    "Median Champion Accuracy",
    f"{risk_filt['forecast_accuracy_pct'].median():.1f}%",
    help="100% - Median WAPE across selected parts.",
)
k2.metric(
    "Median Champion WAPE",
    f"{risk_filt['wape_pct'].median():.1f}%",
    delta="Target: Below 25%",
    delta_color="normal" if risk_filt["wape_pct"].median() <= 25 else "inverse",
)
k3.metric(
    "Parts Meeting Target (<25% WAPE)",
    f"{within_target} / {total_parts} ({target_pct:.0f}%)",
)
k4.metric(
    "Median Forecast Bias",
    f"{risk_filt['forecast_bias_pct'].median():+.1f}%",
    help="Positive = over-forecasting; Negative = under-forecasting. Ideal is close to 0%.",
)

st.markdown("---")

# ---------------------------------------------------------------------------
# Row 1: Algorithm Benchmark Summary & Champion Wins by Demand Pattern
# ---------------------------------------------------------------------------
col1, col2 = st.columns([1.15, 1])

with col1:
    st.subheader("Algorithm Performance Comparison (Holdout Backtest)")
    algo_summary = (
        comp_filt.groupby("model_name", as_index=False)
        .agg(
            Median_WAPE_Pct=("wape_pct", "median"),
            Mean_WAPE_Pct=("wape_pct", "mean"),
            Median_MAE=("mae", "median"),
            Mean_Bias_Pct=("forecast_bias_pct", "mean"),
            Champion_Wins=("is_champion", "sum"),
        )
        .round(2)
        .sort_values("Median_WAPE_Pct")
    )
    st.dataframe(algo_summary, use_container_width=True, hide_index=True)

    st.info(
        "**Why WAPE over MAPE?** Spare-parts series contain frequent zero-demand months where "
        "standard MAPE divides by zero or explodes on single-unit orders. WAPE weights error by total volume."
    )

with col2:
    st.subheader("Champion Model Wins by Demand Pattern")
    champ_wins = (
        comp_enriched[comp_enriched["is_champion"]]
        .groupby(["demand_pattern", "model_name"], as_index=False)
        .size()
        .rename(columns={"size": "parts_won"})
    )
    fig_wins = px.bar(
        champ_wins,
        x="demand_pattern",
        y="parts_won",
        color="model_name",
        barmode="group",
        labels={
            "demand_pattern": "Demand Pattern",
            "parts_won": "Parts Selected",
            "model_name": "Champion Algorithm",
        },
        text_auto=True,
    )
    fig_wins.update_layout(
        height=350,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig_wins, use_container_width=True)

# ---------------------------------------------------------------------------
# Row 2: Intermittency vs. WAPE Scatter & Full Part Accuracy Scorecard
# ---------------------------------------------------------------------------
st.subheader("Forecast Error (WAPE %) vs. Intermittency Rate")
fig_scatter = px.scatter(
    risk_filt,
    x="intermittency_rate_pct",
    y="wape_pct",
    color="champion_model",
    size="total_spend_aed",
    hover_name="part_name",
    hover_data=["part_number", "demand_pattern", "mae", "forecast_bias_pct"],
    labels={
        "intermittency_rate_pct": "Intermittency Rate (% Zero-Demand Months)",
        "wape_pct": "Champion WAPE (%)",
        "champion_model": "Champion Model",
    },
)
fig_scatter.add_hline(
    y=25.0, line_dash="dash", line_color="red", annotation_text="25% WAPE Threshold"
)
fig_scatter.update_layout(height=390, template="plotly_white", margin=dict(l=10, r=10, t=20, b=10))
st.plotly_chart(fig_scatter, use_container_width=True)

st.subheader("Part-Level Champion Accuracy & Bias Scorecard")
scorecard_cols = [
    "part_number",
    "part_name",
    "demand_pattern",
    "intermittency_rate_pct",
    "champion_model",
    "wape_pct",
    "forecast_accuracy_pct",
    "mae",
    "mape_pct",
    "forecast_bias_pct",
]
st.dataframe(
    risk_filt[scorecard_cols].sort_values("wape_pct", ascending=True),
    use_container_width=True,
    hide_index=True,
)