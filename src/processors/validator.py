"""
Data validator - Quality checks for job data.
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

from utils import setup_logger

logger = setup_logger(__name__)


class JobValidator:
    """Validates job data quality with comprehensive checks."""
    
    # Canadian provinces
    VALID_PROVINCES = {'ON', 'BC', 'AB', 'SK', 'MB', 'QC', 'NS', 'NB', 'NL', 'PE', 'NT', 'NU', 'YT'}
    
    # Major Canadian cities
    MAJOR_CITIES = {
        'Toronto', 'Vancouver', 'Calgary', 'Ottawa', 'Edmonton', 'Montreal', 'Montréal',
        'Winnipeg', 'Saskatchewan', 'Quebec', 'Québec', 'Halifax', 'Victoria', 'Regina',
        'St. John\'s', 'Fredericton', 'Charlottetown', 'Whitehorse', 'Yellowknife', 'Iqaluit',
        'Mississauga', 'Brampton', 'Hamilton', 'Surrey', 'Laval', 'London', 'Markham',
        'Vaughan', 'Kitchener', 'Windsor', 'Richmond', 'Burnaby', 'Waterloo', 'Saskatoon',
        'Ayr', 'Port Coquitlam', 'Lethbridge'  # Added from sample data
    }
    
    # Suspicious patterns
    SPAM_PATTERNS = [
        r'work from home',
        r'make \$\d+',
        r'click here',
        r'limited time',
        r'act now',
        r'guaranteed',
        r'100% remote.*no experience'
    ]
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize validator.
        
        Args:
            strict_mode: If True, apply stricter validation rules
        """
        self.strict_mode = strict_mode
        self.logger = logger
    
    def validate(self, job: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate job data quality.
        
        Args:
            job: Job dictionary
            
        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []
        
        # Rule 1: Required fields present
        if not self._check_required_fields(job):
            issues.append("Missing required fields")
        
        # Rule 2: Province code valid
        province = job.get('province', '')
        if province and province not in self.VALID_PROVINCES:
            issues.append(f"Invalid province code: {province}")
        
        # Rule 3: City name reasonable
        city = job.get('city', '')
        if not self._is_valid_city(city):
            issues.append(f"Invalid city name: {city}")
        
        # Rule 4: Salary range logical
        salary_min = job.get('salary_min')
        salary_max = job.get('salary_max')
        if not self._is_valid_salary_range(salary_min, salary_max):
            issues.append(f"Invalid salary range: {salary_min} - {salary_max}")
        
        # Rule 5: Posted date recent
        posted_date = job.get('posted_date', '')
        if not self._is_recent_date(posted_date):
            issues.append(f"Suspicious posted date: {posted_date}")
        
        # Rule 6: URL valid
        url = job.get('url', '')
        if not self._is_valid_url(url):
            issues.append(f"Invalid URL: {url}")
        
        # Rule 7: Title reasonable length
        title = job.get('title', '')
        if not (3 <= len(title) <= 150):
            issues.append(f"Invalid title length: {len(title)}")
        
        # Rule 8: Company name reasonable
        company = job.get('company', '')
        if not self._is_valid_company(company):
            issues.append(f"Invalid company name: {company}")
        
        # Rule 9: Not spam (strict mode only)
        if self.strict_mode:
            if self._is_spam(job):
                issues.append("Detected spam patterns")
        
        # Rule 10: Job ID format correct
        job_id = job.get('job_id', '')
        source = job.get('source', '')
        if not job_id.startswith(f"{source}_"):
            issues.append(f"Job ID doesn't match source: {job_id} vs {source}")
        
        is_valid = len(issues) == 0
        
        if not is_valid:
            self.logger.debug(f"Validation failed for job {job.get('job_id', 'unknown')}: {', '.join(issues)}")
        
        return is_valid, issues
    
    def _check_required_fields(self, job: Dict[str, Any]) -> bool:
        """Check if all required fields are present."""
        required = ['source', 'job_id', 'title', 'company', 'city', 'province', 'posted_date', 'url']
        return all(key in job and job[key] for key in required)
    
    def _is_valid_city(self, city: str) -> bool:
        """Check if city name is valid."""
        if not city or len(city) < 2:
            return False
        
        # Check if it's a known major city
        if city in self.MAJOR_CITIES:
            return True
        
        # Check if it looks like a city name (letters, spaces, hyphens, apostrophes)
        if re.match(r"^[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\-'.]+$", city):
            return True
        
        return False
    
    # Minimum plausible annual salary - filter out $8-$35 style hourly misparsed as annual
    MIN_ANNUAL_SALARY = 10000

    def _is_valid_salary_range(self, min_sal: Optional[int], max_sal: Optional[int]) -> bool:
        """Check if salary range is logical (annual CAD)."""
        # Null salaries are OK
        if min_sal is None and max_sal is None:
            return True
        
        # If only one is set, it should be reasonable
        if min_sal is not None and max_sal is None:
            if min_sal < self.MIN_ANNUAL_SALARY:
                return False  # Reject $8, $35 etc.
            return 0 <= min_sal <= 500000
        
        if min_sal is None and max_sal is not None:
            if max_sal < self.MIN_ANNUAL_SALARY:
                return False
            return 0 <= max_sal <= 500000
        
        # Both set - check range
        if min_sal > max_sal:
            return False
        
        # Reject suspiciously low (hourly misparsed as annual)
        if max_sal < self.MIN_ANNUAL_SALARY:
            return False
        
        if not (0 <= min_sal <= 500000):
            return False
        
        if not (0 <= max_sal <= 500000):
            return False
        
        # Check range not too wide (max 100x difference)
        if min_sal > 0 and max_sal > min_sal * 100:
            return False
        
        return True
    
    def _is_recent_date(self, date_str: str) -> bool:
        """Check if posted date is recent (within 90 days)."""
        if not date_str:
            return False
        
        try:
            posted = datetime.fromisoformat(date_str).date()
            today = datetime.now().date()
            
            # Not in the future
            if posted > today:
                return False
            
            # Within 90 days
            age_days = (today - posted).days
            return age_days <= 90
            
        except (ValueError, TypeError):
            return False
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid."""
        if not url:
            return False
        
        # Must start with http/https
        if not url.startswith(('http://', 'https://')):
            return False
        
        # Must have a domain
        if not re.search(r'https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}', url):
            return False
        
        return True
    
    def _is_valid_company(self, company: str) -> bool:
        """Check if company name is reasonable."""
        if not company or company.lower() in ('unknown', 'n/a', 'na'):
            return False
        
        # At least 2 characters
        if len(company) < 2:
            return False
        
        # Not just numbers
        if company.isdigit():
            return False
        
        return True
    
    def _is_spam(self, job: Dict[str, Any]) -> bool:
        """Check if job looks like spam."""
        text = f"{job.get('title', '')} {job.get('company', '')} {job.get('description', '')}".lower()
        
        for pattern in self.SPAM_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def validate_batch(self, jobs: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Validate a batch of jobs.
        
        Args:
            jobs: List of job dictionaries
            
        Returns:
            Tuple of (valid_jobs, invalid_jobs)
        """
        valid = []
        invalid = []
        
        for job in jobs:
            is_valid, issues = self.validate(job)
            
            if is_valid:
                valid.append(job)
            else:
                job['validation_issues'] = issues
                invalid.append(job)
        
        self.logger.info(f"Validated {len(jobs)} jobs: {len(valid)} valid, {len(invalid)} invalid")
        
        return valid, invalid
