"""Check current jobs in database."""

import sys
from pathlib import Path

src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from database.connection import DatabaseConnection
from database.models import JobRaw

db = DatabaseConnection()
with db.get_session() as session:
    jobs = session.query(JobRaw).limit(15).all()
    print("\nSample jobs in database:")
    print("="*100)
    for job in jobs:
        salary_str = f"${job.salary_min}-${job.salary_max}" if job.salary_min else "N/A"
        print(f"{job.title[:35]:35s} | {salary_str:20s} | {job.city}, {job.province}")
    print("="*100)
