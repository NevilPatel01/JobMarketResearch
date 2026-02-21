#!/usr/bin/env python3
"""
Comprehensive job collection script to collect 5,000+ jobs.

This script systematically collects jobs from:
- 7 major Canadian cities
- 20+ tech roles
- Multiple pages per search
"""

import sys
from pathlib import Path
import time

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from collectors.jobbank_collector import JobBankCollector
from database.connection import DatabaseConnection
from database.storage import JobStorage
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Comprehensive list of cities
CITIES = [
    'Toronto', 'Montreal', 'Vancouver', 'Calgary', 'Ottawa', 'Edmonton', 'Winnipeg',
    'Quebec City', 'Hamilton', 'Kitchener', 'London', 'Halifax', 'Victoria',
    'Mississauga', 'Brampton', 'Surrey', 'Laval', 'Markham', 'Vaughan', 'Gatineau',
    'Saskatoon', 'Regina', 'Sherbrooke', 'St. John\'s', 'Barrie', 'Kelowna',
    'Abbotsford', 'Kingston', 'Guelph', 'Waterloo'
]

# Comprehensive list of tech roles
ROLES = [
    # Data & Analytics
    'data analyst', 'data scientist', 'data engineer', 'business analyst',
    'business intelligence analyst', 'data architect', 'analytics manager',
    
    # Software Development
    'software engineer', 'software developer', 'full stack developer',
    'frontend developer', 'backend developer', 'web developer',
    'mobile developer', 'application developer', 'java developer',
    'python developer', '.net developer', 'javascript developer',
    
    # DevOps & Infrastructure
    'devops engineer', 'site reliability engineer', 'cloud engineer',
    'cloud architect', 'platform engineer', 'infrastructure engineer',
    'systems engineer', 'network engineer',
    
    # Database & Systems
    'database administrator', 'database developer', 'systems analyst',
    'system administrator', 'network administrator',
    
    # Security
    'security engineer', 'cybersecurity analyst', 'information security analyst',
    
    # QA & Testing
    'qa engineer', 'quality assurance analyst', 'test engineer', 'sdet',
    
    # Management & Leadership
    'technical lead', 'engineering manager', 'product manager',
    'project manager', 'scrum master', 'agile coach',
    
    # Support & Operations
    'technical support', 'IT support', 'help desk', 'IT consultant',
    'solutions architect', 'technical architect',
    
    # Emerging Tech
    'machine learning engineer', 'AI engineer', 'ML engineer',
    'blockchain developer', 'automation engineer'
]

def collect_comprehensive_dataset(max_pages=5, delay_between_searches=1):
    """
    Collect comprehensive dataset from Job Bank Canada.
    
    Args:
        max_pages: Maximum pages to scrape per city/role combination
        delay_between_searches: Delay in seconds between searches
    """
    logger.info("="*80)
    logger.info("COMPREHENSIVE JOB COLLECTION - TARGET: 5,000+ JOBS")
    logger.info("="*80)
    
    # Initialize
    db = DatabaseConnection()
    storage = JobStorage(db)
    collector = JobBankCollector()
    
    # Get current count
    with db.get_session() as session:
        from database.models import JobRaw
        current_count = session.query(JobRaw).count()
    
    logger.info(f"\nStarting with {current_count} jobs in database")
    logger.info(f"Target: 5,000+ jobs")
    logger.info(f"Need: ~{5000 - current_count} more jobs\n")
    
    logger.info(f"Collection plan:")
    logger.info(f"  Cities: {len(CITIES)} cities")
    logger.info(f"  Roles: {len(ROLES)} roles")
    logger.info(f"  Max combinations: {len(CITIES) * len(ROLES)}")
    logger.info(f"  Pages per search: {max_pages}")
    logger.info(f"  Estimated max jobs: ~{len(CITIES) * len(ROLES) * max_pages * 25}\n")
    
    total_collected = 0
    total_inserted = 0
    search_count = 0
    
    try:
        for city in CITIES:
            for role in ROLES:
                search_count += 1
                
                logger.info(f"\n[{search_count}/{len(CITIES) * len(ROLES)}] Collecting {role} in {city}")
                
                try:
                    # Collect jobs
                    jobs = collector.collect_with_validation(city, role, max_pages)
                    total_collected += len(jobs)
                    
                    if jobs:
                        # Store jobs
                        inserted = storage.insert_raw_jobs(jobs, 'jobbank')
                        total_inserted += inserted
                        
                        # Check if we've reached target
                        with db.get_session() as session:
                            from database.models import JobRaw
                            current_total = session.query(JobRaw).count()
                        
                        logger.info(f"✓ Database now has {current_total} jobs")
                        
                        if current_total >= 5000:
                            logger.info(f"\n🎉 TARGET REACHED! Collected {current_total} jobs!")
                            break
                    
                    # Delay between searches to be respectful
                    time.sleep(delay_between_searches)
                    
                except Exception as e:
                    logger.error(f"Failed to collect {role} in {city}: {e}")
                    continue
            
            # Check if target reached (break outer loop)
            with db.get_session() as session:
                from database.models import JobRaw
                current_total = session.query(JobRaw).count()
            
            if current_total >= 5000:
                break
        
        # Final stats
        with db.get_session() as session:
            from database.models import JobRaw
            final_count = session.query(JobRaw).count()
        
        logger.info("\n" + "="*80)
        logger.info("COLLECTION COMPLETE")
        logger.info("="*80)
        logger.info(f"Starting count: {current_count}")
        logger.info(f"Jobs collected: {total_collected}")
        logger.info(f"New jobs inserted: {total_inserted}")
        logger.info(f"Final count: {final_count}")
        logger.info(f"Searches performed: {search_count}")
        logger.info("="*80)
        
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Collection interrupted by user")
        with db.get_session() as session:
            from database.models import JobRaw
            final_count = session.query(JobRaw).count()
        logger.info(f"Partial collection: {final_count} jobs in database")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Collect comprehensive job dataset')
    parser.add_argument('--pages', type=int, default=5, help='Max pages per search (default: 5)')
    parser.add_argument('--delay', type=float, default=1, help='Delay between searches in seconds (default: 1)')
    
    args = parser.parse_args()
    
    collect_comprehensive_dataset(max_pages=args.pages, delay_between_searches=args.delay)
