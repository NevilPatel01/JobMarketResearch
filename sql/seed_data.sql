-- ==============================================================================
-- CANADA TECH JOB COMPASS - SEED DATA
-- ==============================================================================
-- Skills master data with categories and relevance scores
-- Run this after schema.sql

-- ==============================================================================
-- CLEAR EXISTING DATA (if re-running)
-- ==============================================================================
TRUNCATE TABLE skills_master CASCADE;

-- ==============================================================================
-- PROGRAMMING LANGUAGES
-- ==============================================================================
INSERT INTO skills_master (skill, category, aliases, role_relevance) VALUES
('python', 'programming', '["py"]', '{"data_analyst": 0.9, "devops": 0.7, "full_stack": 0.8, "qa_tester": 0.6}'),
('java', 'programming', '[]', '{"full_stack": 0.9, "devops": 0.6, "qa_tester": 0.5}'),
('javascript', 'programming', '["js", "ecmascript"]', '{"full_stack": 0.95, "web_designer": 0.9, "devops": 0.5}'),
('typescript', 'programming', '["ts"]', '{"full_stack": 0.9, "web_designer": 0.7}'),
('c++', 'programming', '["cpp", "c plus plus"]', '{"full_stack": 0.4, "qa_tester": 0.3}'),
('c#', 'programming', '["csharp", "c-sharp"]', '{"full_stack": 0.8, "devops": 0.5}'),
('go', 'programming', '["golang"]', '{"devops": 0.8, "full_stack": 0.6}'),
('ruby', 'programming', '["rb"]', '{"full_stack": 0.6}'),
('php', 'programming', '[]', '{"full_stack": 0.7, "web_designer": 0.5}'),
('swift', 'programming', '[]', '{"full_stack": 0.5}'),
('kotlin', 'programming', '[]', '{"full_stack": 0.5}'),
('scala', 'programming', '[]', '{"full_stack": 0.4, "data_analyst": 0.3}'),
('rust', 'programming', '[]', '{"devops": 0.5, "full_stack": 0.4}'),
('r', 'programming', '[]', '{"data_analyst": 0.7}');

-- ==============================================================================
-- DATABASES
-- ==============================================================================
INSERT INTO skills_master (skill, category, aliases, role_relevance) VALUES
('sql', 'database', '["structured query language"]', '{"data_analyst": 0.95, "full_stack": 0.8, "business_analyst": 0.9, "devops": 0.6}'),
('postgresql', 'database', '["postgres", "pg"]', '{"full_stack": 0.7, "devops": 0.7, "data_analyst": 0.8}'),
('mysql', 'database', '[]', '{"full_stack": 0.8, "devops": 0.6}'),
('mongodb', 'database', '["mongo"]', '{"full_stack": 0.7, "devops": 0.5}'),
('redis', 'database', '[]', '{"full_stack": 0.6, "devops": 0.7}'),
('cassandra', 'database', '[]', '{"devops": 0.5, "data_analyst": 0.4}'),
('oracle', 'database', '["oracle db"]', '{"data_analyst": 0.6, "full_stack": 0.5}'),
('dynamodb', 'database', '["dynamo db"]', '{"devops": 0.6, "full_stack": 0.5}'),
('elasticsearch', 'database', '["elastic search"]', '{"devops": 0.7, "full_stack": 0.5}'),
('mariadb', 'database', '[]', '{"full_stack": 0.6}');

-- ==============================================================================
-- CLOUD PLATFORMS
-- ==============================================================================
INSERT INTO skills_master (skill, category, aliases, role_relevance) VALUES
('aws', 'cloud', '["amazon web services", "amazon aws"]', '{"devops": 0.95, "full_stack": 0.7, "data_analyst": 0.5}'),
('azure', 'cloud', '["microsoft azure"]', '{"devops": 0.9, "full_stack": 0.6, "data_analyst": 0.5}'),
('gcp', 'cloud', '["google cloud", "google cloud platform"]', '{"devops": 0.85, "full_stack": 0.6, "data_analyst": 0.5}'),
('s3', 'cloud', '["amazon s3"]', '{"devops": 0.7, "full_stack": 0.5}'),
('ec2', 'cloud', '["amazon ec2"]', '{"devops": 0.7, "full_stack": 0.5}'),
('lambda', 'cloud', '["aws lambda"]', '{"devops": 0.6, "full_stack": 0.5}'),
('cloud functions', 'cloud', '["gcf"]', '{"devops": 0.5, "full_stack": 0.4}');

