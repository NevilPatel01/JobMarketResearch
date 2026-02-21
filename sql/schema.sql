-- ==============================================================================
-- CANADA TECH JOB COMPASS - DATABASE SCHEMA
-- ==============================================================================
-- PostgreSQL 14+ (Supabase compatible)
-- Run this script in Supabase SQL Editor to initialize database

-- ==============================================================================
-- TABLE 1: jobs_raw - Raw job postings
-- ==============================================================================
CREATE TABLE IF NOT EXISTS jobs_raw (
    id BIGSERIAL PRIMARY KEY,
    
    -- Source identification
    source VARCHAR(50) NOT NULL,
    job_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Basic information
    title VARCHAR(200) NOT NULL,
    company VARCHAR(200),
    city VARCHAR(100) NOT NULL,
    province CHAR(2),
    description TEXT,
    
    -- Salary information
    salary_min INTEGER CHECK (salary_min >= 0),
    salary_max INTEGER CHECK (salary_max >= salary_min),
    salary_mid INTEGER GENERATED ALWAYS AS (
        (COALESCE(salary_min, 0) + COALESCE(salary_max, 0)) / 2
    ) STORED,
    
    -- Work arrangement
    remote_type VARCHAR(50),
    
    -- Dates
    posted_date DATE,
    scraped_at TIMESTAMP DEFAULT NOW(),
    
    -- URL
    url TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Comments
COMMENT ON TABLE jobs_raw IS 'Raw job postings from all sources';
COMMENT ON COLUMN jobs_raw.source IS 'Data source: jobbank, rapidapi, workopolis, indeed';
COMMENT ON COLUMN jobs_raw.job_id IS 'Unique ID with source prefix (e.g., jobbank_12345)';
COMMENT ON COLUMN jobs_raw.salary_mid IS 'Computed midpoint of salary range';
COMMENT ON COLUMN jobs_raw.remote_type IS 'Work arrangement: remote, hybrid, onsite';

-- ==============================================================================
-- TABLE 2: jobs_features - Extracted features from job descriptions
-- ==============================================================================
CREATE TABLE IF NOT EXISTS jobs_features (
    job_id VARCHAR(255) PRIMARY KEY REFERENCES jobs_raw(job_id) ON DELETE CASCADE,
    
    -- Experience requirements
    exp_min INTEGER CHECK (exp_min >= 0),
    exp_max INTEGER CHECK (exp_max >= exp_min),
    exp_avg DECIMAL(4,2) GENERATED ALWAYS AS (
        (COALESCE(exp_min, 0) + COALESCE(exp_max, exp_min, 0)) / 2.0
    ) STORED,
    exp_level VARCHAR(20) CHECK (exp_level IN ('entry', 'junior', 'mid', 'senior', 'lead')),
    
    -- Skills (JSONB array of strings)
    skills JSONB DEFAULT '[]'::jsonb,
    
    -- Computed flags (is_junior computed from exp_min/exp_max directly, not from exp_avg)
    -- NULL experience data means we don't know, so default to FALSE (not junior)
    is_junior BOOLEAN GENERATED ALWAYS AS (
        CASE 
            WHEN exp_min IS NULL AND exp_max IS NULL THEN FALSE
            ELSE (COALESCE(exp_min, 0) + COALESCE(exp_max, exp_min, 0)) / 2.0 <= 2
        END
    ) STORED,
    is_remote BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    extracted_at TIMESTAMP DEFAULT NOW(),
    extraction_confidence DECIMAL(3,2) DEFAULT 0.8
);

-- Comments
COMMENT ON TABLE jobs_features IS 'Extracted features from job descriptions using NLP';
COMMENT ON COLUMN jobs_features.exp_avg IS 'Average experience requirement in years';
COMMENT ON COLUMN jobs_features.exp_level IS 'Inferred seniority level';
COMMENT ON COLUMN jobs_features.skills IS 'Array of technical skills (e.g., ["python", "sql", "aws"])';
COMMENT ON COLUMN jobs_features.is_junior IS 'TRUE if suitable for candidates with <=2 years experience';
COMMENT ON COLUMN jobs_features.extraction_confidence IS 'Confidence score (0.0-1.0) of feature extraction';

-- ==============================================================================
-- TABLE 3: skills_master - Reference table of tech skills
-- ==============================================================================
CREATE TABLE IF NOT EXISTS skills_master (
    skill VARCHAR(50) PRIMARY KEY,
    category VARCHAR(30) NOT NULL,
    aliases JSONB DEFAULT '[]'::jsonb,
    role_relevance JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Comments
COMMENT ON TABLE skills_master IS 'Master list of technical skills with categories';
COMMENT ON COLUMN skills_master.category IS 'Skill category: programming, database, cloud, visualization, devops, tool';
COMMENT ON COLUMN skills_master.aliases IS 'Alternative names for the skill (e.g., ["js", "javascript"])';
COMMENT ON COLUMN skills_master.role_relevance IS 'Relevance scores per role (e.g., {"data_analyst": 0.9})';

-- ==============================================================================
-- TABLE 4: scraper_metrics - Pipeline execution tracking
-- ==============================================================================
CREATE TABLE IF NOT EXISTS scraper_metrics (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_date TIMESTAMP DEFAULT NOW(),
    
    -- Collection stats
    jobs_collected INTEGER DEFAULT 0,
    jobs_failed INTEGER DEFAULT 0,
    jobs_valid INTEGER DEFAULT 0,
    jobs_duplicates INTEGER DEFAULT 0,
    
    -- Source breakdown
    sources_used VARCHAR(100)[] DEFAULT ARRAY[]::VARCHAR[],
    jobs_by_source JSONB DEFAULT '{}'::jsonb,
    
    -- Performance
    collection_time_ms INTEGER,
    processing_time_ms INTEGER,
    total_time_ms INTEGER,
    avg_collection_time_ms INTEGER GENERATED ALWAYS AS (
        CASE 
            WHEN jobs_collected > 0 THEN collection_time_ms / jobs_collected 
            ELSE 0 
        END
    ) STORED,
    
    -- Quality metrics
    validation_rate DECIMAL(5,2) GENERATED ALWAYS AS (
        CASE 
            WHEN jobs_collected > 0 THEN (jobs_valid::DECIMAL / jobs_collected * 100)
            ELSE 0 
        END
    ) STORED,
    success_rate DECIMAL(5,2) GENERATED ALWAYS AS (
        CASE 
            WHEN (jobs_collected + jobs_failed) > 0 
            THEN (jobs_collected::DECIMAL / (jobs_collected + jobs_failed) * 100)
            ELSE 0 
        END
    ) STORED,
    
    -- Errors
    errors JSONB DEFAULT '[]'::jsonb,
    warnings JSONB DEFAULT '[]'::jsonb,
    
    -- Status
    status VARCHAR(20) DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'partial'))
);

