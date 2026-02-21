"""
RapidAPI collector - LinkedIn Jobs API integration.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

import requests

from .base_collector import BaseCollector
from ..utils import Config, retry_on_exception


class RapidAPICollector(BaseCollector):
    """Collect jobs from RapidAPI (LinkedIn Jobs API)."""
    
    BASE_URL = "https://linkedin-jobs.p.rapidapi.com/jobs"
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize RapidAPI collector."""
        super().__init__(config or {})
        
        if not Config.RAPIDAPI_KEY:
            self.logger.warning("RAPIDAPI_KEY not configured")
        
        self.headers = {
            'X-RapidAPI-Key': Config.RAPIDAPI_KEY,
            'X-RapidAPI-Host': Config.RAPIDAPI_HOST
        }
        
        self.request_count = 0
        self.max_requests = 500  # Free tier limit
    
    @retry_on_exception(
        exceptions=(requests.Timeout, requests.ConnectionError, requests.HTTPError),
        max_attempts=Config.MAX_RETRIES
    )
    def _fetch_jobs(self, params: Dict[str, Any]) -> Optional[Dict]:
        """
        Fetch jobs from RapidAPI.
        
        Args:
            params: Query parameters
            
        Returns:
            API response as dictionary, or None if failed
        """
        if self.request_count >= self.max_requests:
            self.logger.warning(f"RapidAPI request limit reached ({self.max_requests})")
            return None
        
        try:
            response = requests.get(
                self.BASE_URL,
                headers=self.headers,
                params=params,
                timeout=Config.JOBBANK_REQUEST_TIMEOUT
            )
            
            # Check for rate limiting
            if response.status_code == 429:
                self.logger.error("RapidAPI rate limit exceeded")
                return None
            
            # Check for auth errors
            if response.status_code == 401 or response.status_code == 403:
                self.logger.error("RapidAPI authentication failed - check API key")
                return None
            
            response.raise_for_status()
            self.request_count += 1
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"RapidAPI HTTP error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"RapidAPI error: {e}")
            return None
    
    def collect(self, city: str, role: str, max_pages: int = 5) -> List[Dict[str, Any]]:
        """
        Collect jobs from RapidAPI.
        
        Args:
            city: Canadian city name
            role: Job role keyword
            max_pages: Maximum pages (not used for API, but kept for consistency)
            
        Returns:
            List of job dictionaries
        """
        self.logger.info(f"Fetching from RapidAPI: {role} in {city}")
        
        # Build query parameters
        params = {
            'location': f"{city}, Canada",
            'keywords': role,
            'datePosted': 'month',  # Last month
            'sort': 'date'
        }
        
        # Fetch from API
        data = self._fetch_jobs(params)
        
        if not data:
            self.logger.warning("Failed to fetch data from RapidAPI")
            return []
        
        # Parse jobs from response
        jobs = self._parse_jobs_from_response(data, city)
        
        self.logger.info(f"Collected {len(jobs)} jobs from RapidAPI")
        return jobs
    
    def _parse_jobs_from_response(self, data: Dict, city: str) -> List[Dict[str, Any]]:
        """
        Parse jobs from API response.
        
        Args:
            data: API response data
            city: City for location normalization
            
        Returns:
            List of job dictionaries
        """
        jobs = []
        
        # LinkedIn Jobs API returns jobs in 'data' or 'jobs' key
        job_list = data.get('data', data.get('jobs', []))
        
        if not isinstance(job_list, list):
            self.logger.warning("Unexpected response format from RapidAPI")
            return []
        
        for job_data in job_list:
            try:
                job = self._parse_single_job(job_data, city)
                if job:
                    jobs.append(job)
            except Exception as e:
                self.logger.debug(f"Failed to parse job: {e}")
                continue
        
        return jobs
    
    def _parse_single_job(self, job_data: Dict, city: str) -> Optional[Dict[str, Any]]:
        """
        Parse single job from API response.
        
        Args:
            job_data: Single job data from API
            city: City for location normalization
            
        Returns:
            Job dictionary or None if parsing failed
        """
        try:
            # Extract job ID
            job_id_raw = job_data.get('id') or job_data.get('jobId') or job_data.get('job_id')
            if not job_id_raw:
                return None
            
            # Extract title
            title = job_data.get('title') or job_data.get('jobTitle') or job_data.get('position')
            if not title:
                return None
            
            # Extract company
            company = job_data.get('company') or job_data.get('companyName') or job_data.get('employer') or 'Unknown'
            
            # Extract location
            location = job_data.get('location') or job_data.get('jobLocation') or f"{city}, Canada"
            city_normalized, province = self._parse_location(location, city)
            
            # Extract description
            description = job_data.get('description') or job_data.get('jobDescription') or ''
            
            # Extract salary
            salary_text = job_data.get('salary') or job_data.get('salaryRange') or ''
            salary_min, salary_max = self._parse_salary(salary_text)
            
            # Extract URL
            url = job_data.get('url') or job_data.get('jobUrl') or job_data.get('link') or ''
            
            # Extract posted date
            posted_date_str = job_data.get('postedAt') or job_data.get('datePosted') or job_data.get('posted_date')
            posted_date = self._parse_date(posted_date_str)
            
            # Detect remote work
            remote_type = self._detect_remote(description, title)
            
            return {
                'source': 'rapidapi',
                'job_id': f"rapidapi_{job_id_raw}",
                'title': title,
                'company': company,
                'city': city_normalized,
                'province': province,
                'description': description[:1000] if description else '',  # Limit description length
                'salary_min': salary_min,
                'salary_max': salary_max,
                'remote_type': remote_type,
                'posted_date': posted_date,
                'url': url
            }
            
        except Exception as e:
            self.logger.debug(f"Failed to parse job data: {e}")
            return None
    
    def _parse_location(self, location: str, default_city: str) -> Tuple[str, str]:
        """
        Parse location string to city and province.
        
        Args:
            location: Location string
            default_city: Default city if parsing fails
            
        Returns:
            Tuple of (city, province_code)
        """
        province_map = {
            'ontario': 'ON', 'british columbia': 'BC', 'alberta': 'AB',
            'saskatchewan': 'SK', 'manitoba': 'MB', 'quebec': 'QC',
            'nova scotia': 'NS', 'new brunswick': 'NB'
        }
        
        # Remove "Canada" from location
        location_clean = location.replace(', Canada', '').replace(',Canada', '').strip()
        
        parts = [p.strip() for p in location_clean.split(',')]
        city = parts[0] if parts else default_city
        
        province = ""
        if len(parts) > 1:
            prov_text = parts[1].lower()
            if len(parts[1].strip()) == 2:
                province = parts[1].strip().upper()
            else:
                province = province_map.get(prov_text, parts[1].strip()[:2].upper())
        
        return city, province
    
    def _parse_salary(self, salary_text: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Parse salary range from text.
        
        Args:
            salary_text: Salary text
            
        Returns:
            Tuple of (min_salary, max_salary)
        """
        if not salary_text:
            return None, None
        
        # Remove formatting
        cleaned = salary_text.replace(',', '').replace('$', '').replace(' ', '')
        
        # Try to find numbers
        numbers = re.findall(r'\d+', cleaned)
        
        if len(numbers) >= 2:
            return int(numbers[0]), int(numbers[1])
        elif len(numbers) == 1:
            value = int(numbers[0])
            return value, value
        
        return None, None
    
    def _parse_date(self, date_str: Optional[str]) -> str:
        """
        Parse posting date from various formats.
        
        Args:
            date_str: Date string
            
        Returns:
            ISO format date string
        """
        if not date_str:
            return datetime.now().date().isoformat()
        
        # Try ISO format
        iso_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_str)
        if iso_match:
            return iso_match.group(1)
        
        # Try timestamp (milliseconds)
        if date_str.isdigit():
            try:
                timestamp = int(date_str) / 1000  # Convert ms to seconds
                date = datetime.fromtimestamp(timestamp).date()
                return date.isoformat()
            except:
                pass
        
        # Default to today
        return datetime.now().date().isoformat()
    
    def _detect_remote(self, description: str, title: str) -> Optional[str]:
        """
        Detect remote work type from description and title.
        
        Args:
            description: Job description
            title: Job title
            
        Returns:
            'remote', 'hybrid', or 'onsite'
        """
        text = (description + ' ' + title).lower()
        
        remote_keywords = ['remote', 'work from home', 'wfh', 'telecommute', 'distributed']
        hybrid_keywords = ['hybrid', 'flexible', 'partial remote']
        
        if any(keyword in text for keyword in remote_keywords):
            if any(keyword in text for keyword in hybrid_keywords):
                return 'hybrid'
            return 'remote'
        
        return 'onsite'
