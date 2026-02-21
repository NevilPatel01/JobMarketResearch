"""
Configuration loader for Canada Tech Job Compass.
Loads environment variables and provides access to configuration settings.
"""

import os
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration settings loaded from environment variables."""
    
    # Database Configuration
    SUPABASE_URL: str = os.getenv('SUPABASE_URL', '')
    SUPABASE_KEY: str = os.getenv('SUPABASE_KEY', '')
    SUPABASE_DB_URL: str = os.getenv('SUPABASE_DB_URL', '')
    DB_POOL_SIZE: int = int(os.getenv('DB_POOL_SIZE', '5'))
    DB_MAX_OVERFLOW: int = int(os.getenv('DB_MAX_OVERFLOW', '10'))
    
    # API Keys
    RAPIDAPI_KEY: str = os.getenv('RAPIDAPI_KEY', '')
    RAPIDAPI_HOST: str = os.getenv('RAPIDAPI_HOST', 'linkedin-jobs.p.rapidapi.com')
    
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