-- ==============================================================================
-- DEVOPS & CI/CD
-- ==============================================================================
INSERT INTO skills_master (skill, category, aliases, role_relevance) VALUES
('docker', 'devops', '[]', '{"devops": 0.95, "full_stack": 0.6}'),
('kubernetes', 'devops', '["k8s"]', '{"devops": 0.9, "full_stack": 0.5}'),
('jenkins', 'devops', '[]', '{"devops": 0.8, "qa_tester": 0.5}'),
('terraform', 'devops', '[]', '{"devops": 0.85}'),
('ansible', 'devops', '[]', '{"devops": 0.8}'),
('ci/cd', 'devops', '["continuous integration", "continuous deployment"]', '{"devops": 0.9, "qa_tester": 0.6}'),
('git', 'devops', '[]', '{"full_stack": 0.9, "devops": 0.95, "web_designer": 0.7, "qa_tester": 0.7}'),
('github', 'devops', '[]', '{"full_stack": 0.8, "devops": 0.85, "web_designer": 0.6}'),
('gitlab', 'devops', '[]', '{"full_stack": 0.7, "devops": 0.8}'),
('bitbucket', 'devops', '[]', '{"full_stack": 0.6, "devops": 0.7}'),
('circleci', 'devops', '[]', '{"devops": 0.6}'),
('travis ci', 'devops', '[]', '{"devops": 0.5}'),
('prometheus', 'devops', '[]', '{"devops": 0.6}'),
('grafana', 'devops', '[]', '{"devops": 0.7, "data_analyst": 0.4}');

-- ==============================================================================
-- DATA VISUALIZATION & BI TOOLS
-- ==============================================================================
INSERT INTO skills_master (skill, category, aliases, role_relevance) VALUES
('power bi', 'visualization', '["powerbi", "microsoft power bi"]', '{"data_analyst": 0.95, "business_analyst": 0.9}'),
('tableau', 'visualization', '[]', '{"data_analyst": 0.9, "business_analyst": 0.85}'),
('looker', 'visualization', '[]', '{"data_analyst": 0.7, "business_analyst": 0.7}'),
('qlik', 'visualization', '["qlikview", "qlik sense"]', '{"data_analyst": 0.6, "business_analyst": 0.6}'),
('d3.js', 'visualization', '["d3"]', '{"full_stack": 0.5, "web_designer": 0.6}'),
('matplotlib', 'visualization', '[]', '{"data_analyst": 0.6}'),
('seaborn', 'visualization', '[]', '{"data_analyst": 0.5}'),
('plotly', 'visualization', '[]', '{"data_analyst": 0.5}');

-- ==============================================================================
-- FRONTEND FRAMEWORKS
-- ==============================================================================
INSERT INTO skills_master (skill, category, aliases, role_relevance) VALUES
('react', 'frontend', '["reactjs", "react.js"]', '{"full_stack": 0.95, "web_designer": 0.8}'),
('angular', 'frontend', '["angularjs"]', '{"full_stack": 0.8, "web_designer": 0.7}'),
('vue', 'frontend', '["vue.js", "vuejs"]', '{"full_stack": 0.8, "web_designer": 0.7}'),
('html', 'frontend', '["html5"]', '{"full_stack": 0.9, "web_designer": 0.95}'),
('css', 'frontend', '["css3"]', '{"full_stack": 0.9, "web_designer": 0.95}'),
('sass', 'frontend', '["scss"]', '{"full_stack": 0.6, "web_designer": 0.7}'),
('less', 'frontend', '[]', '{"full_stack": 0.5, "web_designer": 0.6}'),
('bootstrap', 'frontend', '[]', '{"full_stack": 0.7, "web_designer": 0.8}'),
('tailwind', 'frontend', '["tailwind css"]', '{"full_stack": 0.6, "web_designer": 0.7}'),
('material-ui', 'frontend', '["mui"]', '{"full_stack": 0.5, "web_designer": 0.5}'),
('jquery', 'frontend', '[]', '{"full_stack": 0.6, "web_designer": 0.7}');

