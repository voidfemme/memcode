"""Add function versioning and testing framework

Revision ID: 001
Revises: 
Create Date: 2025-01-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create functions table with versioning
    op.create_table(
        'functions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('language', sa.String(50), nullable=True),
        
        # Versioning system
        sa.Column('version', sa.Integer(), nullable=True),
        sa.Column('base_function_id', sa.String(), nullable=True),
        sa.Column('is_latest_version', sa.Boolean(), nullable=True),
        sa.Column('parent_version_id', sa.String(), nullable=True),
        sa.Column('change_summary', sa.Text(), nullable=True),
        
        # Author tracking
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('modified_by', sa.String(255), nullable=True),
        
        # Embeddings
        sa.Column('description_embedding', sa.Text(), nullable=True),
        
        # Metadata
        sa.Column('parameters_schema', sa.Text(), nullable=True),
        sa.Column('usage_examples', sa.Text(), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        
        # Testing framework
        sa.Column('test_cases', sa.Text(), nullable=True),
        sa.Column('test_results', sa.Text(), nullable=True),
        sa.Column('last_test_run', sa.DateTime(), nullable=True),
        sa.Column('test_success_count', sa.Integer(), nullable=True),
        sa.Column('test_failure_count', sa.Integer(), nullable=True),
        
        # Performance tracking
        sa.Column('execution_count', sa.Integer(), nullable=True),
        sa.Column('success_rate', sa.Float(), nullable=True),
        sa.Column('avg_execution_time_ms', sa.Float(), nullable=True),
        sa.Column('total_execution_time_ms', sa.Integer(), nullable=True),
        
        # Security and quality
        sa.Column('security_score', sa.Float(), nullable=True),
        sa.Column('complexity_score', sa.Float(), nullable=True),
        sa.Column('code_quality_score', sa.Float(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['base_function_id'], ['functions.id'], ),
    )
    
    # Create indexes
    op.create_index(op.f('ix_functions_name'), 'functions', ['name'], unique=False)
    op.create_index(op.f('ix_functions_language'), 'functions', ['language'], unique=False)
    op.create_index(op.f('ix_functions_version'), 'functions', ['version'], unique=False)
    op.create_index(op.f('ix_functions_base_function_id'), 'functions', ['base_function_id'], unique=False)
    op.create_index(op.f('ix_functions_is_latest_version'), 'functions', ['is_latest_version'], unique=False)
    op.create_index(op.f('ix_functions_created_by'), 'functions', ['created_by'], unique=False)
    op.create_index(op.f('ix_functions_modified_by'), 'functions', ['modified_by'], unique=False)
    op.create_index(op.f('ix_functions_created_at'), 'functions', ['created_at'], unique=False)
    op.create_index(op.f('ix_functions_is_active'), 'functions', ['is_active'], unique=False)
    
    # Create conversation_memory table
    op.create_table(
        'conversation_memory',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('conversation_id', sa.String(), nullable=True),
        sa.Column('user_message', sa.Text(), nullable=False),
        sa.Column('assistant_response', sa.Text(), nullable=False),
        sa.Column('context_used', sa.Text(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('user_embedding', sa.Text(), nullable=True),
        sa.Column('assistant_embedding', sa.Text(), nullable=True),
        sa.Column('user_feedback', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index(op.f('ix_conversation_memory_conversation_id'), 'conversation_memory', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_conversation_memory_timestamp'), 'conversation_memory', ['timestamp'], unique=False)
    op.create_index(op.f('ix_conversation_memory_user_id'), 'conversation_memory', ['user_id'], unique=False)
    
    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('message_count', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('functions_generated', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('last_activity', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index(op.f('ix_conversations_user_id'), 'conversations', ['user_id'], unique=False)
    op.create_index(op.f('ix_conversations_is_active'), 'conversations', ['is_active'], unique=False)
    op.create_index(op.f('ix_conversations_started_at'), 'conversations', ['started_at'], unique=False)
    
    # Create function_executions table
    op.create_table(
        'function_executions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('function_id', sa.String(), nullable=False),
        sa.Column('execution_context', sa.String(255), nullable=True),
        sa.Column('input_data', sa.Text(), nullable=True),
        sa.Column('output_data', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=False),
        sa.Column('memory_usage_mb', sa.Float(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('security_violations', sa.Text(), nullable=True),
        sa.Column('resource_usage', sa.Text(), nullable=True),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.Column('executed_by', sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['function_id'], ['functions.id'], ),
    )
    
    op.create_index(op.f('ix_function_executions_function_id'), 'function_executions', ['function_id'], unique=False)
    op.create_index(op.f('ix_function_executions_success'), 'function_executions', ['success'], unique=False)
    op.create_index(op.f('ix_function_executions_executed_at'), 'function_executions', ['executed_at'], unique=False)
    op.create_index(op.f('ix_function_executions_executed_by'), 'function_executions', ['executed_by'], unique=False)
    
    # Create function_dependencies table
    op.create_table(
        'function_dependencies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('function_id', sa.String(), nullable=False),
        sa.Column('depends_on_function_id', sa.String(), nullable=False),
        sa.Column('dependency_type', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['depends_on_function_id'], ['functions.id'], ),
        sa.ForeignKeyConstraint(['function_id'], ['functions.id'], ),
    )
    
    op.create_index(op.f('ix_function_dependencies_function_id'), 'function_dependencies', ['function_id'], unique=False)
    op.create_index(op.f('ix_function_dependencies_depends_on_function_id'), 'function_dependencies', ['depends_on_function_id'], unique=False)
    op.create_index(op.f('ix_function_dependencies_is_active'), 'function_dependencies', ['is_active'], unique=False)


def downgrade() -> None:
    op.drop_table('function_dependencies')
    op.drop_table('function_executions')
    op.drop_table('conversations')
    op.drop_table('conversation_memory')
    op.drop_table('functions')