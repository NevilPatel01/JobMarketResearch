"""
Simple CLI to test job collection.
"""

import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.collectors import JobBankCollector, RapidAPICollector, IndeedRSSCollector
from src.database import get_db, JobRaw
from src.utils import setup_logger, Config

logger = setup_logger(__name__)


def test_collection():
    """Test collecting jobs from all sources."""
    logger.info("=" * 60)
    logger.info("JOB COLLECTION TEST")
    logger.info("=" * 60)
    
    # Test city and role
    city = "Toronto"
    role = "data analyst"
    
    all_jobs = []
    
    # Test Job Bank
    if Config.ENABLE_JOBBANK:
        logger.info(f"\n[1/3] Testing Job Bank collector...")
        try:
            collector = JobBankCollector()
            jobs = collector.collect_with_validation(city, role, max_pages=1)
            logger.info(f"✓ Job Bank: Collected {len(jobs)} jobs")
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"✗ Job Bank failed: {e}")
    
    # Test RapidAPI
    if Config.ENABLE_RAPIDAPI:
        logger.info(f"\n[2/3] Testing RapidAPI collector...")
        try:
            collector = RapidAPICollector()
            jobs = collector.collect_with_validation(city, role)
            logger.info(f"✓ RapidAPI: Collected {len(jobs)} jobs")
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"✗ RapidAPI failed: {e}")
    
    # Test Indeed RSS
    if Config.ENABLE_RSS:
        logger.info(f"\n[3/3] Testing Indeed RSS collector...")
        try:
            collector = IndeedRSSCollector()
            jobs = collector.collect_with_validation(city, role)
            logger.info(f"✓ Indeed RSS: Collected {len(jobs)} jobs")
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"✗ Indeed RSS failed: {e}")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"TOTAL JOBS COLLECTED: {len(all_jobs)}")
    logger.info(f"{'='*60}")
    
    if all_jobs:
        # Show sample jobs
        logger.info("\nSample jobs:")
        for i, job in enumerate(all_jobs[:3], 1):
            logger.info(f"\n{i}. {job['title']}")
            logger.info(f"   Company: {job['company']}")
            logger.info(f"   Location: {job['city']}, {job['province']}")
            logger.info(f"   Source: {job['source']}")
            logger.info(f"   Posted: {job['posted_date']}")
        
        # Test database insertion
        logger.info(f"\n{'='*60}")
        logger.info("TESTING DATABASE INSERTION")
        logger.info(f"{'='*60}")
        
        try:
            db = get_db()
            with db.get_session() as session:
                # Insert first 5 jobs as test
                for job in all_jobs[:5]:
                    job_raw = JobRaw(
                        source=job['source'],
                        job_id=job['job_id'],
                        title=job['title'],
                        company=job['company'],
                        city=job['city'],
                        province=job['province'],
                        description=job['description'],
                        salary_min=job.get('salary_min'),
                        salary_max=job.get('salary_max'),
                        remote_type=job.get('remote_type'),
                        posted_date=job['posted_date'],
                        url=job['url']
                    )
                    session.merge(job_raw)  # Use merge to avoid duplicates
                
                session.commit()
                logger.info(f"✓ Successfully inserted {min(5, len(all_jobs))} jobs into database")
                
                # Check counts
                counts = db.get_table_counts()
                logger.info(f"\nDatabase status:")
                for table, count in counts.items():
                    logger.info(f"  {table}: {count} rows")
                
        except Exception as e:
            logger.error(f"✗ Database insertion failed: {e}", exc_info=True)
    
    return len(all_jobs) > 0


if __name__ == '__main__':
    success = test_collection()
    sys.exit(0 if success else 1)
