"""
JSearch API collector - Real-time job listings from RapidAPI.

JSearch aggregates jobs from Google for Jobs, LinkedIn, Indeed, and others.
Supports Canada via location parameter.
Subscribe at: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
"""

import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

import requests

from .base_collector import BaseCollector
from utils import Config, retry_on_exception


class JSearchCollector(BaseCollector):
    """Collect jobs from JSearch API (RapidAPI)."""
    
    BASE_URL = "https://jsearch.p.rapidapi.com/search"
    HOST = "jsearch.p.rapidapi.com"
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize JSearch collector."""
        super().__init__(config or {})
        
        self.api_key = Config.RAPIDAPI_KEY
        self.headers = {
            'X-RapidAPI-Key': self.api_key,
            'X-RapidAPI-Host': self.HOST
        }
        
        if not self.api_key:
            self.logger.warning("RAPIDAPI_KEY not configured for JSearch")
    
    def _get_host(self) -> str:
        """Allow override via RAPIDAPI_JSEARCH_HOST env var."""
        import os
        return os.getenv('RAPIDAPI_JSEARCH_HOST', self.HOST)
    
    @retry_on_exception(
        exceptions=(requests.Timeout, requests.ConnectionError),
        max_attempts=Config.MAX_RETRIES
    )
    def _fetch_jobs(self, params: Dict[str, Any]) -> Optional[Dict]:
        """
        Fetch jobs from JSearch API.
        
        Args:
            params: Query parameters
            
        Returns:
            API response as dictionary, or None if failed
        """
        if not self.api_key:
            return None
            
        host = self._get_host()
        headers = {**self.headers, 'X-RapidAPI-Host': host}
        
        try:
            response = requests.get(
                self.BASE_URL,
                headers=headers,
                params=params,
                timeout=Config.JOBBANK_REQUEST_TIMEOUT
            )
            
            if response.status_code == 429:
                self.logger.warning("JSearch API rate limit exceeded - wait or upgrade plan")
                return None
            
            if response.status_code in (401, 403):
                self.logger.error(
                    "JSearch API auth failed. Subscribe at: "
                    "https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch"
                )
                return None
            
            if response.status_code == 404:
                self.logger.error("JSearch API not found - subscribe at rapidapi.com")
                return None
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"JSearch API HTTP error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"JSearch API error: {e}")
            return None
    
    def collect(self, city: str, role: str, max_pages: int = 3) -> List[Dict[str, Any]]:
        """
        Collect jobs from JSearch API.
        
        Args:
            city: Canadian city name
            role: Job role keyword
            max_pages: Number of pages to fetch (JSearch returns ~10 jobs/page)
            
        Returns:
            List of job dictionaries
        """
        self.logger.info(f"Fetching from JSearch: {role} in {city}")
        
        all_jobs = []
        
        for page in range(max_pages):
            params = {
                'query': f"{role} in {city}, Canada",
                'page': str(page + 1),
                'num_pages': '1',
                'date_posted': 'month'
            }
            
            data = self._fetch_jobs(params)
            
            if not data:
                break
            
            # JSearch returns { "data": [ {...}, ... ] } or { "jobs": [...] }
            job_list = data.get('data', data.get('jobs', data.get('results', [])))
            
            if not job_list:
                break
            
            for job_data in job_list:
                try:
                    job = self._parse_job(job_data, city)
                    if job:
                        all_jobs.append(job)
                except Exception as e:
                    self.logger.debug(f"Failed to parse JSearch job: {e}")
                    continue
        
        self.logger.info(f"Collected {len(all_jobs)} jobs from JSearch")
        return all_jobs
    
    def _parse_job(self, data: Dict, default_city: str) -> Optional[Dict[str, Any]]:
        """
        Parse single job from JSearch response.
        
        JSearch response structure (typical):
        {
            "job_id": "...",
            "employer_name": "...",
            "job_title": "...",
            "job_city": "...",
            "job_state": "...",
            "job_country": "...",
            "job_posted_at_datetime_utc": "...",
            "job_employment_type": "...",
            "job_description": "...",
            "job_apply_link": "...",
            "job_salary_currency": "CAD",
            "job_salary_period": "YEAR",
            "job_min_salary": 80000,
            "job_max_salary": 120000
        }
        """
        try:
            job_id_raw = data.get('job_id') or data.get('id')
            if job_id_raw is not None:
                job_id = str(job_id_raw)
            else:
                job_id = hashlib.md5(
                    str(data.get('job_apply_link', data.get('link', ''))).encode()
                ).hexdigest()[:12]
            
            title = data.get('job_title') or data.get('title') or data.get('position', '')
            if not title:
                return None
            
            company_raw = data.get('employer_name') or data.get('company_name') or data.get('company')
            if isinstance(company_raw, dict):
                company = company_raw.get('name', company_raw.get('title', 'Unknown'))
            else:
                company = company_raw or data.get('employer') or 'Unknown'
            
            # Location - JSearch uses job_city, job_state; others may differ
            loc = data.get('location')
            city = data.get('job_city') or data.get('city') or (loc.get('city') if isinstance(loc, dict) else None) or default_city
            state = data.get('job_state') or data.get('state') or (loc.get('state') if isinstance(loc, dict) else '')
            country = data.get('job_country') or data.get('country', '')
            
            # Map state/province to code
            province = self._normalize_province(state, city)
            
            # Use default city if no city in response
            if not city:
                city = default_city
            
            # Posted date
            posted_raw = data.get('job_posted_at_datetime_utc') or data.get('job_posted_at', '')
            posted_date = self._parse_date(posted_raw)
            
            # Salary
            salary_min = data.get('job_min_salary')
            salary_max = data.get('job_max_salary')
            if salary_min is not None and salary_max is not None and salary_min > salary_max:
                salary_min, salary_max = salary_max, salary_min
            
            # URL
            url = data.get('job_apply_link') or data.get('link', '')
            if not url and data.get('job_id'):
                url = f"https://www.google.com/search?q=jobs+{job_id}"
            
            # Description
            description = data.get('job_description') or data.get('description', '')
            
            # Remote detection
            remote_type = self._detect_remote(
                str(description) + ' ' + str(data.get('job_employment_type', ''))
            )
            
            return {
                'source': 'jsearch',
                'job_id': f"jsearch_{job_id}",
                'title': title,
                'company': company,
                'city': city,
                'province': province,
                'description': (description or '')[:2000],
                'salary_min': salary_min,
                'salary_max': salary_max,
                'remote_type': remote_type,
                'posted_date': posted_date,
                'url': url or f"https://www.google.com/search?q={title}+{company}+jobs"
            }
            
        except Exception as e:
            self.logger.debug(f"Parse error: {e}")
            return None
    
    def _normalize_province(self, state: str, city: str) -> str:
        """Map state/province name to 2-letter code."""
        province_map = {
            'ontario': 'ON', 'on': 'ON',
            'british columbia': 'BC', 'bc': 'BC',
            'alberta': 'AB', 'ab': 'AB',
            'quebec': 'QC', 'qc': 'QC', 'québec': 'QC',
            'manitoba': 'MB', 'mb': 'MB',
            'saskatchewan': 'SK', 'sk': 'SK',
            'nova scotia': 'NS', 'ns': 'NS',
            'new brunswick': 'NB', 'nb': 'NB',
            'newfoundland': 'NL', 'nl': 'NL',
            'pei': 'PE', 'pe': 'PE',
        }
        if not state:
            return ''
        normalized = province_map.get(state.strip().lower(), state[:2].upper() if len(state) >= 2 else '')
        return normalized
    
    def _parse_date(self, date_str: Optional[str]) -> str:
        """Parse date to ISO format."""
        if not date_str:
            return datetime.now().date().isoformat()
        
        # ISO format
        iso_match = re.search(r'(\d{4}-\d{2}-\d{2})', str(date_str))
        if iso_match:
            return iso_match.group(1)
        
        # Timestamp
        if str(date_str).replace('.', '').isdigit():
            try:
                ts = float(date_str)
                if ts > 1e12:  # milliseconds
                    ts /= 1000
                return datetime.fromtimestamp(ts).date().isoformat()
            except (ValueError, OSError):
                pass
        
        return datetime.now().date().isoformat()
    
    def _detect_remote(self, text: str) -> Optional[str]:
        """Detect remote work from text."""
        text_lower = (text or '').lower()
        if any(k in text_lower for k in ['remote', 'work from home', 'wfh', 'distributed']):
            if 'hybrid' in text_lower:
                return 'hybrid'
            return 'remote'
        return None
