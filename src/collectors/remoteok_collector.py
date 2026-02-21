"""
RemoteOK API collector - Free remote job listings (no API key).

API: https://remoteok.com/api
Terms: Link back to RemoteOK, mention as source.
"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime

import requests

from .base_collector import BaseCollector
from utils import Config


class RemoteOKCollector(BaseCollector):
    """Collect remote jobs from RemoteOK (free, no key)."""

    API_URL = "https://remoteok.com/api"

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize RemoteOK collector."""
        super().__init__(config or {})

    def collect_all_roles(self, roles: list) -> List[Dict[str, Any]]:
        """Fetch once and filter by multiple roles (avoids repeated API calls)."""
        self.logger.info("Fetching RemoteOK (all roles)")
        try:
            resp = requests.get(
                self.API_URL,
                headers={'User-Agent': Config.USER_AGENT},
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            self.logger.error(f"RemoteOK API error: {e}")
            return []

        if not isinstance(data, list) or len(data) < 2:
            return []

        all_role_words = set()
        for r in roles:
            all_role_words.update(r.lower().split())

        jobs = []
        seen_ids = set()
        for item in data[1:]:
            if not isinstance(item, dict):
                continue
            try:
                title = (item.get('position') or item.get('title') or '').strip()
                if not title or not all_role_words.intersection(set(title.lower().split())):
                    continue
                job = self._parse_job(item, all_role_words)
                if job and job['job_id'] not in seen_ids:
                    seen_ids.add(job['job_id'])
                    jobs.append(job)
            except Exception:
                continue

        self.logger.info(f"Collected {len(jobs)} jobs from RemoteOK")
        return jobs

    def collect(self, city: str, role: str, max_pages: int = 1) -> List[Dict[str, Any]]:
        """Collect jobs - single page (API returns all jobs). Filter by role."""
        self.logger.info(f"Fetching RemoteOK: {role}")

        try:
            resp = requests.get(
                self.API_URL,
                headers={'User-Agent': Config.USER_AGENT},
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            self.logger.error(f"RemoteOK API error: {e}")
            return []

        if not isinstance(data, list) or len(data) < 2:
            return []

        jobs = []
        role_words = set(role.lower().split())
        for item in data[1:]:  # Skip first (API info)
            if not isinstance(item, dict):
                continue
            try:
                job = self._parse_job(item, role_words)
                if job:
                    jobs.append(job)
            except Exception as e:
                self.logger.debug(f"RemoteOK parse error: {e}")
                continue

        self.logger.info(f"Collected {len(jobs)} jobs from RemoteOK")
        return jobs

    def _parse_job(self, data: Dict, role_words: set = None) -> Optional[Dict[str, Any]]:
        """Parse RemoteOK job."""
        role_words = role_words or set()
        title = (data.get('position') or data.get('title') or '').strip()
        if not title:
            return None

        if role_words:
            title_lower = title.lower()
            if not role_words.intersection(set(title_lower.split())):
                return None

        company = (data.get('company') or 'Unknown').strip()
        if not company:
            company = 'Unknown'

        location = (data.get('location') or '').strip()
        city, province = self._parse_location(location)

        job_id = str(data.get('id', ''))
        if not job_id:
            return None

        desc = data.get('description', '') or ''
        if isinstance(desc, str):
            from html import unescape
            import html
            desc = html.unescape(desc)
            import re as re_mod
            desc = re_mod.sub(r'<[^>]+>', ' ', desc)[:2000]

        date_str = data.get('date', '')
        posted = datetime.now().date().isoformat()
        if date_str:
            m = re.search(r'(\d{4}-\d{2}-\d{2})', str(date_str))
            if m:
                posted = m.group(1)

        url = (data.get('url') or '').strip() or f"https://remoteok.com/remote-jobs/{data.get('slug', job_id)}"

        return {
            'source': 'remoteok',
            'job_id': f"remoteok_{job_id}",
            'title': title,
            'company': company,
            'city': city,
            'province': province,
            'description': desc[:2000] if desc else '',
            'salary_min': None,
            'salary_max': None,
            'remote_type': 'remote',
            'posted_date': posted,
            'url': url or f"https://remoteok.com/"
        }

    def _parse_location(self, loc: str) -> tuple:
        """Parse location to (city, province)."""
        if not loc:
            return 'Remote', 'ON'
        loc_lower = loc.lower()
        if 'canada' in loc_lower or 'ca' in loc_lower:
            parts = [p.strip() for p in loc.split(',')]
            city = parts[0] if parts else 'Remote'
            prov_map = {'ontario': 'ON', 'on': 'ON', 'alberta': 'AB', 'ab': 'AB',
                        'british columbia': 'BC', 'bc': 'BC', 'quebec': 'QC', 'qc': 'QC'}
            province = ''
            for p in parts[1:]:
                province = prov_map.get(p.lower(), prov_map.get(p.lower()[:2], ''))
                if province:
                    break
            province = province or 'ON'
            return city, province
        return 'Remote', 'ON'
