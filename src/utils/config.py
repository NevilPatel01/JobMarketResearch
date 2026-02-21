"""
Configuration loader for Canada Tech Job Compass.
Loads environment variables and provides access to configuration settings.
"""

import os
import re
from typing import Optional, List
from urllib.parse import quote, unquote
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def _derive_pooler_url(direct_url: str, region: str, *, use_session_port: bool = True) -> Optional[str]:
    """
    Derive Supabase pooler URL from direct connection URL.
    Uses Session pooler (5432) by default - for persistent backends, supports prepared statements.
    """
    if not direct_url or 'pooler.supabase.com' in direct_url:
        return None
    match = re.search(r'://postgres:([^@]+)@db\.([a-z0-9]+)\.supabase\.co(?::\d+)?', direct_url)
    if not match:
        return None
    password, project_ref = match.group(1), match.group(2)
    password = unquote(password)
    pass_encoded = quote(password, safe='')
    user = f"postgres.{project_ref}"
    host = f"aws-0-{region}.pooler.supabase.com"
    port = 5432 if use_session_port else 6543
    netloc = f"{user}:{pass_encoded}@{host}:{port}"
    path = '/postgres' if '/postgres' in direct_url else ''
    scheme = 'postgresql' if direct_url.startswith(('postgresql://', 'postgres://')) else 'postgresql'
    return f"{scheme}://{netloc}{path}"


