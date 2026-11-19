"""
Page 1: Demand Analysis & Pattern Segmentation
Author: Aklilu Abera Dana | Supply Chain Data Analyst
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import plotly.express as px
import streamlit as st
from utils import configure_page, load_processed_datasets, render_sidebar_footer

configure_page(title="Demand Analysis", icon="")

data = load_processed_datasets()
monthly_part_df = data["monthly_part"]
monthly_veh_df = data["monthly_vehicle"]
class_df = data["classification"]

# ---------------------------------------------------------------------------
# Sidebar Filters
# ---------------------------------------------------------------------------
st.sidebar.header("Demand Filters")
selected_categories = st.sidebar.multiselect(
    "Part Categories",
    options=sorted(class_df["category"].unique()),
    default=sorted(class_df["category"].unique()),
)
selected_vehicles = st.sidebar.multiselect(
    "Vehicle Types",
    options=sorted(monthly_veh_df["vehicle_type"].unique()),
    default=sorted(monthly_veh_df["vehicle_type"].unique()),
)
render_sidebar_footer()

# Filter datasets
part_filt = class_df[class_df["category"].isin(selected_categories)]
monthly_part_filt = monthly_part_df[monthly_part_df["category"].isin(selected_categories)]
monthly_veh_filt = monthly_veh_df[
    (monthly_veh_df["category"].isin(selected_categories))
    & (monthly_veh_df["vehicle_type"].isin(selected_vehicles))
]

# ---------------------------------------------------------------------------
# Header & Top KPIs
# ---------------------------------------------------------------------------
st.title("Spare-Parts Demand Analysis & Segmentation")
st.markdown(
    "Identify where spare-parts consumption originates across categories, vehicle classes, "
    "seasonal cycles, and Syntetos-Boylan demand patterns."
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Active SKU Count", f"{len(part_filt)} parts")
col2.metric("36M Total Demand", f"{part_filt['total_demand_36m'].sum():,} units")
col3.metric("36M Total Spend", f"AED {part_filt['total_spend_aed'].sum():,.0f}")
col4.metric(
    "Avg Intermittency Rate",
    f"{part_filt['intermittency_rate_pct'].mean():.1f}%",
    help="Average percentage of zero-demand months across selected parts.",
)

st.markdown("---")

# ---------------------------------------------------------------------------
# Row 1: Monthly Consumption Trend by Category & Vehicle Type Share
# ---------------------------------------------------------------------------
c1, c2 = st.columns([1.3, 1])

with c1:
    st.subheader("Monthly Demand Trend by Part Category")
    cat_trend = (
        monthly_part_filt.groupby(["month", "category"], as_index=False)["demand_qty"].sum()
    )
    fig_cat_trend = px.line(
        cat_trend,
        x="month",
        y="demand_qty",
        color="category",
        markers=True,
        labels={"month": "Month", "demand_qty": "Units Issued", "category": "Category"},
    )
    fig_cat_trend.update_layout(
        height=390,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig_cat_trend, use_container_width=True)

with c2:
    st.subheader("Consumption by Vehicle Type & Category")
    veh_cat = (
        monthly_veh_filt.groupby(["vehicle_type", "category"], as_index=False)["demand_qty"].sum()
    )
    fig_veh_cat = px.bar(
        veh_cat,
        x="vehicle_type",
        y="demand_qty",
        color="category",
        labels={
            "vehicle_type": "Vehicle Class",
            "demand_qty": "Units Issued",
            "category": "Category",
        },
    )
    fig_veh_cat.update_layout(
        height=390,
        template="plotly_white",
        showlegend=False,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig_veh_cat, use_container_width=True)

# ---------------------------------------------------------------------------
# Row 2: Syntetos-Boylan Demand Matrix & Seasonality Heatmap
# ---------------------------------------------------------------------------
c3, c4 = st.columns([1.1, 1])

with c3:
    st.subheader("Syntetos-Boylan Demand Pattern Matrix (ADI vs. CV²)")
    fig_sb = px.scatter(
        part_filt,
        x="adi",
        y="cv2",
        color="demand_pattern",
        size="total_spend_aed",
        hover_name="part_name",
        hover_data=["part_number", "avg_monthly_demand", "intermittency_rate_pct"],
        labels={
            "adi": "Average Demand Interval (ADI)",
            "cv2": "Squared Coefficient of Variation (CV²)",
            "demand_pattern": "Demand Pattern",
        },
        color_discrete_map={
            "Fast-Moving": "#2ca02c",
            "Slow-Moving": "#1f77b4",
            "Intermittent": "#ff7f0e",
            "Lumpy": "#d62728",
        },
    )
    fig_sb.add_vline(x=1.32, line_dash="dash", line_color="gray")
    fig_sb.add_hline(y=0.49, line_dash="dash", line_color="gray")
    fig_sb.update_layout(
        height=400,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig_sb, use_container_width=True)

with c4:
    st.subheader("Calendar Seasonality Heatmap (Units by Month)")
    season_df = monthly_part_filt.copy()
    season_df["cal_month"] = season_df["month"].dt.strftime("%b")
    season_df["month_num"] = season_df["month"].dt.month

    pivot_season = (
        season_df.groupby(["category", "month_num", "cal_month"], as_index=False)["demand_qty"]
        .mean()
        .sort_values("month_num")
    )
    heatmap_matrix = pivot_season.pivot(
        index="category", columns="cal_month", values="demand_qty"
    )
    # Reorder columns chronologically Jan-Dec
    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    heatmap_matrix = heatmap_matrix[[m for m in month_order if m in heatmap_matrix.columns]]

    fig_heat = px.imshow(
        heatmap_matrix,
        aspect="auto",
        color_continuous_scale="YlOrRd",
        labels=dict(x="Calendar Month", y="Category", color="Avg Units"),
        text_auto=".0f",
    )
    fig_heat.update_layout(
        height=400,
        template="plotly_white",
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig_heat, use_container_width=True)

# ---------------------------------------------------------------------------
# Row 3: Part-Level Demand & Classification Table
# ---------------------------------------------------------------------------
st.subheader("Part-Level Demand & Classification Summary")
display_cols = [
    "part_number",
    "part_name",
    "category",
    "demand_pattern",
    "total_demand_36m",
    "avg_monthly_demand",
    "intermittency_rate_pct",
    "adi",
    "cv2",
    "demand_growth_pct",
    "total_spend_aed",
]
st.dataframe(
    part_filt[display_cols].sort_values("total_demand_36m", ascending=False),
    use_container_width=True,
    hide_index=True,
)