-- Comments
COMMENT ON TABLE scraper_metrics IS 'Tracks pipeline execution metrics and health';
COMMENT ON COLUMN scraper_metrics.validation_rate IS 'Percentage of collected jobs that passed validation';
COMMENT ON COLUMN scraper_metrics.success_rate IS 'Percentage of jobs successfully collected vs failed';

-- ==============================================================================
-- INDEXES - Performance optimization
-- ==============================================================================

-- jobs_raw indexes
CREATE INDEX IF NOT EXISTS idx_jobs_city ON jobs_raw(city);
CREATE INDEX IF NOT EXISTS idx_jobs_role ON jobs_raw(title);
CREATE INDEX IF NOT EXISTS idx_jobs_date ON jobs_raw(posted_date);
CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs_raw(source);
CREATE INDEX IF NOT EXISTS idx_jobs_province ON jobs_raw(province);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_jobs_city_date ON jobs_raw(city, posted_date);
CREATE INDEX IF NOT EXISTS idx_jobs_role_date ON jobs_raw(title, posted_date);
CREATE INDEX IF NOT EXISTS idx_jobs_city_role ON jobs_raw(city, title);

-- Salary range queries
CREATE INDEX IF NOT EXISTS idx_jobs_salary ON jobs_raw(salary_mid) WHERE salary_mid IS NOT NULL;

