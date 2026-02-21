#!/usr/bin/env python3
"""
Multi-source job collection - Job Bank + JSearch + LinkedIn + Adzuna + Indeed + Workopolis.

Reaches 5,000+ jobs by combining multiple data sources.
- RAPIDAPI_KEY: JSearch + LinkedIn Jobs (separate RapidAPI subscriptions)
- ADZUNA_APP_ID, ADZUNA_APP_KEY: Free at developer.adzuna.com
"""

import sys
from pathlib import Path
import time

src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from collectors.jobbank_collector import JobBankCollector
from collectors.jsearch_collector import JSearchCollector
from collectors.rapidapi_collector import RapidAPICollector
from collectors.adzuna_collector import AdzunaCollector
from collectors.remoteok_collector import RemoteOKCollector
from collectors.rss_collectors import IndeedRSSCollector, WorkopolisRSSCollector
from database.connection import DatabaseConnection
from database.storage import JobStorage
from utils.config import Config
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Cities and roles - expanded for better coverage
CITIES = ['Toronto', 'Montreal', 'Vancouver', 'Calgary', 'Ottawa', 'Edmonton', 'Winnipeg', 'Saskatoon']
ROLES = [
    'data analyst', 'data scientist', 'software engineer', 'devops engineer',
    'business analyst', 'web developer', 'full stack developer', 'cloud engineer',
    'product manager', 'QA engineer', 'data engineer', 'machine learning engineer',
    'backend developer', 'frontend developer', 'mobile developer', 'security engineer'
]


def collect_from_source(collector, storage, db, source_name: str, cities: list, roles: list, max_pages: int):
    """Collect from a single source and return (collected_count, inserted_count)."""
    total_collected = 0
    total_inserted = 0
    
    for city in cities:
        for role in roles:
            try:
                jobs = collector.collect_with_validation(city, role, max_pages)
                total_collected += len(jobs)
                if jobs:
                    inserted = storage.insert_raw_jobs(jobs, source_name)
                    total_inserted += inserted
                    
                    with db.get_session() as session:
                        from database.models import JobRaw
                        current = session.query(JobRaw).count()
                    logger.info(f"  {source_name}: {current} total jobs | +{inserted} new")
                    
                    if current >= 5000:
                        return total_collected, total_inserted, True
                        
            except Exception as e:
                logger.warning(f"  {source_name} failed for {role} in {city}: {e}")
            time.sleep(0.5)  # Brief delay between requests
            
    return total_collected, total_inserted, False


