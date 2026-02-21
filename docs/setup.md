# Setup Guide

## Quick Start (30 minutes)

This guide will help you set up the Canada Tech Job Compass project from scratch.

```mermaid
%%{init: {'theme':'base', 'themeVariables': { 'primaryColor':'#0ea5e9'}}}%%
flowchart TB
    START([Start Setup]) --> VENV[Create venv]
    VENV --> DEPS[Install dependencies]
    DEPS --> SPACY[spacy download en_core_web_sm]
    SPACY --> ENV[Copy .env.example → .env]
    ENV --> SUPABASE[Create Supabase project]
    SUPABASE --> SCHEMA[Run schema.sql]
    SCHEMA --> SEED[Run seed_data.sql]
    SEED --> RAPID[Get RapidAPI key]
    RAPID --> VERIFY[python run.py stats]
    VERIFY --> DONE([✓ Ready!])
    
    style START fill:#e0f2fe
    style DONE fill:#10b981
```

---

## Prerequisites

### Required Software
- **Python 3.11+**: [Download](https://www.python.org/downloads/)
- **Git**: [Download](https://git-scm.com/downloads)
- **Chrome/Chromium**: For Selenium web scraping
- **PostgreSQL Client** (optional): For direct database access

### Required Accounts
1. **Supabase Account** (Free tier)
   - Sign up: https://supabase.com
   - Provides PostgreSQL database hosting
   
2. **RapidAPI Account** (Free tier)
   - Sign up: https://rapidapi.com/auth/sign-up
   - Subscribe to "Mantiks Canada Jobs API"

---

## Step 1: Clone/Setup Repository

```bash
# If cloning from GitHub
git clone https://github.com/NevilPatel01/canada-tech-job-compass.git
cd canada-tech-job-compass

# If starting fresh
mkdir JobMarket
cd JobMarket
```

---

## Step 2: Create Virtual Environment

### macOS/Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

### Windows
```bash
python -m venv venv
venv\Scripts\activate
```

**Verify activation**: Your terminal prompt should show `(venv)` prefix.

---

## Step 3: Install Dependencies

```bash
# Upgrade pip first
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt

# Download spaCy language model (required for NLP)
python -m spacy download en_core_web_sm

# Verify installation
python -c "import requests, bs4, selenium, spacy, pandas, sqlalchemy; print('✓ All packages installed successfully!')"
```

**Expected output**: `✓ All packages installed successfully!`

---

## Step 4: Set Up Supabase Database

### 4.1 Create Supabase Project
1. Go to: https://supabase.com/dashboard
2. Click "New Project"
3. Project name: `canada-tech-jobs-2026`
4. Database password: Generate strong password (save it!)
5. Region: Choose closest to you (e.g., US East)
6. Click "Create new project" (takes 2-3 minutes)

### 4.2 Get Connection Details
1. Click on project → Settings (⚙️) → Database
2. Copy these values:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **Anon/Public Key**: `eyJhbGc...`
   - **Connection String**: `postgresql://postgres:[password]@db.xxxxx.supabase.co:5432/postgres`

### 4.3 Run Database Schema
1. In Supabase dashboard, go to SQL Editor
2. Open `sql/schema.sql` from this project
3. Copy the entire SQL script
4. Paste into SQL Editor and click "Run"
5. Verify tables created: Check "Table Editor" tab → Should see `jobs_raw`, `jobs_features`, `skills_master`

### 4.4 Seed Skills Data
1. Open `sql/seed_data.sql`
2. Copy and run in SQL Editor
3. Verify: `SELECT COUNT(*) FROM skills_master;` → Should return ~50 rows

---

## Step 5: Get RapidAPI Key

### 5.1 Sign Up for RapidAPI
1. Go to: https://rapidapi.com/auth/sign-up
2. Sign up with email or GitHub
3. Verify email address

### 5.2 Subscribe to Jobs API
1. Search for "Mantiks Canada Jobs API" or "FantasticJobs API"
2. Click on API → "Subscribe to Test"
3. Choose **Basic (Free) plan**:
   - 100-500 requests/month
   - No credit card required
4. Click "Subscribe"

### 5.3 Get API Key
1. Go to: https://rapidapi.com/developer/apps
2. Click on your default application
3. Copy **Application Key** (starts with your username)
4. Or find it in API page under "Code Snippets" → Header: `X-RapidAPI-Key`

---

## Step 6: Configure Environment Variables

### 6.1 Create .env File
```bash
# Copy template
cp .env.example .env

# Open in text editor
# macOS: open .env
# Windows: notepad .env
# Linux: nano .env
```

### 6.2 Fill in Values
Replace these placeholders with your actual values:

```bash
# Supabase (from Step 4.2)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGc...your-anon-key
SUPABASE_DB_URL=postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres

# RapidAPI (from Step 5.3)
RAPIDAPI_KEY=your-rapidapi-key-here
```

**Important**: Never commit `.env` to git! It's already in `.gitignore`.

### 6.3 Verify Environment
```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('✓ Environment loaded' if os.getenv('SUPABASE_URL') else '✗ .env not loaded correctly')"
```

---

## Step 7: Test Database Connection

Create a test script `test_connection.py`:

```python
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# Test database connection
db_url = os.getenv('SUPABASE_DB_URL')
engine = create_engine(db_url)

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM skills_master"))
        count = result.scalar()
        print(f"✓ Database connected! Skills in database: {count}")
except Exception as e:
    print(f"✗ Database connection failed: {e}")
```

Run test:
```bash
python test_connection.py
```

**Expected output**: `✓ Database connected! Skills in database: 50`

---

## Step 8: Test Web Scraping

Create a test script `test_scraper.py`:

```python
import requests
from bs4 import BeautifulSoup

url = "https://www.jobbank.gc.ca/jobsearch/jobsearch?searchstring=data+analyst&location=Toronto&postedDate=30"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.content, 'html.parser')
    jobs = soup.find_all('article', class_='resultJobItem')
    print(f"✓ Scraping works! Found {len(jobs)} jobs")
except Exception as e:
    print(f"✗ Scraping failed: {e}")
```

Run test:
```bash
python test_scraper.py
```

**Expected output**: `✓ Scraping works! Found 20 jobs` (number varies)

---

## Step 9: Test RapidAPI

Create a test script `test_rapidapi.py`:

```python
import os
import requests
from dotenv import load_dotenv

load_dotenv()

url = "https://mantiks-jobs-v1.p.rapidapi.com/jobs"
headers = {
    'X-RapidAPI-Key': os.getenv('RAPIDAPI_KEY'),
    'X-RapidAPI-Host': 'mantiks-jobs-v1.p.rapidapi.com'
}
params = {'country': 'CA', 'province': 'ON', 'title': 'developer', 'limit': 10}

try:
    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    jobs = data.get('jobs', [])
    print(f"✓ RapidAPI works! Found {len(jobs)} jobs")
except Exception as e:
    print(f"✗ RapidAPI failed: {e}")
    print("Check your RAPIDAPI_KEY in .env file")
```

Run test:
```bash
python test_rapidapi.py
```

**Expected output**: `✓ RapidAPI works! Found 10 jobs`

---

## Step 10: Run First Data Collection (Test Mode)

Create a simple test pipeline:

```python
# test_pipeline.py
import os
from dotenv import load_dotenv

load_dotenv()

print("="*60)
print("CANADA TECH JOB COMPASS - TEST RUN")
print("="*60)

# Test imports
print("\n[1/5] Testing imports...")
try:
    import requests
    import pandas as pd
    from sqlalchemy import create_engine
    import spacy
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    exit(1)

# Test environment
print("\n[2/5] Testing environment variables...")
required_vars = ['SUPABASE_URL', 'SUPABASE_KEY', 'SUPABASE_DB_URL', 'RAPIDAPI_KEY']
missing = [var for var in required_vars if not os.getenv(var)]
if missing:
    print(f"✗ Missing variables: {missing}")
    exit(1)
print("✓ All environment variables set")

# Test database
print("\n[3/5] Testing database connection...")
try:
    engine = create_engine(os.getenv('SUPABASE_DB_URL'))
    with engine.connect() as conn:
        result = conn.execute("SELECT 1")
        print("✓ Database connected")
except Exception as e:
    print(f"✗ Database connection failed: {e}")
    exit(1)

# Test spaCy model
print("\n[4/5] Testing spaCy model...")
try:
    nlp = spacy.load('en_core_web_sm')
    print("✓ spaCy model loaded")
except Exception as e:
    print(f"✗ spaCy model not found. Run: python -m spacy download en_core_web_sm")
    exit(1)

print("\n[5/5] All tests passed!")
print("="*60)
print("✓ SETUP COMPLETE - Ready to collect jobs!")
print("="*60)
```

Run test:
```bash
python test_pipeline.py
```

---

## Step 11: Verify Directory Structure

Your project should look like this:

```
JobMarket/
├── .env                       # Your secrets (NOT in git)
├── .env.example              # Template
├── .gitignore                # Git ignore rules
├── .cursorrules              # Cursor AI rules (NOT in git)
├── requirements.txt          # Python dependencies
├── ProjectIdea.md           # Project documentation
├── README.md                # Main readme
│
├── docs/                    # Documentation (NOT in git)
│   ├── architecture.md
│   ├── api-integration.md
│   ├── data-pipeline.md
│   ├── analysis-queries.md
│   └── setup.md
│
├── src/                     # Source code
│   ├── collectors/
│   ├── processors/
│   ├── analyzers/
│   ├── database/
│   └── utils/
│
├── tests/                   # Unit tests
├── sql/                     # SQL scripts
├── logs/                    # Log files (NOT in git)
├── cache/                   # Cached data (NOT in git)
└── data/                    # Exported data (NOT in git)
```

---

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'X'`
**Solution**: 
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: spaCy model not found
**Solution**:
```bash
python -m spacy download en_core_web_sm

# Verify download
python -c "import spacy; spacy.load('en_core_web_sm'); print('Model loaded!')"
```

### Issue: Supabase connection timeout
**Solution**:
- Check your internet connection
- Verify connection string in `.env`
- Make sure database password is URL-encoded (spaces = `%20`, @ = `%40`)
- Check Supabase project status in dashboard

### Issue: `could not translate host name "db.xxx.supabase.co" to address`
**Cause**: Your network cannot resolve the direct Supabase host (common in corporate/sandbox environments).

**Solution**: Use the **pooler** connection string instead:
1. Go to [Supabase Dashboard](https://supabase.com/dashboard) → your project
2. **Settings** → **Database** → **Connection string**
3. Under **Transaction pooler**, copy the **URI** (full connection string)
4. Add to `.env`:
   ```bash
   SUPABASE_DB_POOLER_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
   USE_POOLER_FOR_DNS_FIX=false
   ```
5. Restart your collection script.

### Issue: RapidAPI 401 Unauthorized
**Solution**:
- Verify `RAPIDAPI_KEY` in `.env`
- Check you're subscribed to the API (free tier)
- Make sure key doesn't have extra spaces

### Issue: Selenium ChromeDriver error
**Solution**:
```bash
# macOS
brew install --cask chromium

# Ubuntu/Debian
sudo apt-get install chromium-browser

# Or use webdriver-manager (already in requirements.txt)
python -c "from selenium import webdriver; from webdriver_manager.chrome import ChromeDriverManager; from selenium.webdriver.chrome.service import Service; driver = webdriver.Chrome(service=Service(ChromeDriverManager().install())); driver.quit(); print('ChromeDriver installed!')"
```

---

## Next Steps

After setup is complete:

1. **Read Documentation**: Review files in `docs/` folder
2. **Run Test Collection**: Collect 50 jobs in test mode
3. **Validate Data Quality**: Check database for inserted jobs
4. **Run Full Pipeline**: Collect 2,000+ jobs
5. **Launch Streamlit Dashboard**: `streamlit run streamlit_app.py` – Charts and AI natural language search (Ollama Cloud: set `OLLAMA_API_KEY` from ollama.com/settings/keys)
6. **Generate Insights**: Run `python run.py analyze` or use the Streamlit dashboard
7. **AI Search**: Set `OLLAMA_API_KEY` (ollama.com) for cloud, or `LLM_PROVIDER=openai` with `OPENAI_API_KEY`

---

## Getting Help

- **Documentation**: Check `docs/` folder for detailed guides
- **Issues**: File issues on GitHub (if using git)
- **Logs**: Check `logs/job_scraper.log` for error details

---

## Security Reminders

- ✓ `.env` is in `.gitignore` (never commit secrets)
- ✓ `docs/` and `.cursorrules` are in `.gitignore`
- ✓ Use strong database passwords
- ✓ Rotate API keys regularly
- ✓ Don't share API keys in screenshots or logs

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-20  
**Next Review**: 2026-03-20
