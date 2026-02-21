"""
Test database connection and verify setup.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from database import get_db
from utils import setup_logger

logger = setup_logger(__name__)


def main():
    """Test database connection."""
    logger.info("=" * 60)
    logger.info("DATABASE CONNECTION TEST")
    logger.info("=" * 60)
    
    try:
        # Get database connection
        db = get_db()
        
        # Test connection
        logger.info("\n[1/2] Testing connection...")
        if db.test_connection():
            logger.info("✓ Connection successful!")
        else:
            logger.error("✗ Connection failed!")
            return False
        
        # Get table counts
        logger.info("\n[2/2] Checking tables...")
        counts = db.get_table_counts()
        
        for table, count in counts.items():
            if count is not None:
                logger.info(f"  ✓ {table}: {count} rows")
            else:
                logger.warning(f"  ⚠ {table}: Could not get count")
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ DATABASE READY!")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"\n✗ Database test failed: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
