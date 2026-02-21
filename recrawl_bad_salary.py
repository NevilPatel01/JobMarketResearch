#!/usr/bin/env python3
"""
Re-crawl job descriptions for jobs with bad salary data ($8-$35 etc.).

Fetches full job detail pages from Job Bank Canada, parses description + salary,
and updates jobs_raw. Stores complete job description for future re-parsing.

Usage:
    python recrawl_bad_salary.py [--limit N] [--dry-run]

Options:
    --limit N   Max jobs to process (default: all)
    --dry-run   Show what would be updated without writing to DB
"""

from utils.logger import setup_logger
from database.storage import JobStorage
from database.connection import DatabaseConnection
from collectors.jobbank_collector import JobBankCollector
from sqlalchemy import text
import sys
from pathlib import Path

src_path = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(src_path))


logger = setup_logger(__name__)

# Jobs with salary_max < this are considered "bad" (hourly misparsed as annual)
BAD_SALARY_THRESHOLD = 10000


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Re-crawl jobs with bad salary data")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max jobs to process (0=all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Don't write to DB")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("RE-CRAWL BAD SALARY JOBS")
    logger.info("=" * 60)

    db = DatabaseConnection()
    storage = JobStorage(db)
    collector = JobBankCollector()

    # Find Job Bank jobs with bad salary
    with db.get_session() as session:
        q = f"""
            SELECT job_id, url, title, salary_min, salary_max
            FROM jobs_raw
            WHERE source = 'jobbank'
            AND url IS NOT NULL
            AND (COALESCE(salary_max, salary_mid) < {BAD_SALARY_THRESHOLD}
            OR (salary_min IS NOT NULL AND salary_min < {BAD_SALARY_THRESHOLD}))
            ORDER BY posted_date DESC
        """
        if args.limit > 0:
            q += f" LIMIT {args.limit}"
        rows = session.execute(text(q)).fetchall()

    logger.info(f"Found {len(rows)} Job Bank jobs with bad salary data")

    if not rows:
        logger.info("Nothing to re-crawl.")
        return

    updated = 0
    failed = 0

    for job_id, url, title, sal_min, sal_max in rows:
        logger.info(f"Re-crawling: {job_id} - {title[:50]}...")
        try:
            detail = collector.fetch_job_detail(url)
            if not detail:
                logger.warning(f"  Failed to fetch: {url}")
                failed += 1
                continue

            desc = detail.get("description", "")
            new_min = detail.get("salary_min")
            new_max = detail.get("salary_max")

            if args.dry_run:
                logger.info(
                    f"  [DRY-RUN] Would update: desc={len(desc)} chars, salary={new_min}-{new_max}")
                updated += 1
                continue

            # Store full description (no truncation)
            success = storage.update_job_description_and_salary(
                job_id=job_id,
                description=desc,
                salary_min=new_min,
                salary_max=new_max,
            )
            if success:
                updated += 1
                logger.info(
                    f"  Updated: desc={len(desc)} chars, salary={new_min}-{new_max}")
            else:
                failed += 1

        except Exception as e:
            logger.error(f"  Error: {e}")
            failed += 1

    logger.info("=" * 60)
    logger.info(f"Done: {updated} updated, {failed} failed")
    if args.dry_run:
        logger.info("(Dry run - no changes written)")


if __name__ == "__main__":
    main()
