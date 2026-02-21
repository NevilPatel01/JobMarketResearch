"""
Storage layer - Database operations for job data.
"""

from typing import List, Dict, Any, Set
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database import DatabaseConnection, JobRaw, JobFeatures, ScraperMetrics
from utils import setup_logger

logger = setup_logger(__name__)


class JobStorage:
    """Handle database storage operations."""
    
    def __init__(self, db: DatabaseConnection):
        """
        Initialize storage layer.
        
        Args:
            db: Database connection instance
        """
        self.db = db
        self.logger = logger
    
    def insert_raw_jobs(self, jobs: List[Dict[str, Any]], source: str) -> int:
        """
        Insert raw jobs into database.
        
        Args:
            jobs: List of validated job dictionaries
            source: Source name for metrics
            
        Returns:
            Number of jobs inserted
        """
        if not jobs:
            return 0
        
        inserted = 0
        duplicates = 0
        errors = 0
        
        for job in jobs:
            try:
                # Fix invalid salary (min > max violates DB constraint)
                salary_min = job.get('salary_min')
                salary_max = job.get('salary_max')
                if salary_min is not None and salary_max is not None and salary_min > salary_max:
                    salary_min, salary_max = salary_max, salary_min
                    job = {**job, 'salary_min': salary_min, 'salary_max': salary_max}
                
                with self.db.get_session() as session:
                    # Check if job already exists
                    existing = session.query(JobRaw).filter_by(job_id=job['job_id']).first()
                    
                    if existing:
                        duplicates += 1
                        continue
                    
                    # Create new job record
                    job_record = JobRaw(
                        source=job['source'],
                        job_id=job['job_id'],
                        title=job['title'],
                        company=job['company'],
                        city=job['city'],
                        province=job['province'],
                        description=job.get('description', ''),
                        salary_min=job.get('salary_min'),
                        salary_max=job.get('salary_max'),
                        remote_type=job.get('remote_type'),
                        posted_date=job['posted_date'],
                        url=job['url']
                    )
                    
                    session.add(job_record)
                    session.commit()
                    inserted += 1
                    
            except IntegrityError:
                duplicates += 1
            except Exception as e:
                errors += 1
                self.logger.error(f"Failed to insert job {job.get('job_id', 'unknown')}: {e}")
        
        self.logger.info(
            f"Inserted {inserted} jobs from {source} "
            f"({duplicates} duplicates, {errors} errors)"
        )
        
        # Record metrics
        try:
            self._record_metrics(source, len(jobs), inserted, duplicates, errors)
        except Exception as e:
            self.logger.warning(f"Failed to record metrics: {e}")
        
        return inserted
    
    def insert_features(self, features: List[Dict[str, Any]]) -> int:
        """
        Insert job features into database.
        
        Args:
            features: List of feature dictionaries
            
        Returns:
            Number of features inserted
        """
        if not features:
            return 0
        
        inserted = 0
        
        with self.db.get_session() as session:
            for feature in features:
                try:
                    # Check if features already exist for this job
                    existing = session.query(JobFeatures).filter_by(
                        job_id=feature['job_id']
                    ).first()
                    
                    if existing:
                        # Update existing record
                        for key, value in feature.items():
                            if key != 'job_id' and value is not None:
                                setattr(existing, key, value)
                        inserted += 1
                    else:
                        # Create new feature record
                        feature_record = JobFeatures(
                            job_id=feature['job_id'],
                            exp_min=feature.get('exp_min'),
                            exp_max=feature.get('exp_max'),
                            exp_level=feature.get('exp_level'),
                            skills=feature.get('skills', []),
                            is_remote=feature.get('is_remote', False)
                        )
                        
                        session.add(feature_record)
                        inserted += 1
                    
                except Exception as e:
                    session.rollback()
                    self.logger.error(
                        f"Failed to insert features for job {feature.get('job_id', 'unknown')}: {e}"
                    )
            
            # Commit all inserts
            try:
                session.commit()
            except Exception as e:
                session.rollback()
                self.logger.error(f"Failed to commit features: {e}")
                return 0
        
        self.logger.info(f"Inserted/updated {inserted} job features")
        
        return inserted
    
    def get_existing_job_ids(self, source: str = None) -> Set[str]:
        """
        Get set of job IDs already in database.
        
        Args:
            source: Optional source filter
            
        Returns:
            Set of job_id strings
        """
        with self.db.get_session() as session:
            query = session.query(JobRaw.job_id)
            
            if source:
                query = query.filter_by(source=source)
            
            results = query.all()
            return {row[0] for row in results}
    
    def _record_metrics(
        self,
        source: str,
        total: int,
        inserted: int,
        duplicates: int,
        errors: int
    ):
        """Record scraper metrics."""
        import uuid
        try:
            with self.db.get_session() as session:
                metric = ScraperMetrics(
                    run_id=str(uuid.uuid4()),
                    jobs_collected=total,
                    jobs_valid=inserted,
                    jobs_duplicates=duplicates,
                    jobs_failed=errors,
                    sources_used=[source],
                    jobs_by_source={source: total},
                    status='completed' if inserted > 0 else 'failed'
                )
                
                session.add(metric)
                session.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to record metrics: {e}")
    
    def get_table_counts(self) -> Dict[str, int]:
        """
        Get row counts for all tables.
        
        Returns:
            Dictionary of {table_name: row_count}
        """
        counts = {}
        
        with self.db.get_session() as session:
            counts['jobs_raw'] = session.query(JobRaw).count()
            counts['jobs_features'] = session.query(JobFeatures).count()
            counts['scraper_metrics'] = session.query(ScraperMetrics).count()
        
        return counts
