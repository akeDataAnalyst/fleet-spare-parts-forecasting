"""
Page 5: Risk Alerts & Actionable Replenishment Recommendations
Author: Aklilu Abera Dana | Supply Chain Data Analyst
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import plotly.express as px
import streamlit as st
from utils import configure_page, load_processed_datasets, render_sidebar_footer

configure_page(title="Risk Alerts & Recommendations", icon="")

data = load_processed_datasets()
risk_df = data["risk_summary"]

# ---------------------------------------------------------------------------
# Sidebar Filters
# ---------------------------------------------------------------------------
st.sidebar.header("Risk & Action Filters")
selected_tier = st.sidebar.selectbox(
    "Risk Tier",
    ["All Tiers", "Critical Risk", "High Risk", "Moderate Risk", "Low Risk"],
)
selected_action = st.sidebar.selectbox(
    "Recommended Action",
    [
        "All Actions",
        "Increase Stock",
        "Maintain Current Stock",
        "Reduce Stock",
        "Review Demand & Master Data",
    ],
)
selected_category = st.sidebar.selectbox(
    "Part Category",
    ["All Categories"] + sorted(risk_df["category"].unique().tolist()),
)
render_sidebar_footer()

risk_filt = risk_df.copy()
if selected_tier != "All Tiers":
    risk_filt = risk_filt[risk_filt["risk_tier"] == selected_tier]
if selected_action != "All Actions":
    risk_filt = risk_filt[risk_filt["recommended_action"] == selected_action]
if selected_category != "All Categories":
    risk_filt = risk_filt[risk_filt["category"] == selected_category]

# ---------------------------------------------------------------------------
# Header & Risk KPIs
# ---------------------------------------------------------------------------
st.title("Spare-Parts Risk Alerts & Replenishment Action Plan")
st.markdown(
    "Prioritize high-risk components exhibiting rising demand (>10% growth), high forecast error (WAPE >25%), "
    "repeat failures, or high unit cost/criticality to guide supply planning."
)

critical_count = int((risk_df["risk_tier"] == "Critical Risk").sum())
high_count = int((risk_df["risk_tier"] == "High Risk").sum())
increase_count = int((risk_df["recommended_action"] == "Increase Stock").sum())
review_count = int((risk_df["recommended_action"] == "Review Demand & Master Data").sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric(
    "Critical Risk SKUs",
    f"{critical_count} parts",
    delta="Immediate Priority",
    delta_color="inverse",
)
c2.metric("High Risk SKUs", f"{high_count} parts")
c3.metric("Action: Increase Stock", f"{increase_count} parts")
c4.metric("Action: Review Master Data", f"{review_count} parts")

st.markdown("---")

# ---------------------------------------------------------------------------
# Row 1: Risk Tier Donut & Top Risk Score Bar Chart (Yellow -> Red)
# ---------------------------------------------------------------------------
col1, col2 = st.columns([1, 1.3])

with col1:
    st.subheader("Fleet SKUs by Risk Tier")
    tier_order = ["Critical Risk", "High Risk", "Moderate Risk", "Low Risk"]
    tier_counts = (
        risk_df["risk_tier"]
        .value_counts()
        .reindex(tier_order, fill_value=0)
        .reset_index()
    )
    tier_counts.columns = ["Risk_Tier", "Count"]

    fig_tier = px.pie(
        tier_counts,
        names="Risk_Tier",
        values="Count",
        hole=0.45,
        color="Risk_Tier",
        color_discrete_map={
            "Critical Risk": "#d62728",
            "High Risk": "#ff7f0e",
            "Moderate Risk": "#ffd700",
            "Low Risk": "#2ca02c",
        },
    )
    fig_tier.update_traces(textposition="inside", textinfo="percent+label")
    fig_tier.update_layout(
        height=370,
        template="plotly_white",
        showlegend=False,
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(fig_tier, use_container_width=True)

with col2:
    st.subheader("Top 10 Highest-Risk Spare Parts (Composite Risk Score)")
    top_risk_parts = risk_df.nlargest(10, "risk_score").sort_values(
        "risk_score", ascending=True
    )
    fig_risk_bar = px.bar(
        top_risk_parts,
        x="risk_score",
        y="part_name",
        orientation="h",
        color="risk_score",
        color_continuous_scale="YlOrRd",
        range_color=[0, 100],
        labels={
            "risk_score": "Composite Risk Score (0–100)",
            "part_name": "",
        },
        text_auto=".0f",
    )
    fig_risk_bar.update_layout(
        height=370,
        template="plotly_white",
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(fig_risk_bar, use_container_width=True)

# ---------------------------------------------------------------------------
# Row 2: Replenishment Action & 6M Spend Summary
# ---------------------------------------------------------------------------
st.subheader("Replenishment Action & 6-Month Projected Spend Breakdown")
action_spend = (
    risk_df.groupby("recommended_action", as_index=False)
    .agg(
        SKUs=("part_number", "count"),
        Next_3M_Units=("forecast_next_3m_qty", "sum"),
        Next_6M_Units=("forecast_next_6m_qty", "sum"),
        Next_6M_Spend_AED=("forecast_next_6m_spend_aed", "sum"),
    )
    .sort_values("Next_6M_Spend_AED", ascending=False)
)
action_spend["Next_3M_Units"] = action_spend["Next_3M_Units"].round(1)
action_spend["Next_6M_Units"] = action_spend["Next_6M_Units"].round(1)
action_spend["Next_6M_Spend_AED"] = action_spend["Next_6M_Spend_AED"].map(
    lambda x: f"AED {x:,.2f}"
)
st.dataframe(action_spend, use_container_width=True, hide_index=True)

st.markdown("---")

# ---------------------------------------------------------------------------
# Row 3: Prioritized Risk & Action Table + CSV Export
# ---------------------------------------------------------------------------
header_col, btn_col = st.columns([3, 1])
with header_col:
    st.subheader(f"Prioritized Spare-Parts Risk Matrix ({len(risk_filt)} SKUs)")

table_cols = [
    "part_number",
    "part_name",
    "category",
    "demand_pattern",
    "risk_tier",
    "risk_score",
    "recommended_action",
    "forecast_next_3m_qty",
    "forecast_next_6m_qty",
    "forecast_next_6m_spend_aed",
    "wape_pct",
    "risk_drivers",
]

sorted_risk_filt = risk_filt[table_cols].sort_values(
    ["risk_score", "forecast_next_6m_spend_aed"], ascending=[False, False]
)

with btn_col:
    csv_export = sorted_risk_filt.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Export Action Plan (CSV)",
        data=csv_export,
        file_name="fleet_spare_parts_risk_action_plan.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.dataframe(
    sorted_risk_filt,
    use_container_width=True,
    hide_index=True,
)