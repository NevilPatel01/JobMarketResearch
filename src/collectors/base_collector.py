"""
Base collector class - Abstract base for all job collectors.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

from ..utils import setup_logger

logger = setup_logger(__name__)


class BaseCollector(ABC):
    """Abstract base class for all data collectors."""
    
    # Required keys that all collectors must return
    REQUIRED_KEYS = [
        'source',        # 'jobbank', 'rapidapi', 'indeed', 'workopolis'
        'job_id',        # Unique ID (source_prefix + original_id)
        'title',         # Job title
        'company',       # Company name
        'city',          # Normalized city name
        'province',      # 2-letter code: ON, SK, AB, BC, MB
        'description',   # Full job description (HTML stripped)
        'posted_date',   # ISO format: 2026-02-15
        'url'            # Direct job posting URL
    ]
    
    # Optional keys (can be None)
    OPTIONAL_KEYS = ['salary_min', 'salary_max', 'remote_type']
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize base collector.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = setup_logger(self.__class__.__name__)
    
    @abstractmethod
    def collect(self, city: str, role: str, max_pages: int = 5) -> List[Dict[str, Any]]:
        """
        Collect jobs from source.
        
        Args:
            city: Canadian city name (e.g., 'Toronto')
            role: Job role keyword (e.g., 'data analyst')
            max_pages: Maximum pages to scrape
            
        Returns:
            List of job dictionaries with standardized keys
        """
        pass
    
    def validate_job(self, job: Dict[str, Any]) -> bool:
        """
        Validate that job has all required fields.
        
        Args:
            job: Job dictionary
            
        Returns:
            True if valid, False otherwise
        """
        # Check required keys
        for key in self.REQUIRED_KEYS:
            if key not in job or job[key] is None or job[key] == '':
                self.logger.warning(f"Job missing required key: {key}")
                return False
        
        # Check job_id format (should start with source name)
        source = job.get('source', '')
        job_id = job.get('job_id', '')
        if not job_id.startswith(f"{source}_"):
            self.logger.warning(f"Invalid job_id format: {job_id} (should start with {source}_)")
            return False
        
        return True
    
    def collect_with_validation(self, city: str, role: str, max_pages: int = 5) -> List[Dict[str, Any]]:
        """
        Collect jobs and filter out invalid ones.
        
        Args:
            city: Canadian city name
            role: Job role keyword
            max_pages: Maximum pages to scrape
            
        Returns:
            List of validated job dictionaries
        """
        self.logger.info(f"Starting collection: {city} - {role}")
        
        try:
            jobs = self.collect(city, role, max_pages)
            
            # Validate and filter
            valid_jobs = []
            for job in jobs:
                if self.validate_job(job):
                    valid_jobs.append(job)
            
            invalid_count = len(jobs) - len(valid_jobs)
            if invalid_count > 0:
                self.logger.warning(f"Filtered {invalid_count} invalid jobs")
            
            self.logger.info(f"Collected {len(valid_jobs)} valid jobs")
            return valid_jobs
            
        except Exception as e:
            self.logger.error(f"Collection failed: {e}", exc_info=True)
            return []
