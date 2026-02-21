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

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Manages database connections with connection pooling."""
    
    def __init__(self):
        """Initialize database connection with connection pooling."""
        if not Config.SUPABASE_DB_URL:
            raise ValueError("SUPABASE_DB_URL not configured in environment variables")
        
        logger.info("Initializing database connection...")
        
        self.engine = create_engine(
            Config.SUPABASE_DB_URL,
            poolclass=QueuePool,
            pool_size=Config.DB_POOL_SIZE,
            max_overflow=Config.DB_MAX_OVERFLOW,
            pool_pre_ping=True,  # Verify connections before use
            echo=Config.DEBUG,  # SQL query logging in debug mode
            future=True
        )
        
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
