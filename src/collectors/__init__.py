"""Collectors package for Canada Tech Job Compass."""

from .base_collector import BaseCollector
from .jobbank_collector import JobBankCollector
from .rapidapi_collector import RapidAPICollector
from .rss_collectors import IndeedRSSCollector, WorkopolisRSSCollector

__all__ = [
    'BaseCollector',
    'JobBankCollector',
    'RapidAPICollector',
    'IndeedRSSCollector',
    'WorkopolisRSSCollector'
]
