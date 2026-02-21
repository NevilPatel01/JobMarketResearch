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
PostgreSQL schema for job market data:

Table: jobs_raw
- job_id (VARCHAR, primary key)
- source (VARCHAR): jobbank, adzuna, remoteok, jsearch, rapidapi
- title (VARCHAR): job title
- company (VARCHAR): company name
- city (VARCHAR): city name
- province (CHAR(2)): ON, AB, BC, QC, SK, MB, etc.
- description (TEXT): job description
- salary_min (INT), salary_max (INT)
- remote_type (VARCHAR): remote, hybrid, onsite
- posted_date (DATE)
- url (TEXT): job posting URL

Table: jobs_features (JOIN on job_id)
- job_id (VARCHAR, FK to jobs_raw)
- exp_min (INT), exp_max (INT): years of experience
- exp_level (VARCHAR): entry, junior, mid, senior, lead
- skills (JSONB): array of skills e.g. ["python","sql"]
- is_remote (BOOLEAN)

Use ILIKE for case-insensitive text search. Always add LIMIT (e.g. 100).
Return job listings with: title, company, city, province, source, posted_date, url.
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

Rules:
- Output ONLY the SQL, no explanation.
- Use SELECT only. No DROP, DELETE, UPDATE, INSERT.
- Use jobs_raw jr, optionally LEFT JOIN jobs_features jf ON jr.job_id = jf.job_id
- For role/title search: jr.title ILIKE '%keyword%'
- For city: jr.city ILIKE '%city%'
- Always include LIMIT (e.g. 100).
- Return columns: title, company, city, province, source, posted_date, url"""
    
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
