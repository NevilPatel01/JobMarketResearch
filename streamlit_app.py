#!/usr/bin/env python3
"""
Canada Tech Job Compass – Interactive Dashboard

Streamlit app with charts and AI-powered natural language search.
Ask in plain English e.g. "Find me Data Analyst jobs in Hamilton" – LLM generates
SQL, validation agent ensures it matches your intent, then results are shown.
Run: streamlit run streamlit_app.py
"""

import re
import sys
from pathlib import Path

# Add src and project root for imports
_root = Path(__file__).resolve().parent
sys.path.insert(0, str(_root / "src"))
sys.path.insert(0, str(_root))

import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import text

# Page config – must be first Streamlit command
st.set_page_config(
    page_title="Canada Tech Job Compass",
    page_icon="🇨🇦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for a polished look
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
    
    .stApp {
        background: linear-gradient(165deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
        font-family: 'DM Sans', -apple-system, sans-serif;
    }
    
    h1, h2, h3 {
        font-weight: 600 !important;
        color: #f1f5f9 !important;
        letter-spacing: -0.02em;
    }
    
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%);
        border: 1px solid rgba(148, 163, 184, 0.15);
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #38bdf8;
        line-height: 1.2;
    }
    
    .metric-label {
        font-size: 0.85rem;
        color: #94a3b8;
        margin-top: 0.25rem;
    }
    
    .stMetric [data-testid="stMetricValue"] {
        font-size: 1.75rem !important;
        color: #38bdf8 !important;
    }
    
    .stMetric [data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
    }
    
    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
    }
    
    .section-header {
        font-size: 1.1rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.75rem;
    }
    
    .insight-box {
        background: rgba(56, 189, 248, 0.08);
        border-left: 4px solid #38bdf8;
        padding: 1rem 1.25rem;
        border-radius: 0 8px 8px 0;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


# Exclude jobs with bad salary (e.g. $8-$35 hourly misparsed as annual)
SALARY_FILTER = "((jr.salary_min IS NULL AND jr.salary_max IS NULL) OR COALESCE(jr.salary_max, jr.salary_mid) >= 10000)"
SALARY_FILTER_RAW = "((salary_min IS NULL AND salary_max IS NULL) OR COALESCE(salary_max, salary_mid) >= 10000)"


@st.cache_resource
def get_db():
    """Connect to database (cached for session)."""
    from database.connection import DatabaseConnection
    return DatabaseConnection()


def run_query(db, query: str, params=None, return_columns=False):
    """Execute query and return rows. If return_columns=True, return (rows, column_names)."""
    with db.get_session() as session:
        result = session.execute(text(query), params or {})
        rows = result.fetchall()
        if return_columns:
            cols = list(result.keys()) if result.keys() else []
            return rows, cols
        return rows


def _simple_keyword_search(query: str) -> tuple[str, dict] | None:
    """
    Try to build SQL for simple "X in Y" or "X jobs in Y" patterns (no date filters).
    Returns (sql_with_params, params) if pattern matches, else None.
    Queries with date modifiers (e.g. "within last 5 days") fall through to AI.
    """
    q = query.strip()
    # Don't use simple path when user asks for date filtering - AI handles that
    if re.search(r"within\s+last|last\s+\d+\s+days?|past\s+\d+|posted\s+(in\s+)?last|recent(ly)?", q, re.I):
        return None
    m = re.search(r"(.+?)\s+in\s+(.+)$", q, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    role_part = re.sub(r"^(find\s+me\s+|show\s+me\s+|get\s+|jobs?\s*)*", "", m.group(1), flags=re.I).strip()
    city = m.group(2).strip()
    # City should be a single location, not "Toronto within last 5 days"
    if not role_part or not city or len(city) > 50:
        return None
    sql = f"""
        SELECT title, company, city, province, source, posted_date, url
        FROM jobs_raw
        WHERE title ILIKE '%' || :role || '%' AND city ILIKE '%' || :city || '%'
          AND {SALARY_FILTER_RAW}
        ORDER BY posted_date DESC
        LIMIT 100
    """.strip()
    return sql, {"role": role_part, "city": city}


def render_ask(db):
    """AI-powered natural language query – user asks, LLM generates SQL, validation agent verifies."""
    st.subheader("🤖 Ask in Natural Language")
    st.caption("e.g. 'Find me Data Analyst jobs in Hamilton' – AI converts to SQL and runs it")
    
    with st.form("ask_form", clear_on_submit=False):
        query = st.text_input("Ask", placeholder="Find me Data Analyst jobs in Hamilton", key="nl_query")
        submitted = st.form_submit_button("Search")
    
    if not submitted:
        st.info("Ask a question about jobs, e.g. 'Data Analyst in Toronto', 'remote software engineer jobs'")
        return
    
    if not query or len(query.strip()) < 3:
        st.warning("Please enter at least 3 characters.")
        return
    
    q = query.strip()

    # Fast path: simple "X in Y" or "X jobs in Y" pattern – instant results without LLM
    simple = _simple_keyword_search(q)
    if simple:
        sql, params = simple
        with st.spinner("Searching..."):
            try:
                rows, col_names = run_query(db, sql, params=params, return_columns=True)
            except Exception as e:
                st.error(f"Query failed: {e}")
                return
        if rows:
            cols = col_names if col_names else [f"Col{i}" for i in range(len(rows[0]))]
            df = pd.DataFrame(rows, columns=cols)
            col_config = {}
            for link_col in ["url", "URL"]:
                if link_col in df.columns:
                    col_config[link_col] = st.column_config.LinkColumn(link_col)
                    break
            st.success(f"Found {len(rows)} results")
            st.dataframe(df, width="stretch", hide_index=True, column_config=col_config)
            with st.expander("View SQL query"):
                r, c = params.get("role", "").replace("'", "''"), params.get("city", "").replace("'", "''")
                sql_display = f"""SELECT title, company, city, province, source, posted_date, url
        FROM jobs_raw
        WHERE title ILIKE '%{r}%' AND city ILIKE '%{c}%'
          AND {SALARY_FILTER_RAW}
        ORDER BY posted_date DESC
        LIMIT 100"""
                st.code(sql_display, language="sql")
        else:
            st.warning("No jobs match your query.")
        return

    # AI path: LLM generates SQL (slower, handles complex queries)
    with st.spinner("Generating query... validating... running..."):
        try:
            from ai.query_agent import nl_to_sql_and_validate
            sql, err = nl_to_sql_and_validate(q)
            if err:
                st.error(err)
                return
            
            # Safety: run only first statement
            sql_safe = sql.split(";")[0].strip() or sql
            if "LIMIT" not in sql_safe.upper():
                sql_safe = sql_safe.rstrip() + " LIMIT 100"
            rows, col_names = run_query(db, sql_safe, return_columns=True)
            
            if rows:
                cols = col_names if col_names else [f"Col{i}" for i in range(len(rows[0]))]
                df = pd.DataFrame(rows, columns=cols)
                col_config = {}
                for link_col in ["url", "URL"]:
                    if link_col in df.columns:
                        col_config[link_col] = st.column_config.LinkColumn(link_col)
                        break
                st.success(f"Found {len(rows)} results")
                st.dataframe(df, width="stretch", hide_index=True, column_config=col_config)
                with st.expander("View SQL query"):
                    st.code(sql, language="sql")
            else:
                st.warning("No jobs match your query.")
        except ValueError as e:
            if "OPENAI_API_KEY" in str(e) or "LLM_PROVIDER" in str(e):
                st.error("For AI search: set OLLAMA_API_KEY (ollama.com) or LLM_PROVIDER=openai with OPENAI_API_KEY.")
            else:
                st.error(str(e))
        except Exception as e:
            err_msg = str(e)
            if "404" in err_msg and "model" in err_msg.lower():
                st.error(f"Model not found. For Ollama Cloud, set OLLAMA_MODEL to a cloud model (e.g. qwen3-next:80b, ministral-3:8b) in .env. See ollama.com/search?c=cloud")
            else:
                st.error(f"Error: {e}")


def _get_filter_options(db):
    """Load distinct provinces and top cities for filter dropdowns."""
    with db.get_session() as session:
        prov = session.execute(text(
            "SELECT DISTINCT province FROM jobs_raw WHERE province IS NOT NULL ORDER BY province"
        )).fetchall()
        cities = session.execute(text(
            """SELECT city FROM jobs_raw GROUP BY city ORDER BY COUNT(*) DESC LIMIT 80"""
        )).fetchall()
    return [p[0] for p in prov], [c[0] for c in cities]


def render_filter_search(db):
    """Filter-based search: Job Title, Province, City, Pay range, Posted date."""
    st.subheader("🔍 Filter Search")
    st.caption("Combine filters to narrow down job listings. Leave fields empty to include all.")
    
    provinces, cities = _get_filter_options(db)
    province_options = [""] + provinces
    city_options = [""] + cities
    
    with st.form("filter_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            job_title = st.text_input(
                "Job Title",
                placeholder="e.g. Software, Data Analyst, Developer",
                help="Partial match – e.g. 'Software' matches Software Developer, Software Engineer, etc."
            )
            province = st.selectbox(
                "Province",
                options=province_options,
                format_func=lambda x: "Any" if not x else f"{x} ({_province_name(x)})",
                help="Filter by Canadian province/territory"
            )
            salary_min = st.number_input(
                "Min Salary ($)",
                min_value=0,
                value=0,
                step=5000,
                help="Minimum annual salary – 0 means no filter"
            )
        with col2:
            city = st.selectbox(
                "City",
                options=city_options,
                format_func=lambda x: "Any" if not x else x,
                help="Filter by city"
            )
            remote_type = st.selectbox(
                "Work Arrangement",
                options=["", "remote", "hybrid", "remote_or_hybrid", "onsite"],
                format_func=lambda x: {"": "Any", "remote_or_hybrid": "Remote or Hybrid"}.get(x, x.title()),
                help="Filter by work arrangement"
            )
            posted_days = st.selectbox(
                "Posted Within",
                options=[0, 7, 14, 30, 60, 90],
                format_func=lambda x: "All time" if x == 0 else f"Last {x} days",
                index=3,
                help="Only show jobs posted in this time window"
            )
            salary_max = st.number_input(
                "Max Salary ($)",
                min_value=0,
                value=0,
                step=5000,
                help="Maximum annual salary – 0 means no filter"
            )
        
        submitted = st.form_submit_button("Apply Filters")
    
    if not submitted:
        st.info("Set your filters above and click **Apply Filters** to search.")
        return
    
    # Build SQL with parameterized filters
    conditions = []
    params = {}
    
    if job_title and job_title.strip():
        # Split into keywords: "Software" -> match "Software Developer", "Software Engineer", etc.
        # "Software Engineer" -> match titles containing BOTH "Software" AND "Engineer"
        # ILIKE with ESCAPE for literal % and _ (regex \Q\E caused "invalid escape" with params)
        keywords = [k.strip() for k in job_title.strip().split() if k.strip()]
        for i, kw in enumerate(keywords):
            safe_kw = kw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            param_name = f"job_title_{i}"
            conditions.append("title ILIKE '%' || :" + param_name + " || '%' ESCAPE '\\'")
            params[param_name] = safe_kw
    
    if province:
        conditions.append("province = :province")
        params["province"] = province
    
    if city:
        conditions.append("city = :city")
        params["city"] = city
    
    if remote_type:
        if remote_type == "remote_or_hybrid":
            conditions.append("LOWER(COALESCE(remote_type, '')) IN ('remote', 'hybrid')")
        else:
            conditions.append("LOWER(COALESCE(remote_type, '')) = :remote_type")
            params["remote_type"] = remote_type.lower()
    
    if salary_min and salary_min > 0:
        conditions.append("COALESCE(salary_max, salary_mid) >= :salary_min")
        params["salary_min"] = salary_min
    
    if salary_max and salary_max > 0:
        conditions.append("COALESCE(salary_min, salary_mid) <= :salary_max")
        params["salary_max"] = salary_max
    
    if posted_days > 0:
        conditions.append(f"posted_date >= CURRENT_DATE - INTERVAL '{posted_days} days'")
    
    # Exclude jobs with bad salary ($8-$35 etc.)
    conditions.append(SALARY_FILTER_RAW)
    where_clause = " AND ".join(conditions)
    
    sql = f"""
        SELECT title, company, city, province, source, posted_date, url,
               salary_min, salary_max
        FROM jobs_raw
        WHERE {where_clause}
        ORDER BY posted_date DESC
        LIMIT 200
    """
    
    with st.spinner("Searching..."):
        try:
            rows, col_names = run_query(db, sql, params=params if params else None, return_columns=True)
        except Exception as e:
            st.error(f"Query failed: {e}")
            return
    
    if rows:
        cols = col_names if col_names else [f"Col{i}" for i in range(len(rows[0]))]
        df = pd.DataFrame(rows, columns=cols)
        col_config = {}
        for link_col in ["url", "URL"]:
            if link_col in df.columns:
                col_config[link_col] = st.column_config.LinkColumn(link_col)
                break
        if "salary_min" in df.columns and "salary_max" in df.columns:
            col_config["salary_min"] = st.column_config.NumberColumn("Min Salary", format="$%d")
            col_config["salary_max"] = st.column_config.NumberColumn("Max Salary", format="$%d")
        st.success(f"Found {len(rows)} results")
        st.dataframe(df, width="stretch", hide_index=True, column_config=col_config)
        with st.expander("View SQL query"):
            st.code(sql, language="sql")
    else:
        st.warning("No jobs match your filters. Try adjusting or removing some filters.")


def _province_name(code: str) -> str:
    """Map province code to full name."""
    names = {"AB": "Alberta", "BC": "British Columbia", "MB": "Manitoba", "NB": "New Brunswick",
             "NL": "Newfoundland", "NS": "Nova Scotia", "NT": "N.W.T.", "NU": "Nunavut",
             "ON": "Ontario", "PE": "P.E.I.", "QC": "Quebec", "SK": "Saskatchewan", "YT": "Yukon"}
    return names.get(code, code)


def render_overview(db, days_option, date_where, date_where_jr):
    """Overview tab – charts and metrics."""
    st.markdown("# 🇨🇦 Canada Tech Job Compass")
    st.markdown("*Explore tech job opportunities across Canadian cities*")
    st.markdown("---")
    
    # Overview metrics (exclude bad salary jobs)
    q_overview = f"""
        SELECT COUNT(*) as total, COUNT(jf.job_id) as with_features
        FROM jobs_raw jr
        LEFT JOIN jobs_features jf ON jr.job_id = jf.job_id
        WHERE {date_where_jr} AND {SALARY_FILTER}
    """
    row = run_query(db, q_overview)[0]
    total, with_features = row[0], row[1]
    
    # Source breakdown
    q_sources = f"""
        SELECT source, COUNT(*) as cnt
        FROM jobs_raw
        WHERE {date_where} AND {SALARY_FILTER_RAW}
        GROUP BY source ORDER BY cnt DESC
    """
    sources = run_query(db, q_sources)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Jobs", f"{total:,}")
    with col2:
        st.metric("With Features", f"{with_features:,}")
    with col3:
        pct = (with_features / total * 100) if total > 0 else 0
        st.metric("Feature Coverage", f"{pct:.1f}%")
    with col4:
        st.metric("Sources", len(sources))
    
    st.markdown("")
    
    # Row 1: By source (pie) + Top cities (bar)
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📥 Jobs by Source")
        df_sources = pd.DataFrame(sources, columns=["Source", "Count"])
        fig_sources = px.pie(
            df_sources, values="Count", names="Source",
            color_discrete_sequence=px.colors.qualitative.Set2,
            hole=0.45,
        )
        fig_sources.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8", size=12),
            legend=dict(orientation="h", yanchor="bottom", y=-0.15),
            showlegend=True,
            height=320,
        )
        st.plotly_chart(fig_sources, width="stretch")
    
    with col_right:
        st.subheader("🏙️ Top Cities")
        q_cities = f"""
            SELECT city, province, COUNT(*) as cnt
            FROM jobs_raw
            WHERE {date_where} AND {SALARY_FILTER_RAW}
            GROUP BY city, province
            ORDER BY cnt DESC LIMIT 12
        """
        cities = run_query(db, q_cities)
        df_cities = pd.DataFrame(cities, columns=["City", "Province", "Count"])
        df_cities["Location"] = df_cities["City"] + ", " + df_cities["Province"].fillna("?")
        
        fig_cities = px.bar(
            df_cities, x="Count", y="Location",
            orientation="h",
            color="Count",
            color_continuous_scale="Blues",
        )
        fig_cities.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8", size=11),
            xaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.15)"),
            yaxis=dict(autorange="reversed"),
            coloraxis_showscale=False,
            height=320,
        )
        st.plotly_chart(fig_cities, width="stretch")
    
    # Row 2: Top roles + Top skills
    col_roles, col_skills = st.columns(2)
    
    with col_roles:
        st.subheader("👔 Top Roles")
        q_roles = f"""
            SELECT title, COUNT(*) as cnt
            FROM jobs_raw jr
            WHERE {date_where_jr} AND {SALARY_FILTER}
            GROUP BY title
            ORDER BY cnt DESC LIMIT 12
        """
        roles = run_query(db, q_roles)
        df_roles = pd.DataFrame(roles, columns=["Role", "Count"])
        
        fig_roles = px.bar(
            df_roles, x="Count", y="Role",
            orientation="h",
            color="Count",
            color_continuous_scale="Teal",
        )
        fig_roles.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8", size=11),
            xaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.15)"),
            yaxis=dict(autorange="reversed"),
            coloraxis_showscale=False,
            height=320,
        )
        st.plotly_chart(fig_roles, width="stretch")
    
    with col_skills:
        st.subheader("🛠️ Top Skills")
        if days_option > 0:
            q_skills = f"""
                SELECT LOWER(TRIM(skill::text)) as sk, COUNT(*) as cnt
                FROM jobs_raw jr
                JOIN jobs_features jf ON jr.job_id = jf.job_id,
                     jsonb_array_elements_text(COALESCE(jf.skills,'[]'::jsonb)) skill
                WHERE jr.posted_date >= CURRENT_DATE - INTERVAL '{days_option} days' AND {SALARY_FILTER}
                GROUP BY sk ORDER BY cnt DESC LIMIT 12
            """
        else:
            q_skills = """
                SELECT LOWER(TRIM(skill::text)) as sk, COUNT(*) as cnt
                FROM jobs_features jf,
                     jsonb_array_elements_text(COALESCE(jf.skills,'[]'::jsonb)) skill
                GROUP BY sk ORDER BY cnt DESC LIMIT 12
            """
        skills = run_query(db, q_skills)
        df_skills = pd.DataFrame(skills, columns=["Skill", "Count"])
        
        fig_skills = px.bar(
            df_skills, x="Count", y="Skill",
            orientation="h",
            color="Count",
            color_continuous_scale="Viridis",
        )
        fig_skills.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8", size=11),
            xaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.15)"),
            yaxis=dict(autorange="reversed"),
            coloraxis_showscale=False,
            height=320,
        )
        st.plotly_chart(fig_skills, width="stretch")
    
    # Row 3: Salary + Remote + Experience ladder
    st.subheader("📊 Key Insights")
    i1, i2, i3 = st.columns(3)
    
    with i1:
        q_sal = f"""
            SELECT ROUND(AVG(salary_mid)) as avg_sal, COUNT(*) as n
            FROM jobs_raw
            WHERE salary_mid IS NOT NULL AND salary_mid >= 10000 AND {date_where}
        """
        r = run_query(db, q_sal)[0]
        if r and r[1] > 0:
            st.markdown(f"""
            <div class="insight-box">
                <div class="metric-value">${r[0]:,.0f}</div>
                <div class="metric-label">Avg salary ({r[1]:,} jobs with data)</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No salary data in selected range")
    
    with i2:
        q_remote = f"""
            SELECT ROUND(100.0 * AVG(CASE WHEN COALESCE(jf.is_remote, false) OR jr.remote_type IN ('remote','hybrid') THEN 1 ELSE 0 END), 1)
            FROM jobs_raw jr
            LEFT JOIN jobs_features jf ON jr.job_id = jf.job_id
            WHERE {date_where_jr} AND {SALARY_FILTER}
        """
        r = run_query(db, q_remote)[0]
        if r and r[0] is not None:
            st.markdown(f"""
            <div class="insight-box">
                <div class="metric-value">{r[0]}%</div>
                <div class="metric-label">Remote / hybrid roles</div>
            </div>
            """, unsafe_allow_html=True)
    
    with i3:
        st.markdown(f"""
        <div class="insight-box">
            <div class="metric-value">{days_option if days_option > 0 else '∞'}</div>
            <div class="metric-label">Days in view</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Experience ladder table
    st.subheader("📈 Experience Ladder (Junior-Friendliest)")
    st.caption("City + role combos with highest % of junior-suitable jobs (≥3 jobs)")
    
    q_exp = f"""
        SELECT jr.city, jr.title, 
               ROUND(AVG((COALESCE(jf.exp_min,0)+COALESCE(jf.exp_max,jf.exp_min,0))/2.0),1) as avg_exp,
               ROUND(100.0*AVG(CASE WHEN (COALESCE(jf.exp_min,99)+COALESCE(jf.exp_max,jf.exp_min,99))/2.0 <= 2 THEN 1 ELSE 0 END),1) as junior_pct,
               COUNT(*) as n
        FROM jobs_raw jr
        JOIN jobs_features jf ON jr.job_id = jf.job_id
        WHERE (jf.exp_min IS NOT NULL OR jf.exp_max IS NOT NULL) AND {date_where_jr} AND {SALARY_FILTER}
        GROUP BY jr.city, jr.title
        HAVING COUNT(*) >= 3
        ORDER BY junior_pct DESC, avg_exp ASC
        LIMIT 15
    """
    exp_rows = run_query(db, q_exp)
    
    if exp_rows:
        df_exp = pd.DataFrame(exp_rows, columns=["City", "Role", "Avg Exp (y)", "Junior %", "Jobs"])
        st.dataframe(df_exp, width="stretch", hide_index=True)
    else:
        st.info("No experience ladder data in this range. Try a wider time range.")


def main():
    db = get_db()
    
    # Sidebar – filters
    st.sidebar.markdown("## 🎛️ Filters")
    st.sidebar.markdown("---")
    
    days_option = st.sidebar.selectbox(
        "Time range",
        [7, 30, 90, 0],
        format_func=lambda x: "Last 7 days" if x == 7 else "Last 30 days" if x == 30 else "Last 90 days" if x == 90 else "All time",
        index=2,
    )
    
    date_where = f"posted_date >= CURRENT_DATE - INTERVAL '{days_option} days'" if days_option > 0 else "1=1"
    date_where_jr = f"jr.posted_date >= CURRENT_DATE - INTERVAL '{days_option} days'" if days_option > 0 else "1=1"
    
    st.sidebar.markdown("---")
    st.sidebar.caption("AI search: OLLAMA_API_KEY (cloud) or LLM_PROVIDER=openai")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📊 Overview", "🔍 Filter Search", "🤖 Ask AI"])
    
    with tab1:
        render_overview(db, days_option, date_where, date_where_jr)
    
    with tab2:
        render_filter_search(db)
    
    with tab3:
        render_ask(db)
    
    st.markdown("---")
    st.caption("Canada Tech Job Compass • Filter search + AI natural language • Refresh: `python run.py process`")


if __name__ == "__main__":
    main()