-- ==============================================================================
-- BACKEND FRAMEWORKS
-- ==============================================================================
INSERT INTO skills_master (skill, category, aliases, role_relevance) VALUES
('node.js', 'backend', '["nodejs", "node"]', '{"full_stack": 0.9, "devops": 0.5}'),
('express', 'backend', '["express.js", "expressjs"]', '{"full_stack": 0.8}'),
('django', 'backend', '[]', '{"full_stack": 0.8}'),
('flask', 'backend', '[]', '{"full_stack": 0.7}'),
('spring', 'backend', '["spring framework"]', '{"full_stack": 0.8}'),
('spring boot', 'backend', '[]', '{"full_stack": 0.85}'),
('.net', 'backend', '["dotnet", "asp.net"]', '{"full_stack": 0.8}'),
('asp.net', 'backend', '[]', '{"full_stack": 0.7}'),
('fastapi', 'backend', '[]', '{"full_stack": 0.6}'),
('rails', 'backend', '["ruby on rails"]', '{"full_stack": 0.6}'),
('laravel', 'backend', '[]', '{"full_stack": 0.6}');

-- ==============================================================================
-- TESTING & QA
-- ==============================================================================
INSERT INTO skills_master (skill, category, aliases, role_relevance) VALUES
('selenium', 'testing', '[]', '{"qa_tester": 0.9, "full_stack": 0.5}'),
('junit', 'testing', '[]', '{"qa_tester": 0.7, "full_stack": 0.6}'),
('pytest', 'testing', '[]', '{"qa_tester": 0.7, "full_stack": 0.6}'),
('jest', 'testing', '[]', '{"qa_tester": 0.7, "full_stack": 0.7}'),
('cypress', 'testing', '[]', '{"qa_tester": 0.8, "full_stack": 0.5}'),
('mocha', 'testing', '[]', '{"qa_tester": 0.6, "full_stack": 0.5}'),
('postman', 'testing', '[]', '{"qa_tester": 0.8, "full_stack": 0.6, "devops": 0.5}'),
('jmeter', 'testing', '[]', '{"qa_tester": 0.6}');

-- ==============================================================================
-- DATA SCIENCE & MACHINE LEARNING
-- ==============================================================================
INSERT INTO skills_master (skill, category, aliases, role_relevance) VALUES
('machine learning', 'data_science', '["ml"]', '{"data_analyst": 0.6, "full_stack": 0.3}'),
('deep learning', 'data_science', '["dl"]', '{"data_analyst": 0.5}'),
('tensorflow', 'data_science', '[]', '{"data_analyst": 0.5}'),
('pytorch', 'data_science', '[]', '{"data_analyst": 0.5}'),
('scikit-learn', 'data_science', '["sklearn"]', '{"data_analyst": 0.6}'),
('pandas', 'data_science', '[]', '{"data_analyst": 0.8}'),
('numpy', 'data_science', '[]', '{"data_analyst": 0.7}'),
('nlp', 'data_science', '["natural language processing"]', '{"data_analyst": 0.5}'),
('computer vision', 'data_science', '["cv"]', '{"data_analyst": 0.4}');

-- ==============================================================================
-- PROJECT MANAGEMENT & METHODOLOGIES
-- ==============================================================================
INSERT INTO skills_master (skill, category, aliases, role_relevance) VALUES
('agile', 'methodology', '[]', '{"business_analyst": 0.8, "full_stack": 0.7, "qa_tester": 0.7, "devops": 0.6}'),
('scrum', 'methodology', '[]', '{"business_analyst": 0.8, "full_stack": 0.7, "qa_tester": 0.7}'),
('jira', 'tool', '[]', '{"business_analyst": 0.8, "full_stack": 0.7, "qa_tester": 0.8, "devops": 0.6}'),
('confluence', 'tool', '[]', '{"business_analyst": 0.7, "qa_tester": 0.6}'),
('trello', 'tool', '[]', '{"business_analyst": 0.6, "web_designer": 0.5}');

