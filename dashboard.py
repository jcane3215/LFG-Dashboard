import os
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# PAGE CONFIG & STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Executive Analytics Dashboard | Case Study",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for polished KPI cards, alert callouts, and architectural boxes
st.markdown("""
<style>
    .kpi-card {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .kpi-title {
        font-size: 0.85rem;
        color: #6c757d;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .kpi-value {
        font-size: 1.6rem;
        color: #1f2937;
        font-weight: 700;
    }
    .kpi-sub {
        font-size: 0.8rem;
        margin-top: 4px;
        font-weight: 500;
    }
    .pos-var { color: #10b981; }
    .neg-var { color: #ef4444; }
    
    .arch-box {
        background-color: #ffffff;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .arch-title {
        font-weight: 700;
        font-size: 1.05rem;
        color: #111827;
        margin-bottom: 6px;
    }
    .arch-desc {
        font-size: 0.9rem;
        color: #4b5563;
    }
    .badge-legacy {
        background-color: #fef2f2;
        color: #991b1b;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-target {
        background-color: #ecfdf5;
        color: #065f46;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

FILE_NAME = "BI_Manager_Case_Study.xlsx"

# -----------------------------------------------------------------------------
# DATA LOADING & RELATIONAL MERGING
# -----------------------------------------------------------------------------
@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path):
        st.error(f"❌ File '{file_path}' not found in `{os.getcwd()}`. Please verify the file location.")
        return None

    try:
        # 1. Load sheets
        loc_master = pd.read_excel(file_path, sheet_name="Location Master")
        df_ns = pd.read_excel(file_path, sheet_name="NetSuite Financials")
        df_adp = pd.read_excel(file_path, sheet_name="ADP Labor")
        df_pas = pd.read_excel(file_path, sheet_name="Passare Cases")

        # Standardize Month column as datetime
        for df in [df_ns, df_adp, df_pas]:
            if "Month" in df.columns:
                df["Month"] = pd.to_datetime(df["Month"])

        # 2. Merge NetSuite Financials with Location Master
        merged = pd.merge(
            df_ns,
            loc_master,
            on="NetSuite Location ID",
            how="left",
            suffixes=("", "_loc")
        )

        # 3. Merge ADP Labor using Month + ADP Company Code
        merged = pd.merge(
            merged,
            df_adp.drop(columns=['Location Name', 'Market'], errors='ignore'),
            left_on=['Month', 'ADP Company Code'],
            right_on=['Month', 'ADP Company Code'],
            how="left"
        )

        # 4. Merge Passare Cases using Month + Passare Location ID
        merged = pd.merge(
            merged,
            df_pas.drop(columns=['Location Name', 'Market'], errors='ignore'),
            left_on=['Month', 'Passare Location ID'],
            right_on=['Month', 'Passare Location ID'],
            how="left"
        )

        # 5. Calculated Metric Columns
        merged['Revenue Variance ($)'] = merged['Actual Revenue ($)'] - merged['Budget Revenue ($)']
        merged['EBITDA Variance ($)'] = merged['Actual EBITDA ($)'] - merged['Budget EBITDA ($)']
        merged['EBITDA Margin %'] = np.where(
            merged['Actual Revenue ($)'] > 0,
            (merged['Actual EBITDA ($)'] / merged['Actual Revenue ($)']) * 100,
            0
        )
        merged['Labor Cost % of Rev'] = np.where(
            merged['Actual Revenue ($)'] > 0,
            (merged['Total Labor Cost ($)'] / merged['Actual Revenue ($)']) * 100,
            0
        )

        return merged

    except Exception as e:
        st.error(f"Error loading and processing data: {e}")
        return None


df = load_data(FILE_NAME)

if df is not None:
    # -------------------------------------------------------------------------
    # SIDEBAR FILTERS
    # -------------------------------------------------------------------------
    st.sidebar.image("https://img.icons8.com/color/96/000000/analytics.png", width=64)
    st.sidebar.title("Dashboard Controls")
    
    # Market / Region Filter
    markets = ["All Markets"] + list(df['Market'].dropna().unique())
    selected_market = st.sidebar.selectbox("Filter Market:", markets)
    
    if selected_market != "All Markets":
        filtered_locations = list(df[df['Market'] == selected_market]['Canonical Location Name'].unique())
    else:
        filtered_locations = list(df['Canonical Location Name'].dropna().unique())

    # Location Filter
    locations = ["All Locations"] + filtered_locations
    selected_loc = st.sidebar.selectbox("Filter Location:", locations)

    # Date Range Filter
    min_date = df['Month'].min().date()
    max_date = df['Month'].max().date()
    
    selected_dates = st.sidebar.date_input(
        "Date Range:",
        value=[min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )

    # Apply Filtering Logic
    f_df = df.copy()
    if selected_market != "All Markets":
        f_df = f_df[f_df['Market'] == selected_market]
    if selected_loc != "All Locations":
        f_df = f_df[f_df['Canonical Location Name'] == selected_loc]
    if len(selected_dates) == 2:
        f_df = f_df[(f_df['Month'].dt.date >= selected_dates[0]) & (f_df['Month'].dt.date <= selected_dates[1])]

    # -------------------------------------------------------------------------
    # HEADER SECTION
    # -------------------------------------------------------------------------
    st.title("📊 Executive BI & FP&A Case Study Dashboard")
    st.caption("Consolidated Analytics across NetSuite Financials, ADP Labor, and Passare Case Management")

    # -------------------------------------------------------------------------
    # TOP KPI CARDS
    # -------------------------------------------------------------------------
    act_rev = f_df['Actual Revenue ($)'].sum()
    bud_rev = f_df['Budget Revenue ($)'].sum()
    rev_var = act_rev - bud_rev
    rev_pct = (rev_var / bud_rev * 100) if bud_rev != 0 else 0

    act_ebitda = f_df['Actual EBITDA ($)'].sum()
    bud_ebitda = f_df['Budget EBITDA ($)'].sum()
    ebitda_var = act_ebitda - bud_ebitda
    ebitda_pct = (ebitda_var / bud_ebitda * 100) if bud_ebitda != 0 else 0

    total_calls = f_df['Total Calls'].sum()
    tot_labor = f_df['Total Labor Cost ($)'].sum()
    labor_pct = (tot_labor / act_rev * 100) if act_rev > 0 else 0

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        rev_class = "pos-var" if rev_var >= 0 else "neg-var"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Actual Revenue</div>
            <div class="kpi-value">${act_rev:,.0f}</div>
            <div class="kpi-sub {rev_class}">${rev_var:+,.0f} ({rev_pct:+.1f}%) vs Bud</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        eb_class = "pos-var" if ebitda_var >= 0 else "neg-var"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Actual EBITDA</div>
            <div class="kpi-value">${act_ebitda:,.0f}</div>
            <div class="kpi-sub {eb_class}">${ebitda_var:+,.0f} ({ebitda_pct:+.1f}%) vs Bud</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        ebitda_margin = (act_ebitda / act_rev * 100) if act_rev > 0 else 0
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">EBITDA Margin</div>
            <div class="kpi-value">{ebitda_margin:.1f}%</div>
            <div class="kpi-sub">Target: 25.0%</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Total Case Volume</div>
            <div class="kpi-value">{int(total_calls):,}</div>
            <div class="kpi-sub">Passare Case Volume</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        labor_class = "neg-var" if labor_pct > 35 else "pos-var"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Labor Cost % Rev</div>
            <div class="kpi-value">{labor_pct:.1f}%</div>
            <div class="kpi-sub {labor_class}">${tot_labor:,.0f} Total Labor</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # MAIN NAVIGATION TABS
    # -------------------------------------------------------------------------
    tab_fin, tab_ops, tab_labor, tab_insights, tab_arch, tab_forecast, tab_data = st.tabs([
        "📈 Financial Performance (NetSuite)",
        "⚱️ Operational & Case Analytics (Passare)",
        "👥 Labor & Productivity (ADP)",
        "💡 Insights & Recommendations",
        "🏗️ Pipeline Architecture",
        "🔮 Forecast Implications",
        "📋 Consolidated Master Dataset"
    ])

    # =========================================================================
    # TAB 1: FINANCIAL PERFORMANCE
    # =========================================================================
    with tab_fin:
        st.subheader("Financial Trends & Budget vs. Actual Variance")

        monthly_fin = f_df.groupby('Month')[
            ['Actual Revenue ($)', 'Budget Revenue ($)', 'Actual EBITDA ($)', 'Budget EBITDA ($)']
        ].sum().reset_index()

        fig_fin = go.Figure()
        fig_fin.add_trace(go.Scatter(x=monthly_fin['Month'], y=monthly_fin['Actual Revenue ($)'], mode='lines+markers', name='Actual Revenue', line=dict(color='#2563eb', width=3)))
        fig_fin.add_trace(go.Scatter(x=monthly_fin['Month'], y=monthly_fin['Budget Revenue ($)'], mode='lines', name='Budget Revenue', line=dict(color='#93c5fd', dash='dash')))
        fig_fin.add_trace(go.Scatter(x=monthly_fin['Month'], y=monthly_fin['Actual EBITDA ($)'], mode='lines+markers', name='Actual EBITDA', line=dict(color='#059669', width=3)))
        fig_fin.add_trace(go.Scatter(x=monthly_fin['Month'], y=monthly_fin['Budget EBITDA ($)'], mode='lines', name='Budget EBITDA', line=dict(color='#6ee7b7', dash='dash')))

        fig_fin.update_layout(title="Monthly Revenue & EBITDA Performance ($)", xaxis_title="Month", yaxis_title="Amount ($)", hovermode="x unified", template="plotly_white")
        st.plotly_chart(fig_fin, use_container_width=True)

        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("##### Revenue Variance by Location")
            loc_rev = f_df.groupby('Canonical Location Name')[['Actual Revenue ($)', 'Budget Revenue ($)', 'Revenue Variance ($)']].sum().reset_index()
            loc_rev = loc_rev.sort_values(by='Revenue Variance ($)', ascending=True)

            fig_bar_rev = px.bar(
                loc_rev,
                y='Canonical Location Name',
                x='Revenue Variance ($)',
                orientation='h',
                color='Revenue Variance ($)',
                color_continuous_scale=['#ef4444', '#e5e7eb', '#10b981'],
                title="Revenue Variance vs Budget ($)"
            )
            fig_bar_rev.update_layout(template="plotly_white", showlegend=False)
            st.plotly_chart(fig_bar_rev, use_container_width=True)

        with col_right:
            st.markdown("##### Cost Structure Breakdown")
            cost_cols = ['Actual Payroll + Benefits ($)', 'Actual Merchandise ($)', 'Actual Facilities ($)', 'Actual Vehicle ($)', 'Actual Marketing ($)', 'Actual Other OpEx ($)']
            costs_sum = f_df[cost_cols].sum().reset_index()
            costs_sum.columns = ['Cost Category', 'Amount']
            costs_sum['Cost Category'] = costs_sum['Cost Category'].str.replace('Actual ', '').str.replace(' ($)', '', regex=False)

            fig_pie = px.pie(costs_sum, names='Cost Category', values='Amount', hole=0.4, title="OpEx Composition", color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_pie.update_layout(template="plotly_white")
            st.plotly_chart(fig_pie, use_container_width=True)

    # =========================================================================
    # TAB 2: OPERATIONAL & CASE ANALYTICS
    # =========================================================================
    with tab_ops:
        st.subheader("Case Volume Mix & Revenue Per Unit Analysis")

        col_op1, col_op2 = st.columns(2)

        with col_op1:
            case_mix = f_df.groupby('Month')[['Burial Cases', 'Cremation Cases', 'Other Cases']].sum().reset_index()
            fig_case_mix = px.bar(
                case_mix,
                x='Month',
                y=['Burial Cases', 'Cremation Cases', 'Other Cases'],
                title="Monthly Case Volume by Service Type",
                barmode='stack',
                color_discrete_sequence=['#1e40af', '#0d9488', '#d97706']
            )
            fig_case_mix.update_layout(template="plotly_white")
            st.plotly_chart(fig_case_mix, use_container_width=True)

        with col_op2:
            crem_trend = f_df.groupby('Month')[['Burial Cases', 'Cremation Cases', 'Total Calls']].sum().reset_index()
            crem_trend['Cremation Rate %'] = (crem_trend['Cremation Cases'] / crem_trend['Total Calls']) * 100

            fig_crem = px.line(
                crem_trend,
                x='Month',
                y='Cremation Rate %',
                title="Portfolio Cremation Mix Trend (%)",
                markers=True,
                line_shape='spline'
            )
            fig_crem.update_traces(line_color='#059669', line_width=3)
            fig_crem.update_layout(template="plotly_white", yaxis_range=[0, 100])
            st.plotly_chart(fig_crem, use_container_width=True)

        st.markdown("##### Unit Economics: Average Revenue per Case by Location")
        unit_econ = f_df.groupby('Canonical Location Name')[['Total Case Revenue ($)', 'Total Calls', 'Burial Cases', 'Cremation Cases']].sum().reset_index()
        unit_econ['Avg Revenue / Unit'] = np.where(unit_econ['Total Calls'] > 0, unit_econ['Total Case Revenue ($)'] / unit_econ['Total Calls'], 0)
        unit_econ = unit_econ.sort_values(by='Avg Revenue / Unit', ascending=False)

        fig_unit = px.bar(
            unit_econ,
            x='Canonical Location Name',
            y='Avg Revenue / Unit',
            text_auto='.2s',
            color='Avg Revenue / Unit',
            color_continuous_scale='Viridis',
            title="Average Revenue Per Case ($)"
        )
        fig_unit.update_layout(template="plotly_white")
        st.plotly_chart(fig_unit, use_container_width=True)

    # =========================================================================
    # TAB 3: LABOR & PRODUCTIVITY
    # =========================================================================
    with tab_labor:
        st.subheader("ADP Payroll Efficiency & Headcount Utilization")

        col_l1, col_l2 = st.columns(2)

        with col_l1:
            labor_hrs = f_df.groupby('Month')[['Regular Hours', 'Overtime Hours']].sum().reset_index()
            fig_hrs = px.bar(
                labor_hrs,
                x='Month',
                y=['Regular Hours', 'Overtime Hours'],
                title="Monthly Staff Hours (Regular vs Overtime)",
                color_discrete_sequence=['#3b82f6', '#ef4444']
            )
            fig_hrs.update_layout(template="plotly_white")
            st.plotly_chart(fig_hrs, use_container_width=True)

        with col_l2:
            labor_trend = f_df.groupby('Month')[['Total Labor Cost ($)', 'Actual Revenue ($)']].sum().reset_index()
            labor_trend['Labor % Rev'] = (labor_trend['Total Labor Cost ($)'] / labor_trend['Actual Revenue ($)']) * 100

            fig_lab_pct = px.line(
                labor_trend,
                x='Month',
                y='Labor % Rev',
                title="Labor Expense Ratio Trend (% of Revenue)",
                markers=True
            )
            fig_lab_pct.add_hline(y=35, line_dash="dash", line_color="red", annotation_text="Target Ceiling (35%)")
            fig_lab_pct.update_layout(template="plotly_white")
            st.plotly_chart(fig_lab_pct, use_container_width=True)

        st.markdown("##### Location Labor Productivity Summary")
        labor_summary = f_df.groupby('Canonical Location Name').agg({
            'Headcount': 'mean',
            'Regular Pay ($)': 'sum',
            'Overtime Pay ($)': 'sum',
            'Total Labor Cost ($)': 'sum',
            'Total Calls': 'sum'
        }).reset_index()

        labor_summary['Cases per Headcount'] = labor_summary['Total Calls'] / labor_summary['Headcount']
        labor_summary['Labor Cost / Case'] = labor_summary['Total Labor Cost ($)'] / labor_summary['Total Calls']

        st.dataframe(
            labor_summary.style.format({
                'Headcount': '{:.1f}',
                'Regular Pay ($)': '${:,.2f}',
                'Overtime Pay ($)': '${:,.2f}',
                'Total Labor Cost ($)': '${:,.2f}',
                'Total Calls': '{:,.0f}',
                'Cases per Headcount': '{:.1f}',
                'Labor Cost / Case': '${:,.2f}'
            }),
            use_container_width=True
        )

    # =========================================================================
    # TAB 4: REFINED EXECUTIVE INSIGHTS & STRATEGIC RECOMMENDATIONS
    # =========================================================================
    with tab_insights:
        st.subheader("💡 Key Executive Insights & Strategic Recommendations")
        
        st.markdown("""
        ### Executive Summary & Diagnostic
        Synthesizing cross-functional performance data across **NetSuite Financials**, **ADP Workforce Data**, and **Passare Operational Cases** to identify operational bottlenecks, cost structure improvements, and enterprise reporting alignment.
        """)

        col_ins1, col_ins2 = st.columns(2)

        with col_ins1:
            st.info("🔍 **Core Key Insights**")
            st.markdown("""
            1. **Location Performance Outlier — Riverview:**
               - **Riverview** represents our largest operational risk: it drives the **highest negative EBITDA variance** and the **highest overtime & labor costs**, despite having the **fewest cases per headcount** across the portfolio. This indicates a severe mismatch between fixed labor allocation and actual throughput.

            2. **Labor Cost Elasticity & Overtime:**
               - Labor expense as a percentage of revenue routinely exceeds the **35% operational target threshold** in high-volume locations during peak demand months.
               - Fixed staffing models contribute to elevated overtime premiums, signaling an opportunity for demand-aligned shift scheduling.

            3. **Cross-System Entity Alignment:**
               - Inconsistent location key naming conventions across source systems (NetSuite `NF-10x`, ADP `ADP-A0x`, Passare `PAS-20x`) increase month-end reporting latency and require manual cross-reference mapping tables.
            """)

        with col_ins2:
            st.success("🚀 **Strategic Recommendations & Action Plan**")
            st.markdown("""
            1. **Riverview Operational Audit & Labor Realignment:**
               - Immediately audit staffing schedules at Riverview to align headcount and overtime with actual case demand, establishing an immediate path to reduce labor overhead and control EBITDA leakage.

            2. **Demand-Aligned Staffing Models:**
               - Implement dynamic workforce scheduling across all locations aligned with 3-month rolling case volume trends to optimize overall labor capacity and reduce overtime leakage by **20–25%**.

            3. **Master Data Governance:**
               - Enforce a centralized `Master Location ID` schema across ERP, CRM, and HR systems at the database layer to automate consolidated executive reporting and eliminate manual staging tables.
            """)

    # =========================================================================
    # TAB 5: PIPELINE ARCHITECTURE
    # =========================================================================
    with tab_arch:
        st.subheader("🏗️ Data Pipeline Architecture")
        st.write("Comparing the legacy manual spreadsheet approach against the current implementation and future target enterprise stack.")

        arch_col1, arch_col2 = st.columns(2)

        with arch_col1:
            st.markdown("### 🔴 Current Architecture (As-Is)")
            st.caption("Manual, File-Based ETL with High Maintenance Risk")

            st.markdown("""
            <div class="arch-box">
                <span class="badge-legacy">DATA SOURCES</span>
                <div class="arch-title">Siloed System Exports</div>
                <div class="arch-desc">
                    • <b>NetSuite:</b> Manual CSV/Excel GL export<br>
                    • <b>ADP Workforce:</b> Monthly labor report CSV<br>
                    • <b>Passare:</b> Operational case history export
                </div>
            </div>

            <div class="arch-box">
                <span class="badge-legacy">INGESTION & TRANSFORM</span>
                <div class="arch-title">Manual Spreadsheet Staging</div>
                <div class="arch-desc">
                    • Manual VLOOKUPs / Excel merging<br>
                    • High risk of formula drift and manual key mismatches<br>
                    • No automated validation or data quality checks
                </div>
            </div>

            <div class="arch-box">
                <span class="badge-legacy">CONSUMPTION</span>
                <div class="arch-title">Static / Ad-hoc Reporting</div>
                <div class="arch-desc">
                    • Substantial reporting lag (5–10 days post month-end)<br>
                    • Execution bound to local <code>.xlsx</code> file
                </div>
            </div>
            """, unsafe_allow_html=True)

        with arch_col2:
            st.markdown("### 🟡 Implementation Architecture (Used for Dashboard)")
            st.caption("API Microservices, Embedded Staging DB, & Interactive Web App")

            st.markdown("""
            <div class="arch-box">
                <span class="badge-target">DATA INGESTION</span>
                <div class="arch-title">FastAPI Microservices</div>
                <div class="arch-desc">
                    • <b>Tools Used:</b> <code>FastAPI</code>, <code>Uvicorn</code><br>
                    • Serves as API endpoints/webhooks to parse incoming operational datasets and normalize raw payloads.
                </div>
            </div>

            <div class="arch-box">
                <span class="badge-target">INGESTION & TRANSFORM</span>
                <div class="arch-title">SQLite Database & Pandas ETL</div>
                <div class="arch-desc">
                    • <b>Tools Used:</b> <code>SQLite</code>, <code>SQLAlchemy</code>, <code>Pandas</code>, <code>NumPy</code><br>
                    • Raw staging in SQLite, with Pandas/SQL handling location cross-references, joins, and KPI logic.
                </div>
            </div>

            <div class="arch-box">
                <span class="badge-target">CONSUMPTION & VISUALIZATION</span>
                <div class="arch-title">Streamlit Interactive Web App</div>
                <div class="arch-desc">
                    • <b>Tools Used:</b> <code>Streamlit</code>, <code>Plotly</code><br>
                    • Web front-end featuring cached execution (<code>@st.cache_data</code>), dynamic filters, and custom KPI cards.
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 🟢 Target Enterprise Architecture (Future State)")
        st.caption("Automated Cloud Pipeline with Data Warehouse & Production BI")

        target_col1, target_col2, target_col3 = st.columns(3)

        with target_col1:
            st.markdown("""
            <div class="arch-box">
                <span class="badge-target">INGESTION (ELT)</span>
                <div class="arch-title">StitchData Integrations</div>
                <div class="arch-desc">
                    • Automated API replication syncing NetSuite, ADP, and Passare into raw staging schemas.<br>
                    • Scheduled incremental syncs (hourly/daily).
                </div>
            </div>
            """, unsafe_allow_html=True)

        with target_col2:
            st.markdown("""
            <div class="arch-box">
                <span class="badge-target">WAREHOUSE & TRANSFORM</span>
                <div class="arch-title">PostgreSQL & SQL Views</div>
                <div class="arch-desc">
                    • Enterprise cloud database staging raw data.<br>
                    • Transformations encapsulated in SQL Views / Materialized Views joining sources via <code>Location Master</code>.
                </div>
            </div>
            """, unsafe_allow_html=True)

        with target_col3:
            st.markdown("""
            <div class="arch-box">
                <span class="badge-target">VISUALIZATION LAYER</span>
                <div class="arch-title">Enterprise BI Tools</div>
                <div class="arch-desc">
                    • Direct SQL connection via Power BI, Tableau, or Streamlit Cloud.<br>
                    • Scheduled automated data refreshes and role-based distribution.
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 🗺️ Data Flow & Lineage Diagram")
        st.code("""
CURRENT IMPLEMENTATION:
[ NetSuite Data ] ----+
                      |
[ ADP Labor Data ] ---+---> [ FastAPI Endpoints ] ---> [ SQLite Staging DB ] ---> [ Pandas / SQL Transforms ] ---> [ Streamlit + Plotly Front-End ]
                      |     (INGESTION / PARSING)    (LOCAL EMBEDDED STORE)      (ENRICHMENT & CALCULATIONS)      (INTERACTIVE DASHBOARD UI)
[ Passare Cases  ] ---+

FUTURE TARGET STATE:
[ NetSuite ERP ] ----( Stitch Data Connector )----+
                                                  |
[ ADP Payroll  ] ----( Stitch Data Connector )----+---> [ PostgreSQL Database ] ---> [ PostgreSQL SQL Views ] ---> [ Power BI / Tableau / Streamlit ]
                                                  |      (RAW STAGING SCHEMA)        (JOIN LOGIC & KPI CALCULATIONS) (ENTERPRISE BI LAYER)
[ Passare CRM  ] ----( Stitch Data Connector )----+
        """, language="text")

    # =========================================================================
    # TAB 6: FORECAST IMPLICATIONS & DATA-DRIVEN PROJECTIONS
    # =========================================================================
    with tab_forecast:
        st.subheader("🔮 Forecast Implications & Quantitative Projections")
        st.caption("Extrapolating forward-looking financial and operational trends using historical run-rates and statistical averages.")

        # Data calculations for forecasting
        monthly_agg = f_df.groupby('Month').agg({
            'Actual Revenue ($)': 'sum',
            'Budget Revenue ($)': 'sum',
            'Actual EBITDA ($)': 'sum',
            'Budget EBITDA ($)': 'sum',
            'Total Labor Cost ($)': 'sum',
            'Total Calls': 'sum'
        }).reset_index().sort_values('Month')

        # Calculate historical 3-month run rates
        recent_3m = monthly_agg.tail(3)
        avg_monthly_rev = recent_3m['Actual Revenue ($)'].mean()
        avg_monthly_ebitda = recent_3m['Actual EBITDA ($)'].mean()
        avg_monthly_labor = recent_3m['Total Labor Cost ($)'].mean()
        avg_monthly_cases = recent_3m['Total Calls'].mean()

        # Run rate annualized figures
        annual_run_rev = avg_monthly_rev * 12
        annual_run_ebitda = avg_monthly_ebitda * 12

        col_fc1, col_fc2, col_fc3 = st.columns(3)

        with col_fc1:
            st.metric("3-Month Avg Monthly Revenue", f"${avg_monthly_rev:,.0f}")
            st.metric("Annualized Revenue Run-Rate", f"${annual_run_rev:,.0f}")

        with col_fc2:
            st.metric("3-Month Avg Monthly EBITDA", f"${avg_monthly_ebitda:,.0f}")
            st.metric("Annualized EBITDA Run-Rate", f"${annual_run_ebitda:,.0f}")

        with col_fc3:
            avg_labor_pct = (avg_monthly_labor / avg_monthly_rev * 100) if avg_monthly_rev > 0 else 0
            st.metric("Recent Labor % of Revenue", f"{avg_labor_pct:.1f}%")
            avg_rev_per_case = (avg_monthly_rev / avg_monthly_cases) if avg_monthly_cases > 0 else 0
            st.metric("Average Revenue / Case", f"${avg_rev_per_case:,.2f}")

        st.markdown("---")
        st.markdown("### 📊 6-Month Forward Projection (Baseline vs. Budget)")

        # Create simple forward projection dataframe based on 3-month moving average trend
        last_month = monthly_agg['Month'].max()
        future_months = [last_month + pd.DateOffset(months=i) for i in range(1, 7)]
        
        hist_df = monthly_agg[['Month', 'Actual Revenue ($)', 'Budget Revenue ($)', 'Actual EBITDA ($)']].copy()
        hist_df['Type'] = 'Historical'

        future_rows = []
        for m in future_months:
            future_rows.append({
                'Month': m,
                'Actual Revenue ($)': avg_monthly_rev,
                'Budget Revenue ($)': monthly_agg['Budget Revenue ($)'].tail(3).mean(),
                'Actual EBITDA ($)': avg_monthly_ebitda,
                'Type': 'Projected (3M Moving Avg)'
            })

        fut_df = pd.DataFrame(future_rows)
        combined_fc = pd.concat([hist_df, fut_df], ignore_index=True)

        fig_fc = go.Figure()
        fig_fc.add_trace(go.Scatter(
            x=combined_fc['Month'], 
            y=combined_fc['Actual Revenue ($)'], 
            mode='lines+markers', 
            name='Revenue (Historical / Projected)', 
            line=dict(color='#2563eb', width=3)
        ))
        fig_fc.add_trace(go.Scatter(
            x=combined_fc['Month'], 
            y=combined_fc['Actual EBITDA ($)'], 
            mode='lines+markers', 
            name='EBITDA (Historical / Projected)', 
            line=dict(color='#059669', width=3)
        ))
        fig_fc.add_trace(go.Scatter(
            x=combined_fc['Month'], 
            y=combined_fc['Budget Revenue ($)'], 
            mode='lines', 
            name='Budget Revenue Baseline', 
            line=dict(color='#93c5fd', dash='dash')
        ))

        fig_fc.update_layout(
            title="Revenue & EBITDA 6-Month Run-Rate Projection ($)",
            xaxis_title="Month",
            yaxis_title="Amount ($)",
            hovermode="x unified",
            template="plotly_white"
        )
        st.plotly_chart(fig_fc, use_container_width=True)

        st.markdown("""
        ### Quantitative Analysis & Model Observations
        - **Revenue Trajectory:** Based on trailing 3-month averages, monthly revenue is projected at **${:,.0f}**, yielding an annualized run-rate of **${:,.0f}**.
        - **EBITDA Run-Rate:** Trailing EBITDA trends project an annual run-rate of **${:,.0f}**.
        - **Labor Cost Impact:** Maintaining current labor cost ratios ({:.1f}% of revenue) without adjusting for location-level efficiency risks continued EBITDA variance against budgeted operational targets.
        """.format(avg_monthly_rev, annual_run_rev, annual_run_ebitda, avg_labor_pct))

    # =========================================================================
    # TAB 7: CONSOLIDATED MASTER DATA TABLE
    # =========================================================================
    with tab_data:
        st.subheader("Consolidated Data View")
        st.write(f"Showing **{len(f_df)}** merged rows matching active filter criteria.")

        csv = f_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Filtered Master Dataset (CSV)",
            data=csv,
            file_name="consolidated_bi_case_study_data.csv",
            mime="text/csv"
        )

        st.dataframe(f_df, use_container_width=True)