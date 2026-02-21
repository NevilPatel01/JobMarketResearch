"""
SQLAlchemy ORM models for Canada Tech Job Compass database.
"""

from datetime import datetime, date
from typing import Dict, Any, Optional
from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, Boolean,
    DECIMAL, CheckConstraint, ForeignKey, CHAR
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class JobRaw(Base):
    """Raw job postings table."""
    
    __tablename__ = 'jobs_raw'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False)
    job_id = Column(String(255), unique=True, nullable=False)
    title = Column(String(200), nullable=False)
    company = Column(String(200))
    city = Column(String(100), nullable=False)
    province = Column(CHAR(2))
    description = Column(Text)
    salary_min = Column(Integer, CheckConstraint('salary_min >= 0'))
    salary_max = Column(Integer, CheckConstraint('salary_max >= salary_min'))
    remote_type = Column(String(50))
    posted_date = Column(Date)
    scraped_at = Column(DateTime, default=datetime.now)
    url = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationship
    features = relationship("JobFeatures", back_populates="job", uselist=False, cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            'id': self.id,
            'source': self.source,
            'job_id': self.job_id,
            'title': self.title,
            'company': self.company,
            'city': self.city,
            'province': self.province,
            'description': self.description,
            'salary_min': self.salary_min,
            'salary_max': self.salary_max,
            'remote_type': self.remote_type,
            'posted_date': self.posted_date.isoformat() if self.posted_date else None,
            'scraped_at': self.scraped_at.isoformat() if self.scraped_at else None,
            'url': self.url
        }
    
    def __repr__(self) -> str:
        return f"<JobRaw(job_id='{self.job_id}', title='{self.title}', city='{self.city}')>"


class JobFeatures(Base):
    """Extracted job features table."""
    
    __tablename__ = 'jobs_features'
    
    job_id = Column(String(255), ForeignKey('jobs_raw.job_id', ondelete='CASCADE'), primary_key=True)
    exp_min = Column(Integer, CheckConstraint('exp_min >= 0'))
    exp_max = Column(Integer, CheckConstraint('exp_max >= exp_min'))
    exp_level = Column(String(20), CheckConstraint("exp_level IN ('entry', 'junior', 'mid', 'senior', 'lead')"))
    skills = Column(JSONB, default=[])
    is_remote = Column(Boolean, default=False)
    extracted_at = Column(DateTime, default=datetime.now)
    extraction_confidence = Column(DECIMAL(3, 2), default=0.8)
    
    # Relationship
    job = relationship("JobRaw", back_populates="features")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            'job_id': self.job_id,
            'exp_min': self.exp_min,
            'exp_max': self.exp_max,
            'exp_level': self.exp_level,
            'skills': self.skills,
            'is_remote': self.is_remote,
            'extracted_at': self.extracted_at.isoformat() if self.extracted_at else None,
            'extraction_confidence': float(self.extraction_confidence) if self.extraction_confidence else None
        }
    
    def __repr__(self) -> str:
        return f"<JobFeatures(job_id='{self.job_id}', exp_level='{self.exp_level}')>"


class SkillsMaster(Base):
    """Skills reference table."""
    
    __tablename__ = 'skills_master'
    
    skill = Column(String(50), primary_key=True)
    category = Column(String(30), nullable=False)
    aliases = Column(JSONB, default=[])
    role_relevance = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            'skill': self.skill,
            'category': self.category,
            'aliases': self.aliases,
            'role_relevance': self.role_relevance
        }
    
    def __repr__(self) -> str:
        return f"<SkillsMaster(skill='{self.skill}', category='{self.category}')>"


class ScraperMetrics(Base):
    """Pipeline execution metrics table."""
    
    __tablename__ = 'scraper_metrics'
    
    run_id = Column(String(36), primary_key=True)  # UUID as string
    run_date = Column(DateTime, default=datetime.now)
    jobs_collected = Column(Integer, default=0)
    jobs_failed = Column(Integer, default=0)
    jobs_valid = Column(Integer, default=0)
    jobs_duplicates = Column(Integer, default=0)
    sources_used = Column(ARRAY(String(100)), default=[])
    jobs_by_source = Column(JSONB, default={})
    collection_time_ms = Column(Integer)
    processing_time_ms = Column(Integer)
    total_time_ms = Column(Integer)
    errors = Column(JSONB, default=[])
    warnings = Column(JSONB, default=[])
    status = Column(String(20), CheckConstraint("status IN ('running', 'completed', 'failed', 'partial')"), default='running')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            'run_id': self.run_id,
            'run_date': self.run_date.isoformat() if self.run_date else None,
            'jobs_collected': self.jobs_collected,
            'jobs_failed': self.jobs_failed,
            'jobs_valid': self.jobs_valid,
            'jobs_duplicates': self.jobs_duplicates,
            'sources_used': self.sources_used,
            'jobs_by_source': self.jobs_by_source,
            'collection_time_ms': self.collection_time_ms,
            'processing_time_ms': self.processing_time_ms,
            'total_time_ms': self.total_time_ms,
            'errors': self.errors,
            'warnings': self.warnings,
            'status': self.status
        }
    
    def __repr__(self) -> str:
        return f"<ScraperMetrics(run_id='{self.run_id}', status='{self.status}', jobs_collected={self.jobs_collected})>"
