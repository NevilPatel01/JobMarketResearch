"""
Database connection management for Canada Tech Job Compass.
"""

from contextlib import contextmanager
from typing import Generator
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from utils.config import Config
from utils.config import _derive_pooler_url

logger = logging.getLogger(__name__)

# Supabase pooler regions (project lives in one of these)
_POOLER_REGIONS = [
    'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
    'ca-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3',
    'eu-central-1', 'eu-central-2', 'eu-north-1',
    'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', 'ap-northeast-2', 'ap-south-1',
    'sa-east-1',
]


def _create_engine_with_retry():
    """Create engine, trying other pooler regions when derived pooler returns Tenant/user not found."""
    db_url = Config.get_db_url()
    if not db_url:
        raise ValueError(
            "SUPABASE_DB_URL or SUPABASE_DB_POOLER_URL not configured. "
            "Get from Supabase Dashboard → Settings → Database."
        )
    # Explicit pooler or direct URL - try once
    if Config.SUPABASE_DB_POOLER_URL and 'pooler.supabase.com' in Config.SUPABASE_DB_POOLER_URL:
        engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=Config.DB_POOL_SIZE,
            max_overflow=Config.DB_MAX_OVERFLOW,
            pool_pre_ping=True,
            echo=Config.DEBUG,
            future=True
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connected (explicit pooler URL)")
        return engine
    if 'pooler' not in db_url:
        try:
            engine = create_engine(
                db_url,
                poolclass=QueuePool,
                pool_size=Config.DB_POOL_SIZE,
                max_overflow=Config.DB_MAX_OVERFLOW,
                pool_pre_ping=True,
                echo=Config.DEBUG,
                future=True
            )
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connected (direct URL)")
            return engine
        except Exception as e:
            if 'could not translate host' in str(e).lower() or 'nodename' in str(e).lower():
                logger.info("Direct URL failed (DNS), trying pooler regions...")
                if not Config.SUPABASE_DB_URL:
                    raise
            else:
                raise
    # Derived pooler or fallback from DNS - try Session (5432) then Transaction (6543) per region
    regions = [Config.SUPABASE_POOLER_REGION] + [r for r in _POOLER_REGIONS if r != Config.SUPABASE_POOLER_REGION]
    last_error = None
    for use_session in (True, False):
        mode = "Session" if use_session else "Transaction"
        for region in regions:
            derived = _derive_pooler_url(Config.SUPABASE_DB_URL, region, use_session_port=use_session)
            if not derived:
                continue
            try:
                engine = create_engine(
                    derived,
                    poolclass=QueuePool,
                    pool_size=Config.DB_POOL_SIZE,
                    max_overflow=Config.DB_MAX_OVERFLOW,
                    pool_pre_ping=True,
                    echo=Config.DEBUG,
                    future=True
                )
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                logger.info(f"Database connected (pooler {mode} mode, region={region})")
                return engine
            except Exception as e:
                last_error = e
                err_lower = str(e).lower()
                if 'tenant' in err_lower or 'user not found' in err_lower:
                    continue  # Try next region
                raise
    import re
    project_ref = ""
    if Config.SUPABASE_DB_URL:
        m = re.search(r'db\.([a-z0-9]+)\.supabase\.co', Config.SUPABASE_DB_URL)
        if m:
            project_ref = m.group(1)
    dashboard_link = f"https://supabase.com/dashboard/project/{project_ref}?showConnect=true" if project_ref else "https://supabase.com/dashboard"
    msg = (
        "All pooler regions failed (Tenant or user not found). "
        "Fix: Copy the pooler URI from Supabase Dashboard → Connect → Session or Transaction pooler, "
        f"then set SUPABASE_DB_POOLER_URL in .env — {dashboard_link}"
    )
    logger.error(msg)
    import sys
    print(f"\n{msg}\n", file=sys.stderr)
    raise last_error


class DatabaseConnection:
    """Manages database connections with connection pooling."""
    
    def __init__(self):
        """Initialize database connection with connection pooling."""
        logger.info("Initializing database connection...")
        self.engine = _create_engine_with_retry()
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        logger.info("Database connection initialized successfully")
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope for database operations.
        
        Yields:
            SQLAlchemy Session object
            
        Example:
            with db.get_session() as session:
                jobs = session.query(JobRaw).all()
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database transaction failed: {e}", exc_info=True)
            raise
        finally:
            session.close()
    
    def test_connection(self) -> bool:
        """
        Test database connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                value = result.scalar()
                if value == 1:
                    logger.info("✓ Database connection test successful")
                    return True
                else:
                    logger.error("✗ Database connection test failed: unexpected result")
                    return False
        except Exception as e:
            logger.error(f"✗ Database connection test failed: {e}", exc_info=True)
            return False
    
    def get_table_counts(self) -> dict:
        """
        Get row counts for all main tables.
        
        Returns:
            Dictionary with table names and row counts
        """
        counts = {}
        tables = ['jobs_raw', 'jobs_features', 'skills_master', 'scraper_metrics']
        
        with self.engine.connect() as conn:
            for table in tables:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    counts[table] = result.scalar()
                except Exception as e:
                    logger.warning(f"Could not get count for {table}: {e}")
                    counts[table] = None
        
        return counts
    
    def close(self):
        """Close database connection and dispose of connection pool."""
        logger.info("Closing database connection...")
        self.engine.dispose()
        logger.info("Database connection closed")


# Global database connection instance
_db_connection = None


def get_db() -> DatabaseConnection:
    """
    Get or create global database connection instance.
    
    Returns:
        DatabaseConnection instance
    """
    global _db_connection
    if _db_connection is None:
        _db_connection = DatabaseConnection()
    return _db_connection


def close_db():
    """Close global database connection."""
    global _db_connection
    if _db_connection is not None:
        _db_connection.close()
        _db_connection = None
