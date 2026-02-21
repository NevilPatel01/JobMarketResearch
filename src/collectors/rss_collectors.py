"""
RSS feed collectors - Indeed and Workopolis.
"""

import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from urllib.parse import urlencode

import feedparser

from .base_collector import BaseCollector
from utils import retry_on_exception, Config


class IndeedRSSCollector(BaseCollector):
    """Collect jobs from Indeed RSS feeds.
    
    Note: Indeed may limit or block RSS access. If feed fails,
    consider using JSearch API (aggregates Indeed + others) instead.
    """
    
    # Try multiple Indeed RSS endpoints
    BASE_URLS = [
        "https://rss.indeed.com/rss",
        "https://ca.indeed.com/rss",
    ]
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize Indeed RSS collector."""
        super().__init__(config or {})
    
    @retry_on_exception(
        exceptions=(Exception,),
        max_attempts=Config.MAX_RETRIES
    )
    def _fetch_feed(self, url: str) -> Optional[feedparser.FeedParserDict]:
        """
        Fetch and parse RSS feed.
        
        Args:
            url: RSS feed URL
            
        Returns:
            Parsed feed or None if failed. Returns feed even if bozo (malformed)
            if entries exist - we can still extract some jobs.
        """
        try:
            # Use tolerant parsing - ignore some XML errors
            feed = feedparser.parse(
                url,
                response_headers={'Content-Type': 'application/xml'},
                sanitize_html=False
            )
            if feed.bozo and feed.bozo_exception:
                self.logger.warning(f"RSS feed parsing issue: {feed.bozo_exception}")
            # Return feed even if bozo - we may still have entries
            return feed
        except Exception as e:
            self.logger.error(f"Failed to fetch RSS feed: {e}")
            return None
    
    def collect(self, city: str, role: str, max_pages: int = 5) -> List[Dict[str, Any]]:
        """
        Collect jobs from Indeed RSS feed.
        
        Args:
            city: Canadian city name
            role: Job role keyword
            max_pages: Not used for RSS (kept for consistency)
            
        Returns:
            List of job dictionaries
        """
        self.logger.info(f"Fetching Indeed RSS: {role} in {city}")
        
        # Try multiple URL formats (Indeed has changed RSS over time)
        urls_to_try = [
            self._build_url(city, role, base="https://rss.indeed.com/rss"),
            self._build_url(city, role, base="https://ca.indeed.com/rss"),
        ]
        
        feed = None
        for url in urls_to_try:
            feed = self._fetch_feed(url)
            if feed and feed.entries:
                break
        
        if not feed or not feed.entries:
            self.logger.warning("Failed to fetch Indeed RSS feed or no entries found")
            return []
        
        # Parse jobs from feed
        jobs = []
        for entry in feed.entries:
            try:
                job = self._parse_entry(entry, city)
                if job:
                    jobs.append(job)
            except Exception as e:
                self.logger.debug(f"Failed to parse RSS entry: {e}")
                continue
        
        self.logger.info(f"Collected {len(jobs)} jobs from Indeed RSS")
        return jobs
    
    def _build_url(self, city: str, role: str, base: str = None) -> str:
        """
        Build Indeed RSS URL.
        
        Args:
            city: City name
            role: Job role
            base: Base URL (rss.indeed.com for US, ca.indeed.com for Canada)
            
        Returns:
            RSS feed URL
        """
        base = base or self.BASE_URLS[0]
        # Format: "City, Province" for Canadian locations
        location = f"{city}, Canada"
        params = {
            'q': role,
            'l': location,
            'fromage': '30',  # Last 30 days
            'limit': '50',   # Max results per feed
        }
        # rss.indeed.com uses co=ca for Canada
        if 'rss.indeed.com' in base:
            params['co'] = 'ca'
        query_string = urlencode(params)
        return f"{base}?{query_string}"
    
    def _parse_entry(self, entry: feedparser.FeedParserDict, city: str) -> Optional[Dict[str, Any]]:
        """
        Parse single RSS entry to job dictionary.
        
        Args:
            entry: Feed entry
            city: City for location normalization
            
        Returns:
            Job dictionary or None
        """
        try:
            # Extract basic fields
            title = entry.get('title', '').strip()
            link = entry.get('link', '')
            summary = entry.get('summary', '')
            
            if not title or not link:
                return None
            
            # Generate job ID from link
            job_id = hashlib.md5(link.encode()).hexdigest()[:12]
            
            # Extract company (Indeed puts company in title like "Job Title - Company")
            company = "Unknown"
            if ' - ' in title:
                parts = title.split(' - ')
                if len(parts) >= 2:
                    company = parts[-1].strip()
                    title = ' - '.join(parts[:-1]).strip()
            
            # Parse published date
            published = entry.get('published_parsed') or entry.get('updated_parsed')
            posted_date = self._parse_date(published)
            
            # Parse province from city
            province = self._infer_province(city)
            
            return {
                'source': 'indeed',
                'job_id': f"indeed_{job_id}",
                'title': title,
                'company': company,
                'city': city,
                'province': province,
                'description': summary[:500] if summary else '',  # Limit description
                'salary_min': None,
                'salary_max': None,
                'remote_type': None,
                'posted_date': posted_date,
                'url': link
            }
            
        except Exception as e:
            self.logger.debug(f"Failed to parse RSS entry: {e}")
            return None
    
    def _parse_date(self, published: Optional[tuple]) -> str:
        """
        Parse published date from feed.
        
        Args:
            published: Time tuple from feedparser
            
        Returns:
            ISO format date string
        """
        if published:
            try:
                date = datetime(*published[:6]).date()
                return date.isoformat()
            except:
                pass
        return datetime.now().date().isoformat()
    
    def _infer_province(self, city: str) -> str:
        """
        Infer province from city name.
        
        Args:
            city: City name
            
        Returns:
            2-letter province code
        """
        province_map = {
            'toronto': 'ON', 'ottawa': 'ON', 'mississauga': 'ON', 'hamilton': 'ON',
            'calgary': 'AB', 'edmonton': 'AB',
            'vancouver': 'BC', 'victoria': 'BC', 'surrey': 'BC',
            'saskatoon': 'SK', 'regina': 'SK',
            'winnipeg': 'MB',
            'montreal': 'QC', 'quebec city': 'QC', 'laval': 'QC'
        }
        return province_map.get(city.lower(), '')


class WorkopolisRSSCollector(BaseCollector):
    """Collect jobs from Workopolis RSS feeds."""
    
    BASE_URL = "https://www.workopolis.com/rss/search/cs"
    
    LOCATION_CODES = {
        'toronto': 'ca-on',
        'ottawa': 'ca-on',
        'mississauga': 'ca-on',
        'calgary': 'ca-ab',
        'edmonton': 'ca-ab',
        'vancouver': 'ca-bc',
        'victoria': 'ca-bc',
        'saskatoon': 'ca-sk',
        'regina': 'ca-sk',
        'winnipeg': 'ca-mb',
        'montreal': 'ca-qc',
        'quebec city': 'ca-qc'
    }
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize Workopolis RSS collector."""
        super().__init__(config or {})
    
    @retry_on_exception(
        exceptions=(Exception,),
        max_attempts=Config.MAX_RETRIES
    )
    def _fetch_feed(self, url: str) -> Optional[feedparser.FeedParserDict]:
        """Fetch and parse RSS feed. Use Accept header to request XML."""
        try:
            import requests
            headers = {'User-Agent': Config.USER_AGENT, 'Accept': 'application/rss+xml, application/xml, text/xml'}
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            ct = (resp.headers.get('Content-Type') or '').lower()
            if 'text/html' in ct and 'xml' not in ct:
                self.logger.warning("Workopolis returned HTML instead of RSS (feed may be deprecated)")
                return None
            feed = feedparser.parse(resp.content)
            if feed.bozo:
                self.logger.warning(f"RSS feed parsing issue: {feed.bozo_exception}")
            return feed
        except Exception as e:
            self.logger.error(f"Failed to fetch RSS feed: {e}")
            return None
    
    def collect(self, city: str, role: str, max_pages: int = 5) -> List[Dict[str, Any]]:
        """
        Collect jobs from Workopolis RSS feed.
        
        Args:
            city: Canadian city name
            role: Job role keyword
            max_pages: Not used for RSS
            
        Returns:
            List of job dictionaries
        """
        self.logger.info(f"Fetching Workopolis RSS: {role} in {city}")
        
        # Build RSS URL
        url = self._build_url(city, role)
        if not url:
            self.logger.warning(f"City {city} not supported by Workopolis RSS")
            return []
        
        # Fetch feed
        feed = self._fetch_feed(url)
        if not feed or not feed.entries:
            self.logger.warning("Failed to fetch Workopolis RSS feed or no entries found")
            return []
        
        # Parse jobs from feed
        jobs = []
        for entry in feed.entries:
            try:
                job = self._parse_entry(entry, city)
                if job:
                    jobs.append(job)
            except Exception as e:
                self.logger.debug(f"Failed to parse RSS entry: {e}")
                continue
        
        self.logger.info(f"Collected {len(jobs)} jobs from Workopolis RSS")
        return jobs
    
    def _build_url(self, city: str, role: str) -> Optional[str]:
        """
        Build Workopolis RSS URL.
        
        Args:
            city: City name
            role: Job role
            
        Returns:
            RSS feed URL or None if city not supported
        """
        location_code = self.LOCATION_CODES.get(city.lower())
        if not location_code:
            return None
        
        params = {
            'as': location_code,
            'keywords': role.replace(' ', '+'),
            'jt': 'fulltime',
            'et': '30d'
        }
        query_string = urlencode(params)
        return f"{self.BASE_URL}?{query_string}"
    
    def _parse_entry(self, entry: feedparser.FeedParserDict, city: str) -> Optional[Dict[str, Any]]:
        """Parse single RSS entry to job dictionary."""
        try:
            # Extract basic fields
            title = entry.get('title', '').strip()
            link = entry.get('link', '')
            summary = entry.get('summary', '')
            
            if not title or not link:
                return None
            
            # Generate job ID from link
            job_id = hashlib.md5(link.encode()).hexdigest()[:12]
            
            # Extract company
            company = entry.get('source', {}).get('title', 'Unknown')
            
            # Parse published date
            published = entry.get('published_parsed') or entry.get('updated_parsed')
            posted_date = self._parse_date(published)
            
            # Parse province from city
            province = self._infer_province(city)
            
            return {
                'source': 'workopolis',
                'job_id': f"workopolis_{job_id}",
                'title': title,
                'company': company,
                'city': city,
                'province': province,
                'description': summary[:500] if summary else '',
                'salary_min': None,
                'salary_max': None,
                'remote_type': None,
                'posted_date': posted_date,
                'url': link
            }
            
        except Exception as e:
            self.logger.debug(f"Failed to parse RSS entry: {e}")
            return None
    
    def _parse_date(self, published: Optional[tuple]) -> str:
        """Parse published date from feed."""
        if published:
            try:
                date = datetime(*published[:6]).date()
                return date.isoformat()
            except:
                pass
        return datetime.now().date().isoformat()
    
    def _infer_province(self, city: str) -> str:
        """Infer province from city name."""
        province_map = {
            'toronto': 'ON', 'ottawa': 'ON', 'mississauga': 'ON',
            'calgary': 'AB', 'edmonton': 'AB',
            'vancouver': 'BC', 'victoria': 'BC',
            'saskatoon': 'SK', 'regina': 'SK',
            'winnipeg': 'MB',
            'montreal': 'QC', 'quebec city': 'QC'
        }
        return province_map.get(city.lower(), '')