-- ==============================================================================
-- OFFICE & BUSINESS TOOLS
-- ==============================================================================
INSERT INTO skills_master (skill, category, aliases, role_relevance) VALUES
('excel', 'tool', '["microsoft excel"]', '{"data_analyst": 0.9, "business_analyst": 0.95}'),
('powerpoint', 'tool', '["microsoft powerpoint"]', '{"business_analyst": 0.8}'),
('word', 'tool', '["microsoft word"]', '{"business_analyst": 0.7}'),
('google sheets', 'tool', '[]', '{"data_analyst": 0.7, "business_analyst": 0.8}'),
('google analytics', 'tool', '["ga"]', '{"data_analyst": 0.6, "business_analyst": 0.7}');

-- ==============================================================================
-- DESIGN TOOLS
-- ==============================================================================
INSERT INTO skills_master (skill, category, aliases, role_relevance) VALUES
('figma', 'design', '[]', '{"web_designer": 0.9, "full_stack": 0.4}'),
('adobe xd', 'design', '["xd"]', '{"web_designer": 0.8}'),
('sketch', 'design', '[]', '{"web_designer": 0.7}'),
('photoshop', 'design', '["adobe photoshop"]', '{"web_designer": 0.8}'),
('illustrator', 'design', '["adobe illustrator"]', '{"web_designer": 0.7}'),
('invision', 'design', '[]', '{"web_designer": 0.6}');

-- ==============================================================================
-- IT SUPPORT & NETWORKING
-- ==============================================================================
INSERT INTO skills_master (skill, category, aliases, role_relevance) VALUES
('windows', 'os', '["windows server"]', '{"it_support": 0.9, "devops": 0.6}'),
('linux', 'os', '["unix"]', '{"devops": 0.9, "full_stack": 0.6, "it_support": 0.8}'),
('macos', 'os', '[]', '{"it_support": 0.6}'),
('active directory', 'networking', '["ad"]', '{"it_support": 0.8, "devops": 0.5}'),
('networking', 'networking', '[]', '{"it_support": 0.9, "devops": 0.7}'),
('tcp/ip', 'networking', '[]', '{"it_support": 0.7, "devops": 0.7}'),
('dns', 'networking', '[]', '{"it_support": 0.7, "devops": 0.8}'),
('dhcp', 'networking', '[]', '{"it_support": 0.6, "devops": 0.6}'),
('vpn', 'networking', '[]', '{"it_support": 0.7, "devops": 0.7}'),
('firewall', 'networking', '[]', '{"it_support": 0.7, "devops": 0.8}');

-- ==============================================================================
-- VERIFICATION QUERIES
-- ==============================================================================

-- Count skills by category
DO $$
DECLARE
    rec RECORD;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '==============================================================================';
    RAISE NOTICE 'SKILLS MASTER DATA - SEEDING COMPLETE';
    RAISE NOTICE '==============================================================================';
    RAISE NOTICE '';
    
    FOR rec IN 
        SELECT category, COUNT(*) as count
        FROM skills_master
        GROUP BY category
        ORDER BY count DESC
    LOOP
        RAISE NOTICE 'Category: % → % skills', RPAD(rec.category, 20), rec.count;
    END LOOP;
    
    RAISE NOTICE '';
    RAISE NOTICE 'Total skills: %', (SELECT COUNT(*) FROM skills_master);
    RAISE NOTICE '';
    RAISE NOTICE 'Sample queries:';
    RAISE NOTICE '  - All Python-related: SELECT * FROM skills_master WHERE skill LIKE ''%python%'';';
    RAISE NOTICE '  - Cloud skills: SELECT * FROM skills_master WHERE category = ''cloud'';';
    RAISE NOTICE '  - High relevance for data analysts: ';
    RAISE NOTICE '    SELECT skill, role_relevance->''data_analyst'' as relevance ';
    RAISE NOTICE '    FROM skills_master ';
    RAISE NOTICE '    WHERE role_relevance->''data_analyst'' IS NOT NULL ';
    RAISE NOTICE '    ORDER BY (role_relevance->''data_analyst'')::text::numeric DESC;';
    RAISE NOTICE '';
END $$;

-- Show sample skills
SELECT 'Sample Skills by Category:' as notice;
SELECT category, skill, ARRAY_LENGTH(aliases::text[], 1) as alias_count
FROM skills_master
ORDER BY category, skill
LIMIT 20;