class Config:
    """Configuration settings loaded from environment variables."""
    
    # Database Configuration
    SUPABASE_URL: str = os.getenv('SUPABASE_URL', '')
    SUPABASE_KEY: str = os.getenv('SUPABASE_KEY', '')
    # Prefer pooler URL (more reliable for remote connections) - aws-0-region.pooler.supabase.com:6543
    SUPABASE_DB_POOLER_URL: str = os.getenv('SUPABASE_DB_POOLER_URL', '')
    SUPABASE_DB_URL: str = os.getenv('SUPABASE_DB_URL', '')
    # Set to 'true' when direct URL fails DNS; we then derive pooler from SUPABASE_DB_URL
    USE_POOLER_FOR_DNS_FIX: bool = os.getenv('USE_POOLER_FOR_DNS_FIX', 'true').lower() == 'true'
    # Region for derived pooler - set if you get "Tenant or user not found" (e.g. eu-west-1, ca-central-1)
    SUPABASE_POOLER_REGION: str = os.getenv('SUPABASE_POOLER_REGION', 'us-east-1')

    @classmethod
    def get_db_url(cls) -> str:
        """Return DB URL. Prefer explicit pooler (must use pooler.supabase.com); else derive if USE_POOLER_FOR_DNS_FIX; else direct."""
        # Only use as pooler if it has pooler host - ignore when user pasted direct URL by mistake
        if cls.SUPABASE_DB_POOLER_URL:
            if 'pooler.supabase.com' in cls.SUPABASE_DB_POOLER_URL:
                return cls.SUPABASE_DB_POOLER_URL
            if 'db.' in cls.SUPABASE_DB_POOLER_URL and 'supabase.co' in cls.SUPABASE_DB_POOLER_URL:
                import logging
                logging.getLogger(__name__).warning(
                    "SUPABASE_DB_POOLER_URL looks like direct URL (db.xxx.supabase.co). "
                    "Use pooler URL from Dashboard → Settings → Database → Connect → Session/Transaction pooler."
                )
        if cls.USE_POOLER_FOR_DNS_FIX and cls.SUPABASE_DB_URL:
            derived = _derive_pooler_url(cls.SUPABASE_DB_URL, cls.SUPABASE_POOLER_REGION)
            if derived:
                return derived
        return cls.SUPABASE_DB_URL or ''
    DB_POOL_SIZE: int = int(os.getenv('DB_POOL_SIZE', '5'))
    DB_MAX_OVERFLOW: int = int(os.getenv('DB_MAX_OVERFLOW', '10'))
    
    # API Keys
    RAPIDAPI_KEY: str = os.getenv('RAPIDAPI_KEY', '')
    RAPIDAPI_HOST: str = os.getenv('RAPIDAPI_HOST', 'linkedin-jobs.p.rapidapi.com')
    ADZUNA_APP_ID: str = os.getenv('ADZUNA_APP_ID', '')
    ADZUNA_APP_KEY: str = os.getenv('ADZUNA_APP_KEY', '')

    # AI / LLM (plug-and-play: ollama or openai)
    LLM_PROVIDER: str = os.getenv('LLM_PROVIDER', 'ollama')
    OLLAMA_MODEL: str = os.getenv('OLLAMA_MODEL', 'llama3.2')
    OLLAMA_BASE_URL: str = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    
    # Scraping Configuration
    JOBBANK_RATE_LIMIT_SECONDS: float = float(os.getenv('JOBBANK_RATE_LIMIT_SECONDS', '2.5'))
    JOBBANK_MAX_PAGES: int = int(os.getenv('JOBBANK_MAX_PAGES', '5'))
    JOBBANK_REQUEST_TIMEOUT: int = int(os.getenv('JOBBANK_REQUEST_TIMEOUT', '30'))
    
    # Selenium Configuration
    SELENIUM_HEADLESS: bool = os.getenv('SELENIUM_HEADLESS', 'true').lower() == 'true'
    SELENIUM_WAIT_TIMEOUT: int = int(os.getenv('SELENIUM_WAIT_TIMEOUT', '10'))
    SELENIUM_IMPLICIT_WAIT: int = int(os.getenv('SELENIUM_IMPLICIT_WAIT', '5'))
    
    # User Agent
    USER_AGENT: str = os.getenv('USER_AGENT', 'CanadaTechJobCompass/1.0 (Educational Project)')
    
    # Collection Targets
    TARGET_TOTAL_JOBS: int = int(os.getenv('TARGET_TOTAL_JOBS', '2200'))
    MIN_JOBS_PER_CITY: int = int(os.getenv('MIN_JOBS_PER_CITY', '50'))
    MIN_SOURCES: int = int(os.getenv('MIN_SOURCES', '3'))
    
    # Validation Rules
    MAX_JOB_AGE_DAYS: int = int(os.getenv('MAX_JOB_AGE_DAYS', '30'))
    MIN_TITLE_LENGTH: int = int(os.getenv('MIN_TITLE_LENGTH', '3'))
    MIN_DESCRIPTION_LENGTH: int = int(os.getenv('MIN_DESCRIPTION_LENGTH', '50'))
    MIN_SALARY: int = int(os.getenv('MIN_SALARY', '30000'))
    MAX_SALARY: int = int(os.getenv('MAX_SALARY', '250000'))
    
    # Feature Extraction
    SPACY_MODEL: str = os.getenv('SPACY_MODEL', 'en_core_web_sm')
    MIN_SKILL_MENTIONS: int = int(os.getenv('MIN_SKILL_MENTIONS', '3'))
    
    # Feature Flags
    ENABLE_JOBBANK: bool = os.getenv('ENABLE_JOBBANK', 'true').lower() == 'true'
    ENABLE_RAPIDAPI: bool = os.getenv('ENABLE_RAPIDAPI', 'true').lower() == 'true'
    ENABLE_RSS: bool = os.getenv('ENABLE_RSS', 'true').lower() == 'true'
    ENABLE_SELENIUM: bool = os.getenv('ENABLE_SELENIUM', 'true').lower() == 'true'
    ENABLE_CACHING: bool = os.getenv('ENABLE_CACHING', 'true').lower() == 'true'
    ENABLE_ML_PREDICTIONS: bool = os.getenv('ENABLE_ML_PREDICTIONS', 'false').lower() == 'true'
    
    # Caching Configuration
    CACHE_ENABLED: bool = os.getenv('CACHE_ENABLED', 'true').lower() == 'true'
    CACHE_DIR: str = os.getenv('CACHE_DIR', 'cache')
    CACHE_TTL_HOURS: int = int(os.getenv('CACHE_TTL_HOURS', '24'))
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', 'logs/job_scraper.log')
    LOG_MAX_BYTES: int = int(os.getenv('LOG_MAX_BYTES', '10485760'))
    LOG_BACKUP_COUNT: int = int(os.getenv('LOG_BACKUP_COUNT', '5'))
    LOG_FORMAT: str = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    LOG_DATE_FORMAT: str = os.getenv('LOG_DATE_FORMAT', '%Y-%m-%d %H:%M:%S')
    
    # Retry & Error Handling
    MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_BACKOFF_MULTIPLIER: int = int(os.getenv('RETRY_BACKOFF_MULTIPLIER', '1'))
    RETRY_MIN_WAIT: int = int(os.getenv('RETRY_MIN_WAIT', '2'))
    RETRY_MAX_WAIT: int = int(os.getenv('RETRY_MAX_WAIT', '10'))
    
    # Monitoring & Alerts
    ALERT_MIN_JOBS: int = int(os.getenv('ALERT_MIN_JOBS', '1800'))
    ALERT_MAX_ERRORS: int = int(os.getenv('ALERT_MAX_ERRORS', '50'))
    ALERT_MIN_SUCCESS_RATE: float = float(os.getenv('ALERT_MIN_SUCCESS_RATE', '0.90'))
    ALERT_EMAIL: str = os.getenv('ALERT_EMAIL', '')
    
    # Cities & Roles
    TARGET_CITIES: List[str] = os.getenv('TARGET_CITIES', 'Toronto,Saskatoon,Regina,Calgary,Edmonton,Winnipeg,Vancouver').split(',')
    TARGET_ROLES: List[str] = os.getenv('TARGET_ROLES', 'data analyst,it support,full stack developer,devops,web designer,business analyst,qa tester').split(',')
    
    # Development/Production Mode
    ENV: str = os.getenv('ENV', 'development')
    DEBUG: bool = os.getenv('DEBUG', 'false').lower() == 'true'
    TEST_MODE: bool = os.getenv('TEST_MODE', 'false').lower() == 'true'
    TEST_MODE_MAX_JOBS: int = int(os.getenv('TEST_MODE_MAX_JOBS', '50'))
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate that all required configuration is present.
        
        Returns:
            True if configuration is valid, raises ValueError otherwise
        """
        required_vars = {
            'SUPABASE_URL': cls.SUPABASE_URL,
            'SUPABASE_KEY': cls.SUPABASE_KEY,
            'SUPABASE_DB_URL': cls.SUPABASE_DB_URL,
        }
        
        missing = [key for key, value in required_vars.items() if not value]
        
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Please check your .env file."
            )
        
        return True
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production mode."""
        return cls.ENV == 'production'
    
    @classmethod
    def is_test_mode(cls) -> bool:
        """Check if running in test mode."""
        return cls.TEST_MODE


# Validate configuration on import
try:
    Config.validate()
except ValueError as e:
    print(f"⚠️  Configuration Error: {e}")
    raise