def main():
    """Run multi-source collection."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Collect jobs from multiple sources')
    parser.add_argument('--sources', nargs='+', 
                        default=['jobbank', 'jsearch', 'linkedin', 'adzuna', 'remoteok', 'indeed', 'workopolis'],
                        help='Sources: jobbank, jsearch, linkedin, adzuna, remoteok, indeed, workopolis (default: all)')
    parser.add_argument('--pages', type=int, default=3, help='Pages per Job Bank search')
    parser.add_argument('--target', type=int, default=5000, help='Target job count')
    
    args = parser.parse_args()
    
    logger.info("="*80)
    logger.info("MULTI-SOURCE JOB COLLECTION - TARGET: 5,000+ JOBS")
    logger.info("="*80)
    
    db = DatabaseConnection()
    storage = JobStorage(db)
    
    with db.get_session() as session:
        from database.models import JobRaw
        start_count = session.query(JobRaw).count()
    
    logger.info(f"\nStarting with {start_count} jobs")
    logger.info(f"Sources: {', '.join(args.sources)}\n")
    
    target_reached = False
    total_inserted = 0
    
    # 1. Job Bank (always works, no API key needed)
    if 'jobbank' in args.sources:
        logger.info("\n📥 SOURCE 1: Job Bank Canada")
        collector = JobBankCollector()
        _, inserted, target_reached = collect_from_source(
            collector, storage, db, 'jobbank',
            CITIES, ROLES, args.pages
        )
        total_inserted += inserted
        if target_reached:
            logger.info("\n🎉 TARGET REACHED!")
            return
    
    # 2. JSearch API (subscribe at rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)
    if 'jsearch' in args.sources and Config.RAPIDAPI_KEY and not target_reached:
        logger.info("\n📥 SOURCE 2: JSearch API (RapidAPI)")
        try:
            collector = JSearchCollector()
            _, inserted, target_reached = collect_from_source(
                collector, storage, db, 'jsearch',
                CITIES[:6], ROLES[:10], 3  # Expanded: more cities, roles, pages
            )
            total_inserted += inserted
            if target_reached:
                logger.info("\n🎉 TARGET REACHED!")
                return
        except Exception as e:
            logger.warning(f"JSearch failed: {e}")
            logger.info("  Tip: Subscribe to JSearch at RapidAPI, add RAPIDAPI_KEY to .env")

    # 3. LinkedIn Jobs (RapidAPI - uses RAPIDAPI_HOST=linkedin-jobs.p.rapidapi.com)
    if 'linkedin' in args.sources and Config.RAPIDAPI_KEY and not target_reached:
        logger.info("\n📥 SOURCE 3: LinkedIn Jobs API (RapidAPI)")
        try:
            collector = RapidAPICollector()
            _, inserted, target_reached = collect_from_source(
                collector, storage, db, 'rapidapi',
                CITIES[:6], ROLES[:8], 2
            )
            total_inserted += inserted
            if target_reached:
                logger.info("\n🎉 TARGET REACHED!")
                return
        except Exception as e:
            logger.warning(f"LinkedIn Jobs failed: {e}")
            logger.info("  Tip: Subscribe to LinkedIn Jobs at RapidAPI, set RAPIDAPI_HOST in .env")

    # 4. Adzuna (free - register at developer.adzuna.com)
    if 'adzuna' in args.sources and Config.ADZUNA_APP_ID and Config.ADZUNA_APP_KEY and not target_reached:
        logger.info("\n📥 SOURCE 4: Adzuna API (free)")
        try:
            collector = AdzunaCollector()
            _, inserted, target_reached = collect_from_source(
                collector, storage, db, 'adzuna',
                CITIES[:6], ROLES, 3
            )
            total_inserted += inserted
            if target_reached:
                logger.info("\n🎉 TARGET REACHED!")
                return
        except Exception as e:
            logger.warning(f"Adzuna failed: {e}")
            logger.info("  Tip: Register at developer.adzuna.com, add ADZUNA_APP_ID and ADZUNA_APP_KEY to .env")

    # 5. RemoteOK (free, no key - remote jobs)
    if 'remoteok' in args.sources and not target_reached:
        logger.info("\n📥 SOURCE 5: RemoteOK (free, no key)")
        try:
            collector = RemoteOKCollector()
            jobs = collector.collect_all_roles(ROLES)
            valid = [j for j in jobs if collector.validate_job(j)]
            if valid:
                inserted = storage.insert_raw_jobs(valid, 'remoteok')
                total_inserted += inserted
                with db.get_session() as session:
                    from database.models import JobRaw
                    current = session.query(JobRaw).count()
                logger.info(f"  remoteok: {current} total jobs | +{inserted} new")
                if current >= 5000:
                    target_reached = True
        except Exception as e:
            logger.warning(f"RemoteOK failed: {e}")

    # 6. Indeed RSS (may be limited by Indeed)
    if 'indeed' in args.sources and not target_reached:
        logger.info("\n📥 SOURCE 6: Indeed RSS")
        try:
            collector = IndeedRSSCollector()
            _, inserted, target_reached = collect_from_source(
                collector, storage, db, 'indeed',
                CITIES[:6], ROLES[:8], 1
            )
            total_inserted += inserted
            if target_reached:
                logger.info("\n🎉 TARGET REACHED!")
                return
        except Exception as e:
            logger.warning(f"Indeed RSS failed: {e}")

    # 7. Workopolis RSS (may return HTML - feed deprecated)
    if 'workopolis' in args.sources and not target_reached:
        logger.info("\n📥 SOURCE 7: Workopolis RSS")
        try:
            collector = WorkopolisRSSCollector()
            workopolis_cities = ['Toronto', 'Ottawa', 'Calgary', 'Vancouver', 'Montreal', 'Saskatoon', 'Regina', 'Winnipeg']
            _, inserted, target_reached = collect_from_source(
                collector, storage, db, 'workopolis',
                workopolis_cities, ROLES[:6], 1
            )
            total_inserted += inserted
        except Exception as e:
            logger.warning(f"Workopolis failed: {e}")
    
    # Final stats
    with db.get_session() as session:
        from database.models import JobRaw
        final_count = session.query(JobRaw).count()
    
    logger.info("\n" + "="*80)
    logger.info("COLLECTION COMPLETE")
    logger.info("="*80)
    logger.info(f"Starting: {start_count} | New: +{total_inserted} | Final: {final_count}")
    logger.info("="*80)
    
    if final_count < args.target:
        logger.info(f"\n💡 To reach {args.target}+ jobs:")
        logger.info("   1. JSearch: Subscribe at rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch")
        logger.info("   2. LinkedIn Jobs: Subscribe at rapidapi.com (RAPIDAPI_HOST=linkedin-jobs.p.rapidapi.com)")
        logger.info("   3. Adzuna: Free at developer.adzuna.com — add ADZUNA_APP_ID, ADZUNA_APP_KEY")
        logger.info("   4. RemoteOK: Free, no key — remote jobs (already included)")
        logger.info("   5. Run collect_5000.py for more Job Bank jobs (no API key)")


if __name__ == '__main__':
    main()
