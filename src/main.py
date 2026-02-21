#!/usr/bin/env python3
"""
Main CLI for Canada Tech Job Compass.

Commands:
    collect     - Collect jobs from all sources
    process     - Process raw jobs (validate, deduplicate, extract features)
    full        - Run full pipeline (collect + process)
    stats       - Show database statistics
"""

import click

from collectors.jobbank_collector import JobBankCollector
from processors.validator import JobValidator
from processors.deduplicator import JobDeduplicator
from processors.feature_extractor import FeatureExtractor
from database.connection import DatabaseConnection
from database.storage import JobStorage
from utils.config import Config
from utils.logger import setup_logger

logger = setup_logger(__name__)


# Target cities and roles
CITIES = ['Toronto', 'Vancouver', 'Calgary', 'Ottawa', 'Edmonton', 'Montreal', 'Winnipeg']
ROLES = ['data analyst', 'data scientist', 'data engineer', 'software engineer', 'devops engineer', 'web developer', 'business analyst']


@click.group()
def cli():
    """Canada Tech Job Compass - Job Market Analysis Pipeline"""
    pass


@cli.command()
@click.option('--city', multiple=True, help='City to collect from (can specify multiple)')
@click.option('--role', multiple=True, help='Role to search for (can specify multiple)')
@click.option('--pages', default=3, help='Max pages per search')
@click.option('--source', type=click.Choice(['jobbank', 'rapidapi', 'rss', 'all']), default='all')
def collect(city, role, pages, source):
    """Collect jobs from sources."""
    logger.info("="*80)
    logger.info("STARTING JOB COLLECTION")
    logger.info("="*80)
    
    # Use defaults if not specified
    cities = list(city) if city else CITIES[:3]  # First 3 cities as default
    roles = list(role) if role else ROLES[:2]   # First 2 roles as default
    
    logger.info(f"Cities: {', '.join(cities)}")
    logger.info(f"Roles: {', '.join(roles)}")
    logger.info(f"Max pages: {pages}")
    logger.info(f"Source: {source}")
    
    # Initialize database
    db = DatabaseConnection()
    storage = JobStorage(db)
    
    all_jobs = []
    
    # Collect from Job Bank
    if source in ('jobbank', 'all'):
        collector = JobBankCollector()
        
        for c in cities:
            for r in roles:
                logger.info(f"\n📥 Collecting {r} jobs in {c} from Job Bank...")
                jobs = collector.collect_with_validation(c, r, pages)
                all_jobs.extend(jobs)
                logger.info(f"✓ Collected {len(jobs)} jobs")
    
    logger.info(f"\n{'='*80}")
    logger.info(f"TOTAL COLLECTED: {len(all_jobs)} jobs")
    logger.info(f"{'='*80}")
    
    if not all_jobs:
        logger.warning("No jobs collected!")
        return
    
    # Store raw jobs
    logger.info("\n💾 Storing jobs in database...")
    inserted = storage.insert_raw_jobs(all_jobs, 'jobbank')
    logger.info(f"✓ Inserted {inserted} new jobs")
    
    # Show stats
    counts = storage.get_table_counts()
    logger.info(f"\nDatabase stats:")
    for table, count in counts.items():
        logger.info(f"  {table}: {count} rows")


