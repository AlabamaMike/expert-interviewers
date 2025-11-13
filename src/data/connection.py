"""
Database connection management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import logging

from ..config import settings

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Database connection manager"""

    def __init__(self, database_url: str = None):
        """
        Initialize database connection

        Args:
            database_url: Database URL (uses settings if not provided)
        """
        self.database_url = database_url or settings.database_url

        # Create engine
        self.engine = create_engine(
            self.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,  # Verify connections before using
            echo=settings.debug,  # Log SQL in debug mode
        )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        logger.info("Database connection initialized")

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()

    def close(self):
        """Close database connection"""
        self.engine.dispose()
        logger.info("Database connection closed")


# Global database connection instance
_db_connection = None


def get_db_connection() -> DatabaseConnection:
    """Get or create global database connection"""
    global _db_connection
    if _db_connection is None:
        _db_connection = DatabaseConnection()
    return _db_connection


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI endpoints to get database session

    Usage:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            items = db.query(Item).all()
            return items
    """
    db = get_db_connection().get_session()
    try:
        yield db
    finally:
        db.close()
