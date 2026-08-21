-- NIR_MISTRAL Database Initialization Script
-- This script creates the initial database schema and extensions

-- Enable required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "hstore";

-- Create schema for NIR_MISTRAL application
CREATE SCHEMA IF NOT EXISTS nir_mistral;
SET search_path TO nir_mistral, public;

-- Create tables for Django models (these will be created by Django migrations)
-- This script is mainly for setting up extensions and initial data

-- Create a function to check if a table exists
CREATE OR REPLACE FUNCTION table_exists(table_name text) RETURNS boolean AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = current_schema() 
        AND table_name = lower(table_name)
    );
END;
$$ LANGUAGE plpgsql;

-- Create initial configuration table
CREATE TABLE IF NOT EXISTS nir_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial configuration values
INSERT INTO nir_config (key, value, description) 
VALUES 
    ('database_version', '1.0.0', 'Current database schema version'),
    ('init_timestamp', CURRENT_TIMESTAMP::text, 'Database initialization timestamp'),
    ('app_name', 'NIR_MISTRAL', 'Application name'),
    ('app_version', '1.0.0', 'Application version')
ON CONFLICT (key) DO NOTHING;

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_timestamp() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for automatic timestamp updates
DROP TRIGGER IF EXISTS update_nir_config_timestamp ON nir_config;
CREATE TRIGGER update_nir_config_timestamp
    BEFORE UPDATE ON nir_config
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_nir_config_key ON nir_config(key);

-- Log the initialization
INSERT INTO nir_config (key, value, description) 
VALUES ('last_init_script', 'init-db.sql', 'Last initialization script executed')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP;

-- Output completion message
DO $$
BEGIN
    RAISE NOTICE 'NIR_MISTRAL database initialization completed successfully';
END $$;