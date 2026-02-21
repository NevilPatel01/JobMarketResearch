"""
Feature extractor - Extract structured features from job data.

NOTE: This is a basic regex-based implementation.
For production, integrate spaCy for better NLP extraction.
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from utils import setup_logger

logger = setup_logger(__name__)


class FeatureExtractor:
    """Extract features from job postings for analysis."""
    
    # Experience level patterns
    EXP_PATTERNS = [
        r'(\d+)[\s\-]*(?:to|-)[\s\-]*(\d+)\s*(?:years?|yrs?)',
        r'(\d+)\+?\s*(?:years?|yrs?)',
        r'minimum\s*(?:of\s*)?(\d+)\s*(?:years?|yrs?)',
        r'at least\s*(\d+)\s*(?:years?|yrs?)',
    ]
    
    # Remote work patterns
    REMOTE_PATTERNS = {
        'remote': [
            r'remote',
            r'work from home',
            r'100% remote',
            r'fully remote'
        ],
        'hybrid': [
            r'hybrid',
            r'flexible work',
            r'remote.*office'
        ],
        'onsite': [
            r'on[\-\s]?site',
            r'in[\-\s]?office',
            r'office based'
        ]
    }
    
    # Common tech skills
    TECH_SKILLS = [
        'python', 'java', 'javascript', 'typescript', 'c\\+\\+', 'c#', 'golang', 'rust',
        'react', 'angular', 'vue', 'node\\.?js', 'express',
        'sql', 'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform',
        'git', 'jenkins', 'ci/cd', 'github actions',
        'pandas', 'numpy', 'scikit-learn', 'tensorflow', 'pytorch',
        'spark', 'hadoop', 'kafka', 'airflow',
        'tableau', 'power bi', 'looker', 'excel'
    ]
    
    def __init__(self):
        """Initialize feature extractor."""
        self.logger = logger
    
    def extract(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract features from a single job.
        
        Args:
            job: Job dictionary from jobs_raw table
            
        Returns:
            Features dictionary for jobs_features table
        """
        title = job.get('title', '').lower()
        description = job.get('description', '').lower()
        combined_text = f"{title} {description}"
        
        # Extract experience requirements
        exp_min, exp_max = self._extract_experience(combined_text)
        
        # Detect remote type
        remote_type = job.get('remote_type') or self._detect_remote_type(combined_text)
        
        # Extract skills mentioned
        skills_found = self._extract_skills(combined_text)
        
        # Determine role/category
        role = self._classify_role(title)
        
        return {
            'job_id': job.get('job_id'),
            'exp_min': exp_min,
            'exp_max': exp_max,
            'is_remote': remote_type in ('remote', 'hybrid') if remote_type else False,
            'skills': skills_found[:10],  # Top 10 skills (JSONB array)
            'exp_level': self._infer_exp_level(exp_min, exp_max),
            'extracted_at': datetime.now().isoformat()
        }
    
    def _extract_experience(self, text: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Extract years of experience from text.
        
        Returns:
            (min_years, max_years) tuple
        """
        for pattern in self.EXP_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            
            if matches:
                # Pattern with range (e.g., "3-5 years")
                if isinstance(matches[0], tuple) and len(matches[0]) == 2:
                    try:
                        min_exp = int(matches[0][0])
                        max_exp = int(matches[0][1])
                        return min_exp, max_exp
                    except (ValueError, IndexError):
                        continue
                
                # Pattern with single value (e.g., "5+ years")
                elif isinstance(matches[0], str):
                    try:
                        exp = int(matches[0])
                        # For "X+" patterns, assume X to X+3
                        return exp, exp + 3
                    except ValueError:
                        continue
        
        # Check for entry-level keywords
        entry_level_keywords = ['entry level', 'junior', 'graduate', 'new grad', 'intern']
        if any(keyword in text for keyword in entry_level_keywords):
            return 0, 2
        
        return None, None
    
    def _detect_remote_type(self, text: str) -> Optional[str]:
        """
        Detect remote work type from text.
        
        Returns:
            'remote', 'hybrid', 'onsite', or None
        """
        for remote_type, patterns in self.REMOTE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return remote_type
        
        return None
    
    def _extract_skills(self, text: str) -> List[str]:
        """
        Extract mentioned tech skills from text.
        
        Returns:
            List of skill names found
        """
        found_skills = []
        
        for skill in self.TECH_SKILLS:
            # Use word boundaries for exact matches
            pattern = rf'\b{skill}\b'
            if re.search(pattern, text, re.IGNORECASE):
                # Normalize skill name
                normalized = skill.replace('\\', '').replace('.', '').replace('?', '')
                found_skills.append(normalized)
        
        return found_skills
    
    def _classify_role(self, title: str) -> str:
        """
        Classify job role from title.
        
        Returns:
            Role category
        """
        title_lower = title.lower()
        
        # Role classification rules
        if any(kw in title_lower for kw in ['data scientist', 'machine learning', 'ml engineer', 'ai engineer']):
            return 'Data Scientist'
        
        if any(kw in title_lower for kw in ['data engineer', 'data pipeline', 'etl']):
            return 'Data Engineer'
        
        if any(kw in title_lower for kw in ['data analyst', 'business analyst', 'analytics']):
            return 'Data Analyst'
        
        if any(kw in title_lower for kw in ['software engineer', 'software developer', 'backend', 'frontend', 'full stack']):
            return 'Software Engineer'
        
        if any(kw in title_lower for kw in ['devops', 'site reliability', 'sre', 'platform engineer']):
            return 'DevOps Engineer'
        
        if any(kw in title_lower for kw in ['security', 'cybersecurity', 'infosec']):
            return 'Security Engineer'
        
        if any(kw in title_lower for kw in ['web developer', 'web dev']):
            return 'Web Developer'
        
        if any(kw in title_lower for kw in ['mobile', 'ios', 'android']):
            return 'Mobile Developer'
        
        if any(kw in title_lower for kw in ['qa', 'quality assurance', 'test', 'sdet']):
            return 'QA Engineer'
        
        if any(kw in title_lower for kw in ['database', 'dba']):
            return 'Database Administrator'
        
        # Default
        return 'Other'
    
    def _infer_exp_level(self, exp_min: Optional[int], exp_max: Optional[int]) -> str:
        """
        Infer experience level from years.
        
        Returns:
            'entry', 'junior', 'mid', 'senior', or 'lead'
        """
        if exp_min is None and exp_max is None:
            return 'mid'  # Default assumption
        
        avg_exp = (exp_min or 0 + exp_max or exp_min or 0) / 2.0
        
        if avg_exp <= 1:
            return 'entry'
        elif avg_exp <= 3:
            return 'junior'
        elif avg_exp <= 5:
            return 'mid'
        elif avg_exp <= 8:
            return 'senior'
        else:
            return 'lead'
    
    def extract_batch(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract features for a batch of jobs.
        
        Args:
            jobs: List of job dictionaries
            
        Returns:
            List of feature dictionaries
        """
        features = []
        
        for job in jobs:
            try:
                feature = self.extract(job)
                features.append(feature)
            except Exception as e:
                self.logger.error(f"Failed to extract features for job {job.get('job_id', 'unknown')}: {e}")
                continue
        
        self.logger.info(f"Extracted features for {len(features)}/{len(jobs)} jobs")
        
        return features
