# 🇨🇦 Canada Tech Job Compass 2026

> **Comprehensive tech job market analysis across 7 Canadian cities** - Helping job seekers find their optimal career opportunities through data-driven insights.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## 📊 Project Overview

**Canada Tech Job Compass** analyzes **2,000+ live tech job postings** from the last 30 days across major Canadian cities to provide actionable insights for job seekers pursuing tech careers and PR pathways (SINP/OINP).

### 🎯 Target Insights

The system generates insights like:

- **"Saskatoon Data Analyst: 2.1y avg exp vs Toronto 4.3y - 65% junior roles"**
- **"DevOps: Docker+AWS required everywhere, Power BI > Tableau 3:1 in Prairies"**
- **"Vancouver +25% salary but +1.8y exp demand"**
- **"IT Support: 80% remote in Calgary/Winnipeg"**
- **"Easiest entry: Regina SK (42% junior roles across tech)"**

---

## 🚀 Features

### Data Collection
- ✅ Multi-source aggregation (Job Bank Canada, RapidAPI, RSS feeds)
- ✅ Intelligent web scraping with rate limiting and retry logic
- ✅ Automated deduplication and data validation
- ✅ 2,000+ jobs from 3+ sources

### Data Processing
- ✅ NLP-powered feature extraction (experience, skills, seniority)
- ✅ 500+ technical skills recognition
- ✅ Remote work detection (remote/hybrid/onsite)
- ✅ 15+ data quality validation rules

### Analysis & Insights
- ✅ Experience ladder by city and role
- ✅ Skills demand heatmap
- ✅ City competitiveness scoring
- ✅ Salary range analysis
- ✅ Entry-level job recommendations

### Visualization
- ✅ Power BI dashboard (5 interactive pages)
- ✅ Automated data export for BI tools
- ✅ Daily refresh pipeline

---

## 🛠 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Language** | Python 3.11+ | Core development |
| **Database** | PostgreSQL (Supabase) | Data storage |
| **Web Scraping** | BeautifulSoup, Selenium | Data collection |
| **NLP** | spaCy | Feature extraction |
| **Data Processing** | pandas, numpy | Data manipulation |
| **Visualization** | Power BI | Interactive dashboards |
| **Scheduling** | APScheduler, GitHub Actions | Automation |
| **Testing** | pytest | Quality assurance |

---

## 📁 Project Structure

```
JobMarket/
├── src/
│   ├── collectors/          # Data collection from APIs/web scraping
│   ├── processors/          # Validation, deduplication, feature extraction
│   ├── analyzers/           # SQL queries, insights generation
│   ├── database/            # ORM models, connection management
│   └── utils/               # Logging, config, retry logic
│
├── tests/                   # Unit and integration tests
├── sql/                     # Database schema and queries
│   ├── schema.sql          # Table definitions
│   ├── seed_data.sql       # Skills master data
│   └── analysis_queries.sql # Pre-built queries
│
├── docs/                    # Comprehensive documentation
│   ├── setup.md            # Setup instructions
│   ├── architecture.md     # System design
│   ├── api-integration.md  # API usage guide
│   ├── data-pipeline.md    # Pipeline documentation
│   └── analysis-queries.md # SQL query reference
│
├── .env.example            # Environment variables template
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

---

## 🚦 Quick Start

### Prerequisites
- Python 3.11+
- Git
- Chrome/Chromium (for Selenium)
- Supabase account (free tier)
- RapidAPI account (free tier)

### Installation (5 minutes)

```bash
# 1. Clone repository
git clone https://github.com/NevilPatel01/JobMarketResearch.git
cd JobMarketResearch

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# 4. Configure environment
cp .env.example .env
# Edit .env with your Supabase and RapidAPI credentials

# 5. Set up database
# Run sql/schema.sql in Supabase SQL Editor
# Run sql/seed_data.sql to populate skills

