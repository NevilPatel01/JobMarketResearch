"""
Job Bank Canada collector - Web scraping with BeautifulSoup.
"""

import re
import time
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base_collector import BaseCollector
from ..utils import Config, retry_on_exception, rate_limit


class JobBankCollector(BaseCollector):
    """Collect jobs from Job Bank Canada using web scraping."""
    
    BASE_URL = "https://www.jobbank.gc.ca/jobsearch/jobsearch"
    
    HEADERS = {
        'User-Agent': Config.USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize Job Bank collector."""
        super().__init__(config or {})
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
    
    @rate_limit(min_interval=Config.JOBBANK_RATE_LIMIT_SECONDS)
    @retry_on_exception(
        exceptions=(requests.Timeout, requests.ConnectionError),
        max_attempts=Config.MAX_RETRIES
    )
    def _fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch HTML content from URL with rate limiting and retry.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content as string, or None if failed
        """
        try:
            response = self.session.get(
                url,
                timeout=Config.JOBBANK_REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.text
        except Exception as e:
            self.logger.error(f"Failed to fetch {url}: {e}")
            return None
    
    def collect(self, city: str, role: str, max_pages: int = 5) -> List[Dict[str, Any]]:
        """
        Collect jobs from Job Bank Canada.
        
        Args:
            city: Canadian city name
            role: Job role keyword
            max_pages: Maximum pages to scrape
            
        Returns:
            List of job dictionaries
        """
        all_jobs = []
        
        for page in range(1, max_pages + 1):
            self.logger.info(f"Scraping page {page}/{max_pages} for {role} in {city}")
            
            # Build URL
            url = self._build_url(city, role, page)
            
            # Fetch HTML
            html = self._fetch_page(url)
            if not html:
                self.logger.warning(f"Failed to fetch page {page}, stopping")
                break
            
            # Parse jobs from HTML
            jobs = self._parse_jobs_from_html(html, city)
            
            if not jobs:
                self.logger.info(f"No more jobs found on page {page}, stopping")
                break
            
            all_jobs.extend(jobs)
            self.logger.info(f"Found {len(jobs)} jobs on page {page}")
        
        self.logger.info(f"Total jobs collected: {len(all_jobs)}")
        return all_jobs
    
    def _build_url(self, city: str, role: str, page: int = 1) -> str:
        """
        Build Job Bank search URL.
        
        Args:
            city: City name
            role: Job role
            page: Page number
            
        Returns:
            Complete URL
        """
        params = {
            'searchstring': role.replace(' ', '+'),
            'location': city,
            'postedDate': '30',  # Last 30 days
            'sort': 'posted',
            'page': str(page)
        }
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{self.BASE_URL}?{query_string}"
    
    def _parse_jobs_from_html(self, html: str, city: str) -> List[Dict[str, Any]]:
        """
        Parse job listings from HTML.
        
        Args:
            html: HTML content
            city: City name for normalization
            
        Returns:
            List of job dictionaries
        """
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []
        
        # Find all job listing articles
        job_articles = soup.find_all('article', class_='resultJobItem')
        
        for article in job_articles:
            try:
                job = self._parse_job_article(article, city)
                if job:
                    jobs.append(job)
            except Exception as e:
                self.logger.warning(f"Failed to parse job article: {e}")
                continue
        
        return jobs
    
    def _parse_job_article(self, article: BeautifulSoup, city: str) -> Optional[Dict[str, Any]]:
        """
        Parse single job article element.
        
        Args:
            article: BeautifulSoup article element
            city: City for location normalization
            
        Returns:
            Job dictionary or None if parsing failed
        """
        try:
            # Extract job title and URL
            title_tag = article.find('h3', class_='noctitle')
            if not title_tag:
                title_tag = article.find('h2', class_='jobTitle') or article.find('h3')
            
            if not title_tag:
                return None
            
            link_tag = title_tag.find('a')
            if not link_tag:
                return None
            
            title = link_tag.get_text(strip=True)
            job_path = link_tag.get('href', '')
            
            if not job_path:
                return None
            
            # Generate job ID from path
            job_id = self._extract_job_id_from_path(job_path)
            url = urljoin('https://www.jobbank.gc.ca', job_path)
            
            # Extract company
            company_tag = article.find('span', class_='business')
            if not company_tag:
                company_tag = article.find('div', class_='company')
            company = company_tag.get_text(strip=True) if company_tag else "Unknown"
            
            # Extract location
            location_tag = article.find('span', class_='location')
            if not location_tag:
                location_tag = article.find('div', class_='location')
            location = location_tag.get_text(strip=True) if location_tag else city
            
            city_normalized, province = self._parse_location(location)
            
            # Extract salary if available
            salary_tag = article.find('span', class_='salary')
            if not salary_tag:
                salary_tag = article.find('div', class_='salary')
            salary_min, salary_max = self._parse_salary(salary_tag.get_text(strip=True)) if salary_tag else (None, None)
            
            # Extract posting date
            date_tag = article.find('time')
            if not date_tag:
                date_tag = article.find('span', class_='date')
            posted_date = self._parse_date(date_tag.get_text(strip=True) if date_tag else None)
            
            return {
                'source': 'jobbank',
                'job_id': f"jobbank_{job_id}",
                'title': title,
                'company': company,
                'city': city_normalized or city,
                'province': province,
                'description': '',  # Will be fetched separately if needed
                'salary_min': salary_min,
                'salary_max': salary_max,
                'remote_type': None,
                'posted_date': posted_date,
                'url': url
            }
            
        except Exception as e:
            self.logger.debug(f"Failed to parse job article: {e}")
            return None
    
    def _extract_job_id_from_path(self, path: str) -> str:
        """Extract job ID from URL path."""
        # Extract numeric ID or generate hash from path
        match = re.search(r'/(\d+)/?$', path)
        if match:
            return match.group(1)
        else:
            # Generate hash from path if no ID found
            return hashlib.md5(path.encode()).hexdigest()[:12]
    
    def _parse_location(self, location: str) -> Tuple[str, str]:
        """
        Parse location string to city and province.
        
        Args:
            location: Location string (e.g., "Toronto, Ontario")
            
        Returns:
            Tuple of (city, province_code)
        """
        province_map = {
            'ontario': 'ON', 'british columbia': 'BC', 'alberta': 'AB',
            'saskatchewan': 'SK', 'manitoba': 'MB', 'quebec': 'QC',
            'nova scotia': 'NS', 'new brunswick': 'NB',
            'newfoundland and labrador': 'NL', 'prince edward island': 'PE',
            'northwest territories': 'NT', 'nunavut': 'NU', 'yukon': 'YT'
        }
        
        parts = [p.strip() for p in location.split(',')]
        city = parts[0] if parts else "Unknown"
        
        province = ""
        if len(parts) > 1:
            prov_text = parts[1].lower()
            # Check if it's already a 2-letter code
            if len(parts[1].strip()) == 2:
                province = parts[1].strip().upper()
            else:
                # Look up full name
                province = province_map.get(prov_text, parts[1].strip()[:2].upper())
        
        return city, province
    
    def _parse_salary(self, salary_text: str) -> Tuple[Optional[int], Optional[int]]:
        """
        Parse salary range from text.
        
        Args:
            salary_text: Salary text (e.g., "$60,000 to $80,000")
            
        Returns:
            Tuple of (min_salary, max_salary)
        """
        if not salary_text or 'not' in salary_text.lower():
            return None, None
        
        # Remove formatting
        cleaned = salary_text.replace(',', '').replace('$', '').replace(' ', '')
        
        # Try to find range: "60000to80000" or "60000-80000"
        range_pattern = r'(\d+)(?:to|-|–)(\d+)'
        match = re.search(range_pattern, cleaned, re.IGNORECASE)
        
        if match:
            return int(match.group(1)), int(match.group(2))
        
        # Try single value
        single_pattern = r'(\d+)'
        match = re.search(single_pattern, cleaned)
        
        if match:
            value = int(match.group(1))
            return value, value
        
        return None, None
    
    def _parse_date(self, date_text: Optional[str]) -> str:
        """
        Parse posting date from text.
        
        Args:
            date_text: Date text (e.g., "Posted 5 days ago", "2026-02-15")
            
        Returns:
            ISO format date string (YYYY-MM-DD)
        """
        if not date_text:
            return datetime.now().date().isoformat()
        
        # Try ISO format first
        iso_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_text)
        if iso_match:
            return iso_match.group(1)
        
        # Try "X days ago"
        days_match = re.search(r'(\d+)\s+days?\s+ago', date_text, re.IGNORECASE)
        if days_match:
            days = int(days_match.group(1))
            date = datetime.now().date() - timedelta(days=days)
            return date.isoformat()
        
        # Try "yesterday"
        if 'yesterday' in date_text.lower():
            date = datetime.now().date() - timedelta(days=1)
            return date.isoformat()
        
        # Try "today"
        if 'today' in date_text.lower():
            return datetime.now().date().isoformat()
        
        # Default to today
        return datetime.now().date().isoformat()
