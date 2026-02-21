"""Collectors package for Canada Tech Job Compass."""

from .base_collector import BaseCollector
from .jobbank_collector import JobBankCollector
from .rapidapi_collector import RapidAPICollector
from .jsearch_collector import JSearchCollector
from .adzuna_collector import AdzunaCollector
from .remoteok_collector import RemoteOKCollector
from .rss_collectors import IndeedRSSCollector, WorkopolisRSSCollector

__all__ = [
    'BaseCollector',
    'JobBankCollector',
    'RapidAPICollector',
    'JSearchCollector',
    'AdzunaCollector',
    'RemoteOKCollector',
    'IndeedRSSCollector',
    'WorkopolisRSSCollector'
]