# 6. Test setup
python test_pipeline.py
```

**For detailed setup instructions**, see [`docs/setup.md`](docs/setup.md).

---

## 📖 Usage

### Collect Jobs (CLI)

```bash
# Collect jobs from all sources
python src/main.py collect --cities Toronto Saskatoon --roles "data analyst" devops

# Run full pipeline (collect + process + analyze)
python src/main.py full-pipeline --parallel

# Generate insights and export for Power BI
python src/main.py analyze
```

### Programmatic Usage

```python
from collectors.orchestrator import DataCollectionPipeline
from processors.validator import DataValidator
from analyzers.insights_generator import InsightsGenerator

# Collect jobs
collector = DataCollectionPipeline()
raw_jobs = collector.run(parallel=True)

# Validate data
validator = DataValidator()
valid_jobs, stats = validator.validate_batch(raw_jobs)

# Generate insights
analyzer = InsightsGenerator(db_url)
insights = analyzer.generate_all_insights()
```

---

## 📊 Data Pipeline

```
STAGE 1: COLLECTION (30-60 min)
  ↓ Job Bank + RapidAPI + RSS → 2,000+ jobs

STAGE 2: VALIDATION (5-10 min)
  ↓ 15+ quality checks → 90%+ valid data

STAGE 3: DEDUPLICATION (2-5 min)
  ↓ Hash-based matching → Unique jobs

STAGE 4: FEATURE EXTRACTION (10-20 min)
  ↓ NLP + Regex → Experience, Skills, Remote

STAGE 5: STORAGE (2-5 min)
  ↓ Bulk insert → PostgreSQL

STAGE 6: ANALYSIS (3-5 min)
  ↓ SQL queries → Insights + Power BI refresh
```

**Total Runtime**: ~60 minutes for full pipeline

---

## 🎨 Power BI Dashboard

The project exports data for a 5-page interactive dashboard:

1. **Canada Heatmap**: Geographic job distribution
2. **Experience Ladder**: Career progression paths by city/role
3. **Skills Radar**: In-demand technical skills heatmap
4. **Location Strategy**: Remote work availability, opportunity scores
5. **Action Plan**: Personalized job recommendations

**Connect Power BI**:
1. Open Power BI Desktop
2. Get Data → PostgreSQL database
3. Enter Supabase connection string (from .env)
4. Select tables: `vw_jobs_full` or `mv_powerbi_export`
5. Build visualizations using provided specs
6. Set up scheduled refresh

---

## 🔍 Key Analyses

### Experience Requirements
```sql
SELECT city, title as role, 
       AVG(exp_min) as avg_exp, 
       COUNT(*) * AVG(is_junior::int) as junior_jobs
FROM jobs_raw jr
JOIN jobs_features jf ON jr.job_id = jf.job_id
GROUP BY city, title
ORDER BY junior_jobs DESC;
```

### Skills Demand
```sql
SELECT skill, COUNT(*) as demand
FROM jobs_features
CROSS JOIN jsonb_array_elements_text(skills) as skill
GROUP BY skill
ORDER BY demand DESC
LIMIT 20;
```

### City Opportunity Score
```sql
-- Composite metric: junior %, remote %, volume, low exp, good salary
SELECT city, 
       ROUND((junior_ratio * 0.3 + remote_ratio * 0.25 + ...) * 100, 1) as score
FROM city_metrics
ORDER BY score DESC;
```

**Full query library**: See [`docs/analysis-queries.md`](docs/analysis-queries.md)

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_collectors.py

# Run with verbose output
pytest -v
```

**Coverage target**: 85%+ overall, 90%+ for collectors

---

## 🗂 Data Sources

| Source | Type | Volume | Rate Limit |
|--------|------|--------|-----------|
| **Job Bank Canada** | Web Scraping | 60% (1,200+ jobs) | 2.5s/request |
| **RapidAPI (Mantiks)** | REST API | 20% (400+ jobs) | 500/month |
| **Workopolis RSS** | RSS Feed | 10% (200+ jobs) | Unlimited |
| **Indeed RSS** | RSS Feed | 10% (200+ jobs) | Unlimited |

