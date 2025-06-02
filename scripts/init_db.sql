-- Initialize MemCode database with pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create initial admin user (optional)
-- INSERT INTO users (id, username, email) VALUES 
-- ('admin', 'admin', 'admin@memcode.local');

-- Create indexes for better performance
-- These will be created by Alembic migrations, but can be pre-created here
