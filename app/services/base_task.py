"""
Base Celery Task with database session management.
Shared by all task modules to avoid duplicating the DatabaseTask class.
"""
from typing import Optional
from celery import Task
from sqlalchemy.orm import Session

from app.database import SessionLocal


class DatabaseTask(Task):
    """Base task that provides a database session"""
    _db: Optional[Session] = None

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        """Clean up database connection after task completes"""
        if self._db is not None:
            self._db.close()
            self._db = None