**Total**: 2,000+ jobs from 3+ sources (last 30 days)

---

## 📅 Automation

### Daily Scheduled Pipeline

```yaml
# GitHub Actions (.github/workflows/daily_scrape.yml)
name: Daily Job Scraper
on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC daily

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - run: python src/main.py full-pipeline
      - run: python src/main.py analyze
```

### Local Scheduling

```python
# Use APScheduler
from apscheduler.schedulers.blocking import BlockingScheduler

scheduler = BlockingScheduler()

@scheduler.scheduled_job('cron', hour=2, minute=0)
def daily_scrape():
    run_full_pipeline()

scheduler.start()
```

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Follow code style: Run `black src/ && isort src/`
4. Add tests: Coverage must remain >85%
5. Commit: `git commit -m 'feat: add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open Pull Request

**Code Style**: We use Black (line length 100), isort, and type hints.

---

## 📝 Documentation

Comprehensive guides available in [`docs/`](docs/):

- [`setup.md`](docs/setup.md) - Detailed setup instructions
- [`architecture.md`](docs/architecture.md) - System design and components
- [`api-integration.md`](docs/api-integration.md) - API usage and scraping
- [`data-pipeline.md`](docs/data-pipeline.md) - Pipeline stages explained
- [`analysis-queries.md`](docs/analysis-queries.md) - SQL query reference

---

## 🔒 Security

- ✅ All secrets in `.env` (never committed)
- ✅ API keys stored in environment variables
- ✅ Rate limiting on all external requests
- ✅ Personal data stripped from job descriptions
- ✅ Supabase Row Level Security (RLS) enabled

**Report security issues**: Please email security@example.com

---

## 📊 Success Metrics

Current status:

- ✅ 2,000+ jobs collected from 3+ sources
- ✅ 90%+ data validation rate
- ✅ 85%+ skills extraction accuracy
- ✅ All 7 cities & 7 roles represented
- ✅ 5-page Power BI dashboard
- ✅ End-to-end refresh <60 mins
- ✅ 5+ actionable insights generated

---

## 🚧 Roadmap

### Phase 1 (Current - MVP)
- [x] Multi-source data collection
- [x] Feature extraction (exp, skills, remote)
- [x] Basic analysis queries
- [x] Power BI export

### Phase 2 (Next 3 months)
- [ ] ML salary predictor (XGBoost)
- [ ] Real-time job alerts
- [ ] LinkedIn integration
- [ ] Mobile-responsive dashboard

### Phase 3 (6-12 months)
- [ ] AI cover letter generator
- [ ] Interview prep resources
- [ ] Career path predictor
- [ ] Company culture analysis

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Job Bank Canada** for providing public job data
- **RapidAPI** for API marketplace
- **Supabase** for free PostgreSQL hosting
- **spaCy** for NLP capabilities
- **Open source community** for amazing tools

---

## 📧 Contact

**Project Maintainer**: Axis Patel  
**Email**: contact@example.com  
**GitHub**: [@NevilPatel01](https://github.com/NevilPatel01)  
**Project Link**: [https://github.com/NevilPatel01/JobMarketResearch](https://github.com/NevilPatel01/JobMarketResearch)

---

## 💡 For Job Seekers

This project is built **by job seekers, for job seekers**. Our mission is to democratize access to job market insights and help you make informed career decisions.

**Using this project?** Share your success story! We'd love to hear how the data helped you land your dream job.

---

<div align="center">

**Made with ❤️ for the Canadian tech community**

[⭐ Star this repo](https://github.com/NevilPatel01/JobMarketResearch) • [🐛 Report Bug](https://github.com/NevilPatel01/JobMarketResearch/issues) • [💡 Request Feature](https://github.com/NevilPatel01/JobMarketResearch/issues)

</div>