@cli.command()
@click.option('--limit', default=0, help='Limit number of jobs to process (0 = all)')
def process(limit):
    """Process raw jobs (validate, deduplicate, extract features)."""
    logger.info("="*80)
    logger.info("STARTING JOB PROCESSING")
    logger.info("="*80)
    
    # Initialize
    db = DatabaseConnection()
    storage = JobStorage(db)
    validator = JobValidator(strict_mode=False)
    deduplicator = JobDeduplicator()
    extractor = FeatureExtractor()
    
    # Get raw jobs that don't have features yet
    with db.get_session() as session:
        from database.models import JobRaw, JobFeatures
        from sqlalchemy import and_
        
        query = session.query(JobRaw).outerjoin(
            JobFeatures,
            JobRaw.job_id == JobFeatures.job_id
        ).filter(JobFeatures.job_id.is_(None))
        
        if limit > 0:
            query = query.limit(limit)
        
        raw_jobs = query.all()
        
        # Convert to dictionaries
        jobs = [{
            'source': j.source,
            'job_id': j.job_id,
            'title': j.title,
            'company': j.company,
            'city': j.city,
            'province': j.province,
            'description': j.description or '',
            'salary_min': j.salary_min,
            'salary_max': j.salary_max,
            'remote_type': j.remote_type,
            'posted_date': j.posted_date.isoformat() if j.posted_date else '',
            'url': j.url
        } for j in raw_jobs]
    
    logger.info(f"Found {len(jobs)} unprocessed jobs")
    
    if not jobs:
        logger.info("No jobs to process!")
        return
    
    # Step 1: Validate
    logger.info("\n✓ Validating jobs...")
    valid_jobs, invalid_jobs = validator.validate_batch(jobs)
    logger.info(f"  Valid: {len(valid_jobs)}, Invalid: {len(invalid_jobs)}")
    
    # Step 2: Deduplicate
    logger.info("\n✓ Deduplicating jobs...")
    unique_jobs = deduplicator.deduplicate(valid_jobs)
    logger.info(f"  Unique: {len(unique_jobs)}")
    
    # Step 3: Extract features
    logger.info("\n✓ Extracting features...")
    features = extractor.extract_batch(unique_jobs)
    logger.info(f"  Extracted: {len(features)} feature sets")
    
    # Step 4: Store features
    logger.info("\n💾 Storing features in database...")
    inserted = storage.insert_features(features)
    logger.info(f"✓ Inserted {inserted} feature records")
    
    # Step 5: Refresh Power BI view
    logger.info("\n🔄 Refreshing Power BI view...")
    storage.refresh_powerbi_view()
    logger.info("✓ Power BI view refreshed")
    
    # Show stats
    counts = storage.get_table_counts()
    logger.info(f"\nDatabase stats:")
    for table, count in counts.items():
        logger.info(f"  {table}: {count} rows")


@cli.command()
@click.option('--cities', default=3, help='Number of cities to collect from')
@click.option('--roles', default=2, help='Number of roles to search for')
@click.option('--pages', default=3, help='Max pages per search')
def full(cities, roles, pages):
    """Run full pipeline (collect + process)."""
    logger.info("="*80)
    logger.info("RUNNING FULL PIPELINE")
    logger.info("="*80)
    
    # Step 1: Collect
    logger.info("\n" + "="*80)
    logger.info("PHASE 1: COLLECTION")
    logger.info("="*80)
    
    target_cities = CITIES[:cities]
    target_roles = ROLES[:roles]
    
    ctx = click.Context(collect)
    ctx.invoke(collect, city=target_cities, role=target_roles, pages=pages, source='all')
    
    # Step 2: Process
    logger.info("\n" + "="*80)
    logger.info("PHASE 2: PROCESSING")
    logger.info("="*80)
    
    ctx = click.Context(process)
    ctx.invoke(process, limit=0)
    
    logger.info("\n" + "="*80)
    logger.info("✅ FULL PIPELINE COMPLETE")
    logger.info("="*80)


@cli.command()
def stats():
    """Show database statistics."""
    db = DatabaseConnection()
    storage = JobStorage(db)
    
    logger.info("="*80)
    logger.info("DATABASE STATISTICS")
    logger.info("="*80)
    
    counts = storage.get_table_counts()
    
    logger.info(f"\nTable counts:")
    for table, count in counts.items():
        logger.info(f"  {table:20s}: {count:6d} rows")
    
    # Get source breakdown
    with db.get_session() as session:
        from database.models import JobRaw
        from sqlalchemy import func
        
        source_counts = session.query(
            JobRaw.source,
            func.count(JobRaw.job_id).label('count')
        ).group_by(JobRaw.source).all()
        
        logger.info(f"\nJobs by source:")
        for source, count in source_counts:
            logger.info(f"  {source:20s}: {count:6d} jobs")
        
        # Get city breakdown
        city_counts = session.query(
            JobRaw.city,
            func.count(JobRaw.job_id).label('count')
        ).group_by(JobRaw.city).order_by(func.count(JobRaw.job_id).desc()).limit(10).all()
        
        logger.info(f"\nTop 10 cities:")
        for city, count in city_counts:
            logger.info(f"  {city:20s}: {count:6d} jobs")


if __name__ == '__main__':
    cli()
