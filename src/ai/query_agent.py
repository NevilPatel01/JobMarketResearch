"""
AI-powered natural language to SQL with validation agent.

Plug-and-play LLM: use Ollama (local) or OpenAI via LLM_PROVIDER.
User asks e.g. "Find me Data Analyst jobs in Toronto"
-> LLM generates SQL
-> Validation agent checks if SQL matches intent
-> If not, iterate with feedback until correct (max 3 attempts)
"""

import os
from typing import Tuple, Optional

from .backends import get_llm_backend

SCHEMA = """
PostgreSQL schema for job market data. Use jobs_raw (alias jr) as main table.

jobs_raw (jr) - main table for job listings:
  jr.job_id, jr.source, jr.title, jr.company, jr.city, jr.province,
  jr.description, jr.salary_min, jr.salary_max, jr.remote_type,
  jr.posted_date (DATE - use for recency filters),
  jr.url

jobs_features (jf) - optional JOIN on jr.job_id = jf.job_id:
  jf.exp_min, jf.exp_max, jf.exp_level, jf.skills (JSONB), jf.is_remote, jf.is_junior

COLUMN RULES:
- Title/role search: jr.title ILIKE '%keyword%'
- City search: jr.city ILIKE '%city%'  
- Company: jr.company ILIKE '%company%'
- Remote/hybrid: jr.remote_type IN ('remote','hybrid') OR jf.is_remote = true
- DATE FILTERS (critical - posted_date is DATE):
  "last N days" or "within last N days" or "past N days" or "posted in last N days"
  -> jr.posted_date >= CURRENT_DATE - INTERVAL 'N days'
  "last week" -> INTERVAL '7 days'
  "last 2 weeks" -> INTERVAL '14 days'
  "last month" -> INTERVAL '30 days'
- Province: jr.province = 'ON' or ILIKE for codes (ON, AB, BC, QC, SK, MB)
- Salary: jr.salary_min, jr.salary_max (both INTEGER)
- Skills in JSONB: jf.skills @> '["python"]'::jsonb or jsonb_array_elements_text(jf.skills)

OUTPUT: SELECT jr.title, jr.company, jr.city, jr.province, jr.source, jr.posted_date, jr.url
Always add ORDER BY jr.posted_date DESC and LIMIT 100.
"""


def _get_llm():
    """Get configured LLM backend (Ollama or OpenAI)."""
    return get_llm_backend()


def generate_sql(user_query: str, feedback: Optional[str] = None) -> str:
    """
    Convert user natural language to PostgreSQL SELECT query.
    
    Args:
        user_query: e.g. "Find me Data Analyst jobs in Toronto"
        feedback: If validation failed, feedback from validator
        
    Returns:
        SQL SELECT query string
    """
    llm = _get_llm()
    
    sys_msg = f"""You are a SQL expert. Convert the user's question into a PostgreSQL query.
{SCHEMA}

RULES:
- Output ONLY valid SQL, no markdown, no explanation.
- SELECT only. No DROP, DELETE, UPDATE, INSERT.
- Always use: FROM jobs_raw jr (optionally LEFT JOIN jobs_features jf ON jr.job_id = jf.job_id)
- Use jr. prefix for jobs_raw columns.
- For recency: "last N days", "within last N days", "past N days" -> jr.posted_date >= CURRENT_DATE - INTERVAL 'N days'
- Combine all filters with AND in WHERE clause.
- Return columns: jr.title, jr.company, jr.city, jr.province, jr.source, jr.posted_date, jr.url
- Always add ORDER BY jr.posted_date DESC NULLS LAST LIMIT 100

EXAMPLES:
Q: "Data Analyst in Toronto within last 5 days"
SELECT jr.title, jr.company, jr.city, jr.province, jr.source, jr.posted_date, jr.url
FROM jobs_raw jr
WHERE jr.title ILIKE '%Data Analyst%' AND jr.city ILIKE '%Toronto%' AND jr.posted_date >= CURRENT_DATE - INTERVAL '5 days'
ORDER BY jr.posted_date DESC NULLS LAST LIMIT 100;

Q: "remote Python jobs"
SELECT jr.title, jr.company, jr.city, jr.province, jr.source, jr.posted_date, jr.url
FROM jobs_raw jr
WHERE (jr.remote_type IN ('remote','hybrid') OR jr.title ILIKE '%remote%') AND jr.title ILIKE '%Python%'
ORDER BY jr.posted_date DESC NULLS LAST LIMIT 100;"""
    
    user_msg = user_query
    if feedback:
        user_msg = f"Previous query was wrong. Feedback: {feedback}\n\nOriginal question: {user_query}\n\nGenerate a corrected SQL query."
    
    sql = llm.chat(
        messages=[
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.1,
    )
    # Extract SQL if wrapped in markdown
    if sql.startswith("```"):
        lines = sql.split("\n")
        sql = "\n".join(l for l in lines if not l.strip().startswith("```"))
    return sql


def validate_query(user_query: str, sql: str) -> Tuple[bool, str]:
    """
    Validation agent: check if generated SQL correctly implements user intent.
    
    Returns:
        (is_valid, feedback) - if not valid, feedback explains what's wrong
    """
    # Safety: reject non-SELECT
    s = sql.strip().upper()
    if not s.startswith("SELECT"):
        return False, "Query must be SELECT only."
    for bad in ("DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE"):
        if bad in s:
            return False, f"Query contains forbidden operation: {bad}"
    
    llm = _get_llm()
    
    resp = llm.chat(
        messages=[
            {"role": "system", "content": """You are a SQL validation agent. Given a user question and a SQL query, determine if the query correctly implements the user's intent.
Answer in exact format:
VALID: yes
OR
VALID: no
FEEDBACK: [brief explanation of what's wrong and how to fix]"""},
            {"role": "user", "content": f"User question: {user_query}\n\nGenerated SQL:\n{sql}"},
        ],
        temperature=0,
    )
    resp = (resp or "").strip().upper()
    if "VALID: YES" in resp:
        return True, ""
    feedback = ""
    if "FEEDBACK:" in resp:
        feedback = resp.split("FEEDBACK:", 1)[-1].strip()
    return False, feedback or "Query does not match user intent."


def nl_to_sql_and_validate(user_query: str, max_attempts: int = 3) -> Tuple[Optional[str], Optional[str]]:
    """
    Generate SQL from natural language with validation loop.
    
    Returns:
        (sql, error) - sql if success, error message if failed
    """
    sql = None
    feedback = None
    
    for attempt in range(max_attempts):
        sql = generate_sql(user_query, feedback)
        ok, feedback = validate_query(user_query, sql)
        if ok:
            return sql, None
        # Re-iterate with feedback
    
    return sql, f"Could not generate valid query after {max_attempts} attempts. Last feedback: {feedback}"
