"""
SQLAlchemy models for functions, memory, and conversations.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, String, Text, Integer, DateTime, Boolean, JSON, Float, ForeignKey
from sqlalchemy.dialects.sqlite import BLOB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Function(Base):
    """Generated or stored functions for semantic search."""
    
    __tablename__ = "functions"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(50), default="python", index=True)
    
    # Versioning system
    version: Mapped[int] = mapped_column(Integer, default=1, index=True)
    base_function_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("functions.id"), nullable=True, index=True)
    is_latest_version: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    parent_version_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Author and modification tracking
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    modified_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    # Store embeddings as JSON for SQLite compatibility
    description_embedding: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Function metadata
    parameters_schema: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON as string
    usage_examples: Mapped[Optional[str]] = mapped_column(Text, nullable=True)     # JSON as string
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)               # JSON as string
    
    # Testing framework fields
    test_cases: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON as string
    test_results: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON as string
    last_test_run: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    test_success_count: Mapped[int] = mapped_column(Integer, default=0)
    test_failure_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Performance tracking
    execution_count: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_execution_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_execution_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    
    # Security and reliability
    security_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0.0 to 1.0
    complexity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # McCabe complexity
    code_quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    def __repr__(self):
        return f"<Function(name='{self.name}', version={self.version}, language='{self.language}')>"


class ConversationMemory(Base):
    """Conversation history with embeddings for context retrieval."""
    
    __tablename__ = "conversation_memory"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(String, index=True)
    
    # Message content
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    assistant_response: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Context information
    context_used: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON as string
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Embeddings for retrieval (stored as JSON strings for SQLite)
    user_embedding: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assistant_embedding: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Quality metrics
    user_feedback: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # -1, 0, 1
    
    # Metadata
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    def __repr__(self):
        return f"<ConversationMemory(conversation_id='{self.conversation_id}', timestamp='{self.timestamp}')>"


class Conversation(Base):
    """Conversation sessions and metadata."""
    
    __tablename__ = "conversations"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Conversation metadata
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    functions_generated: Mapped[int] = mapped_column(Integer, default=0)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    # Timestamps
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Conversation(id='{self.id}', message_count={self.message_count})>"


class FunctionExecution(Base):
    """Track function execution history and performance metrics."""
    
    __tablename__ = "function_executions"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    function_id: Mapped[str] = mapped_column(String, ForeignKey("functions.id"), nullable=False, index=True)
    execution_context: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # 'test', 'user', 'validation'
    
    # Execution details
    input_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON as string
    output_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON as string
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Performance metrics
    execution_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    memory_usage_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    
    # Security metrics
    security_violations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON as string
    resource_usage: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON as string
    
    # Metadata
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    executed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    def __repr__(self):
        return f"<FunctionExecution(function_id='{self.function_id}', success={self.success})>"


class FunctionDependency(Base):
    """Track dependencies between functions."""
    
    __tablename__ = "function_dependencies"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    function_id: Mapped[str] = mapped_column(String, ForeignKey("functions.id"), nullable=False, index=True)
    depends_on_function_id: Mapped[str] = mapped_column(String, ForeignKey("functions.id"), nullable=False, index=True)
    dependency_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'calls', 'imports', 'references'
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    def __repr__(self):
        return f"<FunctionDependency(function_id='{self.function_id}', depends_on='{self.depends_on_function_id}')>"
