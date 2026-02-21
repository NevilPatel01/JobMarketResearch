"""
Retry logic utilities with exponential backoff.
"""

import time
from functools import wraps
from typing import Callable, Type, Tuple, Any
import logging

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)

from .config import Config

logger = logging.getLogger(__name__)


def rate_limit(min_interval: float = 2.0):
    """
    Decorator to enforce minimum interval between function calls.
    
    Args:
        min_interval: Minimum seconds between calls
        
    Example:
        @rate_limit(min_interval=2.5)
        def scrape_page(url):
            return requests.get(url)
    """
    def decorator(func: Callable) -> Callable:
        last_called = [0.0]
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            if elapsed < min_interval:
                sleep_time = min_interval - elapsed
                time.sleep(sleep_time)
            
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        
        return wrapper
    return decorator


def retry_on_exception(
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    max_attempts: int = None,
    min_wait: int = None,
    max_wait: int = None
):
    """
    Decorator for retrying function calls with exponential backoff.
    
    Args:
        exceptions: Tuple of exception types to retry on
        max_attempts: Maximum number of retry attempts (default: Config.MAX_RETRIES)
        min_wait: Minimum wait time in seconds (default: Config.RETRY_MIN_WAIT)
        max_wait: Maximum wait time in seconds (default: Config.RETRY_MAX_WAIT)
        
    Example:
        @retry_on_exception(exceptions=(requests.Timeout, requests.ConnectionError))
        def fetch_data(url):
            return requests.get(url, timeout=30)
    """
    if max_attempts is None:
        max_attempts = Config.MAX_RETRIES
    if min_wait is None:
        min_wait = Config.RETRY_MIN_WAIT
    if max_wait is None:
        max_wait = Config.RETRY_MAX_WAIT
    
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(
            multiplier=Config.RETRY_BACKOFF_MULTIPLIER,
            min=min_wait,
            max=max_wait
        ),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.DEBUG)
    )


class RateLimiter:
    """
    Rate limiter class for controlling request frequency.
    
    Example:
        limiter = RateLimiter(min_interval=2.5)
        
        for url in urls:
            limiter.wait()
            response = requests.get(url)
    """
    
    def __init__(self, min_interval: float):
        """
        Initialize rate limiter.
        
        Args:
            min_interval: Minimum seconds between calls
        """
        self.min_interval = min_interval
        self.last_called = 0.0
    
    def wait(self):
        """Wait until minimum interval has passed since last call."""
        elapsed = time.time() - self.last_called
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            time.sleep(sleep_time)
        self.last_called = time.time()
    
    def reset(self):
        """Reset the rate limiter."""
        self.last_called = 0.0
