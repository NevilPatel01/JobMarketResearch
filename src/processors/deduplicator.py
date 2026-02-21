"""
Data deduplicator - Remove duplicate job postings.
"""

import hashlib
import re
from typing import List, Dict, Any, Set, Tuple
from difflib import SequenceMatcher

from utils import setup_logger

logger = setup_logger(__name__)


class JobDeduplicator:
    """Remove duplicate job postings using multiple strategies."""
    
    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize deduplicator.
        
        Args:
            similarity_threshold: Minimum similarity (0-1) to consider jobs duplicates
        """
        self.similarity_threshold = similarity_threshold
        self.logger = logger
        self.seen_hashes: Set[str] = set()
    
    def deduplicate(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicates from job list.
        
        Args:
            jobs: List of job dictionaries
            
        Returns:
            List of unique jobs
        """
        if not jobs:
            return []
        
        unique_jobs = []
        duplicates = 0
        
        # Strategy 1: Exact job_id duplicates
        seen_ids = set()
        
        for job in jobs:
            job_id = job.get('job_id', '')
            
            # Check if we've seen this exact ID
            if job_id in seen_ids:
                duplicates += 1
                self.logger.debug(f"Duplicate job_id: {job_id}")
                continue
            
            seen_ids.add(job_id)
            unique_jobs.append(job)
        
        # Strategy 2: Content-based hashing
        final_unique = []
        seen_content = set()
        content_duplicates = 0
        
        for job in unique_jobs:
            content_hash = self._compute_content_hash(job)
            
            if content_hash in seen_content:
                content_duplicates += 1
                self.logger.debug(f"Duplicate content: {job.get('title', '')} at {job.get('company', '')}")
                continue
            
            seen_content.add(content_hash)
            final_unique.append(job)
        
        duplicates += content_duplicates
        
        self.logger.info(
            f"Deduplicated {len(jobs)} jobs: {len(final_unique)} unique, {duplicates} duplicates removed"
        )
        
        return final_unique
    
    def _compute_content_hash(self, job: Dict[str, Any]) -> str:
        """
        Compute content-based hash for job.
        
        Uses title, company, city to identify duplicates.
        """
        # Normalize title and company
        title = self._normalize_text(job.get('title', ''))
        company = self._normalize_text(job.get('company', ''))
        city = self._normalize_text(job.get('city', ''))
        
        # Create hash from key fields
        content = f"{title}::{company}::{city}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison.
        
        - Lowercase
        - Remove extra whitespace
        - Remove special characters
        """
        # Lowercase
        text = text.lower().strip()
        
        # Remove special characters (keep letters, numbers, spaces)
        text = re.sub(r'[^a-z0-9\s]', '', text)
        
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def find_near_duplicates(self, jobs: List[Dict[str, Any]]) -> List[Tuple[int, int, float]]:
        """
        Find near-duplicate pairs using fuzzy matching.
        
        Args:
            jobs: List of job dictionaries
            
        Returns:
            List of (index1, index2, similarity_score) tuples
        """
        near_dupes = []
        
        for i in range(len(jobs)):
            for j in range(i + 1, len(jobs)):
                similarity = self._compute_similarity(jobs[i], jobs[j])
                
                if similarity >= self.similarity_threshold:
                    near_dupes.append((i, j, similarity))
                    self.logger.debug(
                        f"Near-duplicate pair (similarity {similarity:.2f}): "
                        f"{jobs[i].get('title', '')} vs {jobs[j].get('title', '')}"
                    )
        
        return near_dupes
    
    def _compute_similarity(self, job1: Dict[str, Any], job2: Dict[str, Any]) -> float:
        """
        Compute similarity between two jobs.
        
        Returns:
            Similarity score (0-1)
        """
        # Same company and city is very likely a duplicate
        if (self._normalize_text(job1.get('company', '')) == self._normalize_text(job2.get('company', '')) and
            self._normalize_text(job1.get('city', '')) == self._normalize_text(job2.get('city', ''))):
            
            # Compare titles
            title1 = self._normalize_text(job1.get('title', ''))
            title2 = self._normalize_text(job2.get('title', ''))
            
            title_sim = SequenceMatcher(None, title1, title2).ratio()
            
            return title_sim
        
        return 0.0
    
    def deduplicate_against_database(
        self,
        jobs: List[Dict[str, Any]],
        existing_ids: Set[str]
    ) -> List[Dict[str, Any]]:
        """
        Remove jobs that already exist in database.
        
        Args:
            jobs: List of new jobs
            existing_ids: Set of job_ids already in database
            
        Returns:
            List of truly new jobs
        """
        new_jobs = []
        skipped = 0
        
        for job in jobs:
            job_id = job.get('job_id', '')
            
            if job_id in existing_ids:
                skipped += 1
                continue
            
            new_jobs.append(job)
        
        self.logger.info(f"Filtered {skipped} jobs already in database, {len(new_jobs)} are new")
        
        return new_jobs
