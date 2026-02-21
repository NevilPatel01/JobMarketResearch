"""
Adzuna API collector - Free job listings for Canada.

Register at https://developer.adzuna.com/ for free API keys.
Set ADZUNA_APP_ID and ADZUNA_APP_KEY in .env.
"""

import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime

import requests

from .base_collector import BaseCollector
from utils import Config, retry_on_exception


class AdzunaCollector(BaseCollector):
    """Collect jobs from Adzuna API (free, Canada support)."""

    BASE_URL = "https://api.adzuna.com/v1/api/jobs/ca/search"

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize Adzuna collector."""
        super().__init__(config or {})

        self.app_id = Config.ADZUNA_APP_ID
        self.app_key = Config.ADZUNA_APP_KEY

        if not self.app_id or not self.app_key:
            self.logger.warning(
                "ADZUNA_APP_ID and ADZUNA_APP_KEY not configured. "
                "Register at https://developer.adzuna.com/"
            )

    @retry_on_exception(
        exceptions=(requests.Timeout, requests.ConnectionError),
        max_attempts=Config.MAX_RETRIES
    )
    def _fetch_page(self, role: str, city: str, page: int) -> Optional[Dict]:
        """Fetch one page from Adzuna API."""
        if not self.app_id or not self.app_key:
            return None

        try:
            url = f"{self.BASE_URL}/{page}"
            params = {
                'app_id': self.app_id,
                'app_key': self.app_key,
                'what': role,
                'where': city,
                'results_per_page': 20,
                'content-type': 'application/json',
            }
            response = requests.get(url, params=params, timeout=Config.JOBBANK_REQUEST_TIMEOUT)

            if response.status_code == 401:
                self.logger.error("Adzuna API auth failed - check ADZUNA_APP_ID and ADZUNA_APP_KEY")
                return None
            if response.status_code == 429:
                self.logger.warning("Adzuna API rate limit reached")
                return None

            response.raise_for_status()
            return response.json()

        except Exception as e:
            self.logger.error(f"Adzuna API error: {e}")
            return None

    def collect(self, city: str, role: str, max_pages: int = 3) -> List[Dict[str, Any]]:
        """Collect jobs from Adzuna API."""
        self.logger.info(f"Fetching Adzuna: {role} in {city}")

        all_jobs = []
        for page in range(1, max_pages + 1):
            data = self._fetch_page(role, city, page)
            if not data:
                break

            results = data.get('results', [])
            if not results:
                break

            for item in results:
                try:
                    job = self._parse_job(item, city)
                    if job:
                        all_jobs.append(job)
                except Exception as e:
                    self.logger.debug(f"Adzuna parse error: {e}")
                    continue

        self.logger.info(f"Collected {len(all_jobs)} jobs from Adzuna")
        return all_jobs

    def _parse_job(self, data: Dict, default_city: str) -> Optional[Dict[str, Any]]:
        """Parse Adzuna job result."""
        try:
            title = data.get('title', '').strip()
            if not title:
                return None

            company = data.get('company', {}).get('display_name', 'Unknown')
            if isinstance(company, dict):
                company = company.get('display_name', 'Unknown')

            location = data.get('location', {}) or {}
            city = location.get('display_name', default_city) if isinstance(location, dict) else default_city
            if isinstance(city, str) and ',' in city:
                parts = [p.strip() for p in city.split(',')]
                city = parts[0] if parts else default_city
            city = city or default_city

            province = self._infer_province(city)
            if not province and isinstance(location, dict):
                display = location.get('display_name', '')
                if ',' in str(display):
                    province = self._province_from_name(display.split(',')[-1].strip())
                if not province:
                    province = self._province_from_area(location)
            if not province:
                province = self._infer_province(default_city)

            job_id_raw = data.get('id')
            if not job_id_raw:
                link = data.get('redirect_url', data.get('link', ''))
                job_id_raw = hashlib.md5(link.encode()).hexdigest()[:12] if link else None
            if not job_id_raw:
                return None

            salary_min = data.get('salary_min')
            salary_max = data.get('salary_max')
            if salary_min is not None and salary_max is not None and salary_min > salary_max:
                salary_min, salary_max = salary_max, salary_min

            created = data.get('created')
            posted_date = datetime.now().date().isoformat()
            if created:
                try:
                    if 'T' in str(created):
                        posted_date = str(created).split('T')[0]
                    elif len(str(created)) >= 10:
                        posted_date = str(created)[:10]
                except Exception:
                    pass

            description = data.get('description', '') or ''
            remote_type = self._detect_remote(description)

            url = data.get('redirect_url') or data.get('link') or ''

            return {
                'source': 'adzuna',
                'job_id': f"adzuna_{job_id_raw}",
                'title': title,
                'company': company,
                'city': city,
                'province': province,
                'description': (description or '')[:2000],
                'salary_min': salary_min,
                'salary_max': salary_max,
                'remote_type': remote_type,
                'posted_date': posted_date,
                'url': url or f"https://www.adzuna.ca/jobs/ca?q={title.replace(' ', '+')}",
            }

        except Exception as e:
            self.logger.debug(f"Adzuna parse error: {e}")
            return None

    def _infer_province(self, city: str) -> str:
        """Infer province from city name."""
        province_map = {
            'toronto': 'ON', 'ottawa': 'ON', 'mississauga': 'ON', 'hamilton': 'ON',
            'calgary': 'AB', 'edmonton': 'AB',
            'vancouver': 'BC', 'victoria': 'BC', 'surrey': 'BC',
            'saskatoon': 'SK', 'regina': 'SK',
            'winnipeg': 'MB',
            'montreal': 'QC', 'quebec city': 'QC', 'laval': 'QC',
        }
        return province_map.get((city or '').lower().strip(), '')

    def _province_from_name(self, name: str) -> str:
        """Map province/region name to 2-letter code."""
        if not name:
            return ''
        n = str(name).lower().strip()
        map = {
            'ontario': 'ON', 'on': 'ON',
            'alberta': 'AB', 'ab': 'AB',
            'british columbia': 'BC', 'bc': 'BC', 'b.c.': 'BC',
            'quebec': 'QC', 'qc': 'QC', 'québec': 'QC',
            'manitoba': 'MB', 'mb': 'MB',
            'saskatchewan': 'SK', 'sk': 'SK',
            'nova scotia': 'NS', 'ns': 'NS',
            'new brunswick': 'NB', 'nb': 'NB',
        }
        return map.get(n, '')

    def _province_from_area(self, location: dict) -> str:
        """Extract province from Adzuna location.area array."""
        area = location.get('area', [])
        if not isinstance(area, list):
            return ''
        for part in area:
            p = self._province_from_name(part)
            if p:
                return p
        return ''

    def _detect_remote(self, text: str) -> Optional[str]:
        """Detect remote work from text."""
        text_lower = (text or '').lower()
        if any(k in text_lower for k in ['remote', 'work from home', 'wfh', 'distributed']):
            if 'hybrid' in text_lower:
                return 'hybrid'
            return 'remote'
        return None
