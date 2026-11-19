# Commercial Fleet Spare-Parts Demand Forecasting & Maintenance Trend Dashboard
[![Live Demo](https://img.shields.io/badge/Streamlit-Live%20Demo-brightgreen)](https://fleet-spare-parts-forecasting-6ud6ak4kprbbmmjfeenwar.streamlit.app/)

## Description
An end-to-end supply chain analytics and demand forecasting platform built in Python (Jupyter Notebook) and Streamlit. Designed for commercial fleet and logistics operations in the UAE (AED currency, regional hubs, and peak summer heat seasonality), the system models 36 months of maintenance work orders and spare-parts consumption to segment SKUs, benchmark forecasting algorithms, diagnose repeat failures, and generate actionable replenishment priorities.

---

## Problem
Commercial fleet operators manage heterogeneous vehicle classes (heavy trucks, medium-duty trucks, light commercial vans, and buses) where spare-parts demand varies drastically between routine servicing and unexpected breakdowns:
* **Stockouts of critical components** (brake pads, filters, batteries, tyres, A/C compressors) extend vehicle downtime, disrupt delivery schedules, and trigger costly emergency spot-purchasing.
* **Overstocking intermittent or slow-moving parts** ties up working capital and warehouse space.
* **Single-model forecasting fails** across mixed demand profiles—standard smoothing methods distort sporadic parts with frequent zero-demand months, while reactive corrective repairs (CM) obscure baseline preventive maintenance (PM) consumption.

---

## Solution
The project implements a modular four-stage analytical pipeline feeding an interactive 6-page Streamlit executive dashboard:

1. **Fleet & CMMS Data Engineering (`src/data_generator.py` & `src/preprocessing.py`):**
   * Constructs a balanced 36-month (`24 SKUs × 36 Months`) consumption panel across UAE operating hubs, explicitly preserving zero-demand months.
   * Segments parts using the **Syntetos-Boylan Matrix** ($ADI$ vs. $CV^2$) into Fast-Moving, Slow-Moving, Intermittent, and Lumpy demand classes.
2. **Multi-Algorithm Forecasting & Holdout Backtesting (`src/forecasting.py`):**
   * Evaluates Moving Average (3M), Simple Exponential Smoothing (SES), Holt-Winters Seasonal Smoothing, and Croston’s Method (SBA bias-corrected) over a 6-month validation window.
   * Selects the lowest-**WAPE** champion algorithm per part and generates 3-month and 6-month forward demand and spend (AED) projections.
3. **Maintenance Reliability Diagnostics:**
   * Separates scheduled Preventive Maintenance (PM) from Corrective Repair (CM) demand and tracks vehicle downtime hours and repeat-failure rates per component.
4. **Composite Risk Scoring (`src/risk_engine.py`) & Interactive UI (`app/`):**
   * Flags high-risk SKUs exhibiting accelerating demand (`>10%` growth), elevated forecast error (`WAPE >25%`), or recurring mechanical failures across six interactive dashboard views (Executive Overview, Demand Analysis, Forecast Explorer, Forecast Accuracy, Maintenance Trends, and Risk Alerts).

---

## Tech Stack
* **Language:** Python
* **Data Processing & Numerical Modeling:** Pandas, NumPy, SciPy
* **Time-Series Forecasting & Statistics:** Statsmodels (Holt-Winters, SES), Custom Croston's SBA Engine
* **Interactive Visualization & Dashboarding:** Streamlit, Plotly
* **Development & Documentation:** Jupyter Notebook, Git, GitHub

---

## Recommendation
Based on pipeline diagnostics and backtest performance, fleet supply planners should execute the following actions:

* **Adopt Pattern-Specific Forecasting:** Deploy Holt-Winters Seasonal or SES for smooth, high-turnover consumables (filters, brake pads, lubricants) to capture UAE May–September heat surges, while standardizing on Croston’s SBA for intermittent and lumpy assemblies to prevent zero-bias understocking.
* **Increase Buffer Stock on High-Growth & Repeat-Failure SKUs:** Immediately raise safety stock targets for parts flagged under `Increase Stock` (demand growth `>10%` or repeat-failure rate `≥15%`), prioritizing high-criticality cooling, braking, and electrical components.
* **Audit Master Data & Vendor Quality on High-WAPE Items:** Route erratic, high-error components flagged under `Review Demand & Master Data` (`WAPE >25%`) to maintenance engineering to investigate root-cause installation defects or supplier batch quality issues rather than blindly inflating inventory buffers.
* **Next-Phase Roadmap:** Extend the forecasting output into a dynamic Inventory Optimization Engine incorporating supplier lead times, Reorder Points (ROP), Safety Stock formulas, and Economic Order Quantity (EOQ).

---

**Developed by Aklilu Abera Dana | Supply Chain Data Analyst**