-- jobs_features indexes
CREATE INDEX IF NOT EXISTS idx_features_exp_level ON jobs_features(exp_level);
CREATE INDEX IF NOT EXISTS idx_features_is_junior ON jobs_features(is_junior);
CREATE INDEX IF NOT EXISTS idx_features_is_remote ON jobs_features(is_remote);

-- GIN index for JSONB skills array (fast containment queries)
CREATE INDEX IF NOT EXISTS idx_features_skills ON jobs_features USING GIN(skills);

-- skills_master indexes
CREATE INDEX IF NOT EXISTS idx_skills_category ON skills_master(category);

-- scraper_metrics indexes
CREATE INDEX IF NOT EXISTS idx_metrics_date ON scraper_metrics(run_date DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_status ON scraper_metrics(status);

-- ==============================================================================
-- VIEWS - Denormalized data for analysis
-- ==============================================================================

-- View: Full job details with features
CREATE OR REPLACE VIEW vw_jobs_full AS
SELECT 
    jr.job_id,
    jr.source,
    jr.title,
    jr.company,
    jr.city,
    jr.province,
    jr.salary_min,
    jr.salary_max,
    jr.salary_mid,
    jr.remote_type,
    jr.posted_date,
    jr.url,
    jf.exp_min,
    jf.exp_max,
    jf.exp_avg,
    jf.exp_level,
    jf.skills,
    jf.is_junior,
    jf.is_remote,
    jf.extraction_confidence,
    EXTRACT(EPOCH FROM (CURRENT_DATE::timestamp - jr.posted_date::timestamp)) / 86400 as days_since_posted
FROM jobs_raw jr
LEFT JOIN jobs_features jf ON jr.job_id = jf.job_id;

COMMENT ON VIEW vw_jobs_full IS 'Denormalized view combining jobs and features for easy querying';

-- View: Recent jobs (last 30 days)
CREATE OR REPLACE VIEW vw_recent_jobs AS
SELECT * FROM vw_jobs_full
WHERE posted_date >= CURRENT_DATE - INTERVAL '30 days';

COMMENT ON VIEW vw_recent_jobs IS 'Jobs posted in the last 30 days';

-- View: City statistics
CREATE OR REPLACE VIEW vw_city_stats AS
SELECT 
    jr.city,
    jr.province,
    COUNT(*) as total_jobs,
    ROUND(AVG(jf.exp_min), 1) as avg_exp_min,
    ROUND(AVG(jf.exp_max), 1) as avg_exp_max,
    ROUND(100.0 * AVG(jf.is_junior::int), 1) as junior_pct,
    ROUND(AVG(jr.salary_mid)) as avg_salary,
    ROUND(100.0 * AVG(CASE WHEN jr.remote_type IN ('remote', 'hybrid') THEN 1 ELSE 0 END), 1) as remote_pct,
    MAX(jr.posted_date) as latest_posting,
    COUNT(DISTINCT jr.source) as sources_count
FROM jobs_raw jr
LEFT JOIN jobs_features jf ON jr.job_id = jf.job_id
WHERE jr.posted_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY jr.city, jr.province;

COMMENT ON VIEW vw_city_stats IS 'Aggregated statistics per city for last 30 days';

-- ==============================================================================
-- MATERIALIZED VIEW - Pre-computed for Power BI
-- ==============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_powerbi_export AS
SELECT 
    jr.job_id,
    jr.source,
    jr.title as role,
    jr.company,
    jr.city,
    jr.province,
    jr.posted_date,
    jr.salary_min,
    jr.salary_max,
    jr.salary_mid,
    jr.remote_type,
    jf.exp_min,
    jf.exp_max,
    jf.exp_avg,
    jf.exp_level,
    jf.is_junior,
    jf.is_remote,
    jf.skills::text as skills_json,
    jsonb_array_length(COALESCE(jf.skills, '[]'::jsonb)) as skills_count,
    CASE 
        WHEN jf.exp_level = 'entry' THEN 1
        WHEN jf.exp_level = 'junior' THEN 2
        WHEN jf.exp_level = 'mid' THEN 3
        WHEN jf.exp_level = 'senior' THEN 4
        WHEN jf.exp_level = 'lead' THEN 5
        ELSE 3
    END as seniority_order,
    jr.url
FROM jobs_raw jr
LEFT JOIN jobs_features jf ON jr.job_id = jf.job_id
WHERE jr.posted_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY jr.posted_date DESC;

-- Create indexes on materialized view
CREATE INDEX IF NOT EXISTS idx_mv_powerbi_city ON mv_powerbi_export(city);
CREATE INDEX IF NOT EXISTS idx_mv_powerbi_role ON mv_powerbi_export(role);
CREATE INDEX IF NOT EXISTS idx_mv_powerbi_date ON mv_powerbi_export(posted_date);

COMMENT ON MATERIALIZED VIEW mv_powerbi_export IS 'Pre-computed export for Power BI (refresh daily)';

-- ==============================================================================
-- FUNCTIONS & TRIGGERS
-- ==============================================================================

-- Function: Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Auto-update updated_at on jobs_raw
CREATE TRIGGER trigger_update_jobs_raw_updated_at
    BEFORE UPDATE ON jobs_raw
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function: Refresh materialized view (call after pipeline)
CREATE OR REPLACE FUNCTION refresh_powerbi_export()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW mv_powerbi_export;
    RAISE NOTICE 'Power BI export refreshed at %', NOW();
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION refresh_powerbi_export IS 'Refresh Power BI export materialized view';

-- ==============================================================================
-- ROW LEVEL SECURITY (RLS) - Optional for multi-tenant future
-- ==============================================================================

-- Enable RLS on tables
ALTER TABLE jobs_raw ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs_features ENABLE ROW LEVEL SECURITY;
ALTER TABLE skills_master ENABLE ROW LEVEL SECURITY;
ALTER TABLE scraper_metrics ENABLE ROW LEVEL SECURITY;

-- Policy: Allow all operations for authenticated users (Supabase default)
CREATE POLICY "Enable all operations for authenticated users" ON jobs_raw
    FOR ALL
    USING (true);

CREATE POLICY "Enable all operations for authenticated users" ON jobs_features
    FOR ALL
    USING (true);

CREATE POLICY "Enable read access for all users" ON skills_master
    FOR SELECT
    USING (true);

CREATE POLICY "Enable all operations for authenticated users" ON scraper_metrics
    FOR ALL
    USING (true);

-- ==============================================================================
-- INITIAL DATA VALIDATION CHECKS
-- ==============================================================================

-- Check 1: Verify tables created
DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN ('jobs_raw', 'jobs_features', 'skills_master', 'scraper_metrics');
    
    IF table_count = 4 THEN
        RAISE NOTICE '✓ All tables created successfully';
    ELSE
        RAISE WARNING '✗ Expected 4 tables, found %', table_count;
    END IF;
END $$;

-- Check 2: Verify indexes created
DO $$
DECLARE
    index_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE schemaname = 'public'
    AND tablename IN ('jobs_raw', 'jobs_features', 'skills_master', 'scraper_metrics');
    
    RAISE NOTICE '✓ Created % indexes', index_count;
END $$;

-- Check 3: Verify views created
DO $$
DECLARE
    view_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO view_count
    FROM information_schema.views
    WHERE table_schema = 'public';
    
    RAISE NOTICE '✓ Created % views', view_count;
END $$;

-- ==============================================================================
-- COMPLETION MESSAGE
-- ==============================================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '==============================================================================';
    RAISE NOTICE 'CANADA TECH JOB COMPASS - DATABASE INITIALIZED';
    RAISE NOTICE '==============================================================================';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Run seed_data.sql to populate skills_master table';
    RAISE NOTICE '2. Verify connection: SELECT COUNT(*) FROM jobs_raw;';
    RAISE NOTICE '3. Start collecting jobs with the pipeline';
    RAISE NOTICE '';
    RAISE NOTICE 'Useful queries:';
    RAISE NOTICE '  - Recent jobs: SELECT * FROM vw_recent_jobs LIMIT 10;';
    RAISE NOTICE '  - City stats: SELECT * FROM vw_city_stats;';
    RAISE NOTICE '  - Metrics: SELECT * FROM scraper_metrics ORDER BY run_date DESC LIMIT 5;';
    RAISE NOTICE '';
END $$;
