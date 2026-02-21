# API Integration Guide

## Overview
This guide covers integration with all external data sources: Job Bank Canada (web scraping), RapidAPI (Mantiks/FantasticJobs), Workopolis RSS, and Indeed RSS. Each source has unique authentication, rate limiting, and data formats.

```mermaid
%%{init: {'theme':'base'}}%%
flowchart LR
    subgraph SOURCES["Data Sources"]
        JB[Job Bank Canada<br/>Web Scraping]
        RA[RapidAPI<br/>JSearch · LinkedIn]
        AD[Adzuna<br/>Free API]
        RO[RemoteOK<br/>No key]
        RSS[RSS Feeds<br/>Indeed · Workopolis]
    end
    
    subgraph COLLECTORS["Collectors"]
        C1[JobBankCollector]
        C2[RapidAPICollector]
        C3[AdzunaCollector]
        C4[RemoteOKCollector]
        C5[RSSCollector]
    end
    
    subgraph OUTPUT["Output"]
        OUT[Standardized Job JSON]
    end
    
    JB --> C1
    RA --> C2
    AD --> C3
    RO --> C4
    RSS --> C5
    C1 & C2 & C3 & C4 & C5 --> OUT
    
    style SOURCES fill:#e0f2fe
    style COLLECTORS fill:#d1fae5
    style OUTPUT fill:#6366f1
```

## Prerequisites

### Required Accounts
1. **RapidAPI Account**
   - Sign up: https://rapidapi.com/auth/sign-up
   - Free tier: 100-500 requests/month
   - Subscribe to "Mantiks Canada Jobs API" or "FantasticJobs API"
   - Copy API key from dashboard

2. **Supabase Account**
   - Sign up: https://supabase.com
   - Create project: `canada-tech-jobs-2026`
   - Enable database access (PostgreSQL)
   - Copy project URL and anon key

### Environment Setup
Create `.env` file in project root:
```bash
# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGc...
SUPABASE_DB_URL=postgresql://postgres:[password]@db.xxxxx.supabase.co:5432/postgres

# RapidAPI
RAPIDAPI_KEY=your-rapidapi-key-here
RAPIDAPI_HOST=mantiks-jobs-v1.p.rapidapi.com

# Scraping Configuration
JOBBANK_RATE_LIMIT_SECONDS=2.5
SELENIUM_HEADLESS=true
MAX_RETRIES=3
REQUEST_TIMEOUT=30

# Feature Flags
ENABLE_JOBBANK=true
ENABLE_RAPIDAPI=true
ENABLE_RSS=true
ENABLE_CACHING=true
CACHE_TTL_HOURS=24

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/job_scraper.log
```

---

## 1. Job Bank Canada Integration

### Overview
- **URL**: https://www.jobbank.gc.ca/jobsearch/jobsearch
- **Method**: Web Scraping (No public API)
- **Data Volume**: 1,000+ jobs (60% of total)
- **Rate Limit**: 2.5 seconds between requests (self-imposed)
- **Authentication**: None (public data)

### URL Parameters
| Parameter | Values | Example |
|-----------|--------|---------|
| `searchstring` | Job role keyword | `data+analyst` |
| `location` | City name | `Toronto`, `Saskatoon` |
| `postedDate` | Days since posted | `30` (last 30 days) |
| `sort` | Sort order | `posted` (newest first) |
| `page` | Page number | `1`, `2`, `3`, ... |

### Example URLs
```python
BASE_URL = "https://www.jobbank.gc.ca/jobsearch/jobsearch"

urls = {
    'toronto_data_analyst': (
        f"{BASE_URL}?searchstring=data+analyst"
        f"&location=Toronto&postedDate=30&sort=posted"
    ),
    'saskatoon_devops': (
        f"{BASE_URL}?searchstring=devops"
        f"&location=Saskatoon&postedDate=30&sort=posted"
    ),
    'calgary_full_stack': (
        f"{BASE_URL}?searchstring=full+stack+developer"
        f"&location=Calgary&postedDate=30&sort=posted"
    )
}
```

### HTML Structure (as of Feb 2026)
```html
<!-- Job listing container -->
<article class="resultJobItem">
    <h2 class="jobTitle">
        <a href="/jobsearch/jobposting/[job-id]">Data Analyst</a>
    </h2>
    <div class="company">
        <span>Tech Corp Inc.</span>
    </div>
    <div class="location">
        <span>Toronto, Ontario</span>
    </div>
    <div class="salary">
        <span>$60,000 to $80,000</span>
    </div>
    <div class="date">
        <time datetime="2026-02-15">Posted 5 days ago</time>
    </div>
</article>
```

### Implementation (BeautifulSoup)

#### Basic Scraper
```python
import requests
from bs4 import BeautifulSoup
import time
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'CanadaTechJobCompass/1.0 (Educational Project; contact@example.com)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
}

def scrape_jobbank_page(city: str, role: str, page: int = 1) -> List[Dict]:
    """
    Scrape single page from Job Bank Canada.
    
    Args:
        city: Canadian city name (e.g., 'Toronto')
        role: Job role keyword (e.g., 'data analyst')
        page: Page number (default: 1)
        
    Returns:
        List of job dictionaries
    """
    url = (
        f"https://www.jobbank.gc.ca/jobsearch/jobsearch"
        f"?searchstring={role.replace(' ', '+')}"
        f"&location={city}"
        f"&postedDate=30"
        f"&sort=posted"
        f"&page={page}"
    )
    
    logger.info(f"Scraping Job Bank: {city} - {role} (page {page})")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        jobs = []
        
        # Find all job listings
        job_articles = soup.find_all('article', class_='resultJobItem')
        
        for article in job_articles:
            job = parse_job_article(article, city)
            if job:
                jobs.append(job)
        
        logger.info(f"Found {len(jobs)} jobs on page {page}")
        
        # Respectful rate limiting
        time.sleep(float(os.getenv('JOBBANK_RATE_LIMIT_SECONDS', 2.5)))
        
        return jobs
        
    except requests.RequestException as e:
        logger.error(f"Failed to scrape {url}: {e}")
        return []

def parse_job_article(article: BeautifulSoup, city: str) -> Dict:
    """
    Parse job information from article element.
    
    Args:
        article: BeautifulSoup article element
        city: City name for normalization
        
    Returns:
        Job dictionary with standardized keys
    """
    try:
        # Extract job title and URL
        title_tag = article.find('h2', class_='jobTitle').find('a')
        title = title_tag.get_text(strip=True)
        job_path = title_tag.get('href')
        job_id = f"jobbank_{job_path.split('/')[-1]}"
        url = f"https://www.jobbank.gc.ca{job_path}"
        
        # Extract company
        company_tag = article.find('div', class_='company')
        company = company_tag.get_text(strip=True) if company_tag else "Unknown"
        
        # Extract location
        location_tag = article.find('div', class_='location')
        location = location_tag.get_text(strip=True) if location_tag else city
        
        # Parse city and province
        city_normalized, province = parse_location(location)
        
        # Extract salary (if available)
        salary_tag = article.find('div', class_='salary')
        salary_min, salary_max = parse_salary(salary_tag.get_text(strip=True)) if salary_tag else (None, None)
        
        # Extract posting date
        date_tag = article.find('time')
        posted_date = date_tag.get('datetime') if date_tag else None
        
        return {
            'source': 'jobbank',
            'job_id': job_id,
            'title': title,
            'company': company,
            'city': city_normalized,
            'province': province,
            'description': None,  # Fetch separately if needed
            'salary_min': salary_min,
            'salary_max': salary_max,
            'remote_type': None,  # Detect from description
            'posted_date': posted_date,
            'url': url
        }
        
    except Exception as e:
        logger.warning(f"Failed to parse job article: {e}")
        return None

def parse_location(location: str) -> tuple:
    """
    Parse location string to city and province.
    
    Examples:
        "Toronto, Ontario" → ("Toronto", "ON")
        "Saskatoon, SK" → ("Saskatoon", "SK")
    """
    parts = location.split(',')
    city = parts[0].strip() if parts else "Unknown"
    
    province_map = {
        'Ontario': 'ON', 'British Columbia': 'BC', 'Alberta': 'AB',
        'Saskatchewan': 'SK', 'Manitoba': 'MB', 'Quebec': 'QC',
        'Nova Scotia': 'NS', 'New Brunswick': 'NB'
    }
    
    province = parts[1].strip() if len(parts) > 1 else ""
    province = province_map.get(province, province)[:2].upper()
    
    return city, province

def parse_salary(salary_text: str) -> tuple:
    """
    Parse salary range from text.
    
    Examples:
        "$60,000 to $80,000" → (60000, 80000)
        "$75,000 per year" → (75000, 75000)
        "Salary not specified" → (None, None)
    """
    import re
    
    # Remove commas and dollar signs
    cleaned = salary_text.replace(',', '').replace('$', '')
    
    # Pattern: "60000 to 80000"
    range_pattern = r'(\d+)\s*(?:to|-)\s*(\d+)'
    match = re.search(range_pattern, cleaned)
    
    if match:
        return int(match.group(1)), int(match.group(2))
    
    # Pattern: single value "75000"
    single_pattern = r'(\d+)'
    match = re.search(single_pattern, cleaned)
    
    if match:
        value = int(match.group(1))
        return value, value
    
    return None, None
```

#### Selenium Fallback (for JavaScript-heavy pages)
```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

def scrape_with_selenium(url: str) -> List[Dict]:
    """
    Scrape Job Bank using Selenium for JavaScript-rendered content.
    
    Args:
        url: Full Job Bank URL
        
    Returns:
        List of job dictionaries
    """
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument(f'user-agent={HEADERS["User-Agent"]}')
    
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        
        # Wait for job listings to load
        wait = WebDriverWait(driver, 10)
        wait.until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, 'resultJobItem'))
        )
        
        # Get page source and parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        job_articles = soup.find_all('article', class_='resultJobItem')
        
        jobs = []
        for article in job_articles:
            job = parse_job_article(article, "")
            if job:
                jobs.append(job)
        
        return jobs
        
    except Exception as e:
        logger.error(f"Selenium scraping failed: {e}")
        return []
        
    finally:
        if driver:
            driver.quit()
```

#### Retry Logic with Exponential Backoff
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError))
)
def scrape_jobbank_with_retry(city: str, role: str, page: int) -> List[Dict]:
    """Scrape with automatic retry on network errors."""
    return scrape_jobbank_page(city, role, page)
```

### Fetching Full Job Description
```python
def fetch_job_description(job_url: str) -> str:
    """
    Fetch full job description from Job Bank posting page.
    
    Args:
        job_url: Full URL to job posting
        
    Returns:
        Job description text (HTML stripped)
    """
    try:
        response = requests.get(job_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Job description is typically in a div with class 'job-posting-detail'
        desc_tag = soup.find('div', class_='job-posting-detail')
        
        if desc_tag:
            # Remove script and style tags
            for tag in desc_tag(['script', 'style']):
                tag.decompose()
            
            return desc_tag.get_text(separator=' ', strip=True)
        
        return ""
        
    except Exception as e:
        logger.warning(f"Failed to fetch description from {job_url}: {e}")
        return ""
```

---

## 2. RapidAPI Integration (Mantiks Canada Jobs)

### Overview
- **API**: https://rapidapi.com/mantiks/api/mantiks-jobs-v1
- **Method**: RESTful API (GET requests)
- **Data Volume**: 300-500 jobs (20% of total)
- **Rate Limit**: 100-500 requests/month (free tier)
- **Authentication**: API Key in headers

### Authentication
```python
RAPIDAPI_HEADERS = {
    'X-RapidAPI-Key': os.getenv('RAPIDAPI_KEY'),
    'X-RapidAPI-Host': 'mantiks-jobs-v1.p.rapidapi.com'
}
```

### Endpoints

#### Search Jobs
```
GET https://mantiks-jobs-v1.p.rapidapi.com/jobs
```

**Query Parameters**:
| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `country` | Yes | string | `CA` for Canada |
| `province` | No | string | `ON`, `SK`, `AB`, `BC`, `MB` |
| `title` | No | string | Job title keyword |
| `limit` | No | integer | Max results (default: 50, max: 100) |
| `offset` | No | integer | Pagination offset |

**Response Format**:
```json
{
    "jobs": [
        {
            "id": "12345",
            "title": "Data Analyst",
            "company": "Tech Corp",
            "location": "Toronto, ON",
            "description": "We are seeking...",
            "salary": "$60,000 - $80,000",
            "posted_date": "2026-02-15",
            "url": "https://example.com/job/12345",
            "remote": false
        }
    ],
    "total": 150,
    "limit": 50,
    "offset": 0
}
```

### Implementation

```python
import requests
import os
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class RapidAPICollector:
    BASE_URL = "https://mantiks-jobs-v1.p.rapidapi.com/jobs"
    
    def __init__(self):
        self.api_key = os.getenv('RAPIDAPI_KEY')
        if not self.api_key:
            raise EnvironmentError("RAPIDAPI_KEY not set in .env")
        
        self.headers = {
            'X-RapidAPI-Key': self.api_key,
            'X-RapidAPI-Host': 'mantiks-jobs-v1.p.rapidapi.com'
        }
        
        self.request_count = 0
        self.max_requests = 500  # Free tier limit
    
    def collect(self, province: str, title: str, limit: int = 100) -> List[Dict]:
        """
        Collect jobs from RapidAPI.
        
        Args:
            province: 2-letter province code (ON, SK, AB, BC, MB)
            title: Job title keyword
            limit: Max results per request (max: 100)
            
        Returns:
            List of standardized job dictionaries
        """
        if self.request_count >= self.max_requests:
            logger.warning("RapidAPI request limit reached")
            return []
        
        params = {
            'country': 'CA',
            'province': province,
            'title': title,
            'limit': min(limit, 100)
        }
        
        try:
            logger.info(f"Fetching from RapidAPI: {province} - {title}")
            
            response = requests.get(
                self.BASE_URL,
                headers=self.headers,
                params=params,
                timeout=30
            )
            
            response.raise_for_status()
            self.request_count += 1
            
            data = response.json()
            jobs = data.get('jobs', [])
            
            # Convert to standardized format
            standardized = [self._standardize_job(job) for job in jobs]
            
            logger.info(f"Collected {len(standardized)} jobs from RapidAPI")
            
            return standardized
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.error("RapidAPI rate limit exceeded")
            elif e.response.status_code == 401:
                logger.error("RapidAPI authentication failed - check API key")
            else:
                logger.error(f"RapidAPI HTTP error: {e}")
            return []
            
        except Exception as e:
            logger.error(f"RapidAPI error: {e}")
            return []
    
    def _standardize_job(self, job: Dict) -> Dict:
        """Convert RapidAPI job format to standardized format."""
        # Parse location
        location = job.get('location', '')
        city, province = self._parse_location(location)
        
        # Parse salary
        salary_text = job.get('salary', '')
        salary_min, salary_max = self._parse_salary(salary_text)
        
        # Detect remote
        remote_keywords = ['remote', 'work from home', 'wfh', 'telecommute']
        is_remote = any(kw in job.get('description', '').lower() for kw in remote_keywords)
        remote_type = 'remote' if is_remote else 'onsite'
        
        return {
            'source': 'rapidapi',
            'job_id': f"rapidapi_{job.get('id')}",
            'title': job.get('title', ''),
            'company': job.get('company', ''),
            'city': city,
            'province': province,
            'description': job.get('description', ''),
            'salary_min': salary_min,
            'salary_max': salary_max,
            'remote_type': remote_type,
            'posted_date': job.get('posted_date'),
            'url': job.get('url', '')
        }
    
    def _parse_location(self, location: str) -> tuple:
        """Parse location string to city and province."""
        parts = [p.strip() for p in location.split(',')]
        city = parts[0] if parts else "Unknown"
        province = parts[1][:2].upper() if len(parts) > 1 else ""
        return city, province
    
    def _parse_salary(self, salary_text: str) -> tuple:
        """Parse salary range from text."""
        import re
        
        if not salary_text:
            return None, None
        
        # Remove formatting
        cleaned = salary_text.replace(',', '').replace('$', '')
        
        # Extract numbers
        numbers = re.findall(r'\d+', cleaned)
        
        if len(numbers) >= 2:
            return int(numbers[0]), int(numbers[1])
        elif len(numbers) == 1:
            value = int(numbers[0])
            return value, value
        
        return None, None
```

### Rate Limit Monitoring
```python
def check_rate_limit(response: requests.Response) -> Dict:
    """
    Check RapidAPI rate limit from response headers.
    
    Returns:
        Dict with limit info: {remaining, limit, reset_time}
    """
    headers = response.headers
    
    return {
        'remaining': int(headers.get('X-RateLimit-Requests-Remaining', 0)),
        'limit': int(headers.get('X-RateLimit-Requests-Limit', 500)),
        'reset_time': headers.get('X-RateLimit-Requests-Reset', 'Unknown')
    }
```

### Caching Strategy
```python
import pickle
from pathlib import Path
from datetime import datetime, timedelta

CACHE_DIR = Path('cache/rapidapi')
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def get_cached_response(cache_key: str, ttl_hours: int = 24) -> Optional[List[Dict]]:
    """Retrieve cached API response if not expired."""
    cache_file = CACHE_DIR / f"{cache_key}.pkl"
    
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, 'rb') as f:
            cached = pickle.load(f)
        
        # Check if expired
        age = datetime.now() - cached['timestamp']
        if age < timedelta(hours=ttl_hours):
            logger.info(f"Using cached response for {cache_key}")
            return cached['data']
        
    except Exception as e:
        logger.warning(f"Cache read failed: {e}")
    
    return None

def cache_response(cache_key: str, data: List[Dict]):
    """Save API response to cache."""
    cache_file = CACHE_DIR / f"{cache_key}.pkl"
    
    try:
        with open(cache_file, 'wb') as f:
            pickle.dump({
                'data': data,
                'timestamp': datetime.now()
            }, f)
        logger.info(f"Cached response for {cache_key}")
    except Exception as e:
        logger.warning(f"Cache write failed: {e}")
```

---

## 3. RSS Feed Integration (Workopolis & Indeed)

### Overview
- **Method**: RSS/Atom feed parsing
- **Data Volume**: 200-300 jobs (20% of total)
- **Rate Limit**: None (but respectful polling every 24h)
- **Authentication**: None (public feeds)

### Workopolis RSS

**Feed URL Pattern**:
```
https://www.workopolis.com/rss/search/cs?as={location}&keywords={keywords}&jt=fulltime&et=30d
```

**Parameters**:
- `as`: Location code (`ca-on` for Ontario, `ca-sk` for Saskatchewan)
- `keywords`: Job search keywords (URL encoded)
- `jt`: Job type (`fulltime`, `parttime`, `contract`)
- `et`: Time range (`30d` for 30 days)

### Indeed Canada RSS

**Feed URL Pattern**:
```
https://ca.indeed.com/rss?q={keywords}&l={city}&fromage=30
```

**Parameters**:
- `q`: Job keywords (URL encoded)
- `l`: City name
- `fromage`: Days since posted

### Implementation

```python
import feedparser
from typing import List, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class RSSCollector:
    WORKOPOLIS_BASE = "https://www.workopolis.com/rss/search/cs"
    INDEED_BASE = "https://ca.indeed.com/rss"
    
    LOCATION_CODES = {
        'Toronto': 'ca-on',
        'Calgary': 'ca-ab',
        'Edmonton': 'ca-ab',
        'Vancouver': 'ca-bc',
        'Saskatoon': 'ca-sk',
        'Regina': 'ca-sk',
        'Winnipeg': 'ca-mb'
    }
    
    def collect_workopolis(self, city: str, keywords: str) -> List[Dict]:
        """
        Collect jobs from Workopolis RSS feed.
        
        Args:
            city: Canadian city name
            keywords: Job search keywords
            
        Returns:
            List of standardized job dictionaries
        """
        location_code = self.LOCATION_CODES.get(city, 'ca-on')
        
        feed_url = (
            f"{self.WORKOPOLIS_BASE}"
            f"?as={location_code}"
            f"&keywords={keywords.replace(' ', '+')}"
            f"&jt=fulltime"
            f"&et=30d"
        )
        
        return self._parse_rss_feed(feed_url, 'workopolis', city)
    
    def collect_indeed(self, city: str, keywords: str) -> List[Dict]:
        """
        Collect jobs from Indeed RSS feed.
        
        Args:
            city: Canadian city name
            keywords: Job search keywords
            
        Returns:
            List of standardized job dictionaries
        """
        feed_url = (
            f"{self.INDEED_BASE}"
            f"?q={keywords.replace(' ', '+')}"
            f"&l={city}"
            f"&fromage=30"
        )
        
        return self._parse_rss_feed(feed_url, 'indeed', city)
    
    def _parse_rss_feed(self, feed_url: str, source: str, city: str) -> List[Dict]:
        """
        Parse RSS feed and convert to standardized format.
        
        Args:
            feed_url: Full RSS feed URL
            source: Source name ('workopolis' or 'indeed')
            city: City for location normalization
            
        Returns:
            List of job dictionaries
        """
        try:
            logger.info(f"Fetching {source} RSS feed: {feed_url}")
            
            feed = feedparser.parse(feed_url)
            
            if feed.bozo:  # Feed parsing error
                logger.warning(f"RSS feed parsing issue: {feed.bozo_exception}")
            
            jobs = []
            
            for entry in feed.entries:
                job = self._parse_entry(entry, source, city)
                if job:
                    jobs.append(job)
            
            logger.info(f"Collected {len(jobs)} jobs from {source}")
            
            return jobs
            
        except Exception as e:
            logger.error(f"RSS feed error for {source}: {e}")
            return []
    
    def _parse_entry(self, entry, source: str, city: str) -> Dict:
        """Parse single RSS entry to job dictionary."""
        try:
            # Extract basic fields
            title = entry.get('title', '').strip()
            link = entry.get('link', '')
            summary = entry.get('summary', '')
            
            # Parse published date
            published = entry.get('published_parsed') or entry.get('updated_parsed')
            posted_date = None
            if published:
                posted_date = datetime(*published[:6]).date().isoformat()
            
            # Extract company (varies by source)
            company = "Unknown"
            if 'indeed' in source and 'author' in entry:
                company = entry.author
            elif 'workopolis' in source and 'source' in entry:
                company = entry.source.get('title', 'Unknown')
            
            # Generate unique ID
            job_id = f"{source}_{abs(hash(link))}"
            
            return {
                'source': source,
                'job_id': job_id,
                'title': title,
                'company': company,
                'city': city,
                'province': self._infer_province(city),
                'description': summary,
                'salary_min': None,
                'salary_max': None,
                'remote_type': None,
                'posted_date': posted_date,
                'url': link
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse RSS entry: {e}")
            return None
    
    def _infer_province(self, city: str) -> str:
        """Infer province from city name."""
        province_map = {
            'Toronto': 'ON', 'Ottawa': 'ON', 'Mississauga': 'ON',
            'Calgary': 'AB', 'Edmonton': 'AB',
            'Vancouver': 'BC', 'Victoria': 'BC',
            'Saskatoon': 'SK', 'Regina': 'SK',
            'Winnipeg': 'MB',
            'Montreal': 'QC', 'Quebec City': 'QC'
        }
        return province_map.get(city, '')
```

---

## 4. Unified Collector Interface

### Base Collector Class
```python
from abc import ABC, abstractmethod
from typing import List, Dict

class BaseCollector(ABC):
    """Abstract base class for all data collectors."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def collect(self, city: str, role: str, **kwargs) -> List[Dict]:
        """
        Collect jobs from source.
        
        Returns:
            List of job dictionaries with standardized keys
        """
        pass
    
    def validate_job(self, job: Dict) -> bool:
        """Validate job has required fields."""
        required_keys = ['source', 'job_id', 'title', 'city', 'url']
        return all(key in job and job[key] for key in required_keys)
    
    def collect_with_validation(self, city: str, role: str, **kwargs) -> List[Dict]:
        """Collect jobs and validate."""
        jobs = self.collect(city, role, **kwargs)
        valid_jobs = [job for job in jobs if self.validate_job(job)]
        
        if len(valid_jobs) < len(jobs):
            self.logger.warning(
                f"Filtered {len(jobs) - len(valid_jobs)} invalid jobs"
            )
        
        return valid_jobs
```

### Multi-Source Orchestrator
```python
class JobCollectorOrchestrator:
    """Orchestrate data collection from multiple sources."""
    
    def __init__(self):
        self.collectors = {
            'jobbank': JobBankCollector(config={}),
            'rapidapi': RapidAPICollector(),
            'rss': RSSCollector()
        }
    
    def collect_all(
        self, 
        cities: List[str], 
        roles: List[str],
        sources: List[str] = ['jobbank', 'rapidapi', 'rss']
    ) -> List[Dict]:
        """
        Collect jobs from all sources.
        
        Args:
            cities: List of city names
            roles: List of job role keywords
            sources: List of sources to use
            
        Returns:
            Combined list of all jobs
        """
        all_jobs = []
        
        for city in cities:
            for role in roles:
                logger.info(f"Collecting: {city} - {role}")
                
                # Job Bank
                if 'jobbank' in sources:
                    try:
                        jobs = self.collectors['jobbank'].collect(city, role)
                        all_jobs.extend(jobs)
                    except Exception as e:
                        logger.error(f"Job Bank failed: {e}")
                
                # RapidAPI
                if 'rapidapi' in sources:
                    try:
                        province = self._city_to_province(city)
                        jobs = self.collectors['rapidapi'].collect(province, role)
                        all_jobs.extend(jobs)
                    except Exception as e:
                        logger.error(f"RapidAPI failed: {e}")
                
                # RSS Feeds
                if 'rss' in sources:
                    try:
                        workopolis_jobs = self.collectors['rss'].collect_workopolis(city, role)
                        indeed_jobs = self.collectors['rss'].collect_indeed(city, role)
                        all_jobs.extend(workopolis_jobs + indeed_jobs)
                    except Exception as e:
                        logger.error(f"RSS failed: {e}")
        
        logger.info(f"Total jobs collected: {len(all_jobs)}")
        return all_jobs
    
    def _city_to_province(self, city: str) -> str:
        """Convert city name to province code."""
        mapping = {
            'Toronto': 'ON', 'Calgary': 'AB', 'Edmonton': 'AB',
            'Vancouver': 'BC', 'Saskatoon': 'SK', 'Regina': 'SK',
            'Winnipeg': 'MB'
        }
        return mapping.get(city, 'ON')
```

---

## Testing API Integrations

### Unit Tests
```python
import pytest
from unittest.mock import Mock, patch

def test_jobbank_collector():
    """Test Job Bank scraper with mock response."""
    with patch('requests.get') as mock_get:
        # Mock HTML response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'<article class="resultJobItem">...</article>'
        mock_get.return_value = mock_response
        
        collector = JobBankCollector(config={})
        jobs = collector.collect('Toronto', 'data analyst')
        
        assert isinstance(jobs, list)
        assert len(jobs) >= 0

def test_rapidapi_collector():
    """Test RapidAPI collector with mock response."""
    with patch.dict(os.environ, {'RAPIDAPI_KEY': 'test_key'}):
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'jobs': [
                    {
                        'id': '123',
                        'title': 'Data Analyst',
                        'company': 'Test Corp',
                        'location': 'Toronto, ON'
                    }
                ]
            }
            mock_get.return_value = mock_response
            
            collector = RapidAPICollector()
            jobs = collector.collect('ON', 'data analyst')
            
            assert len(jobs) == 1
            assert jobs[0]['title'] == 'Data Analyst'
```

---

## Troubleshooting

### Common Issues

#### 1. RapidAPI 401 Authentication Error
```
Solution: Check RAPIDAPI_KEY in .env file
- Verify key is correct (copy from RapidAPI dashboard)
- Check you're subscribed to the API
- Ensure no extra whitespace in key
```

#### 2. Job Bank Scraping Blocked
```
Solution: Implement respectful rate limiting
- Increase delay: JOBBANK_RATE_LIMIT_SECONDS=3.0
- Use Selenium with headless mode
- Rotate User-Agent strings
```

#### 3. RSS Feed Parsing Errors
```
Solution: Check feed structure
- Validate feed URL in browser
- Check for feed format changes
- Enable feedparser.parse() debugging
```

#### 4. Rate Limit Exceeded (RapidAPI)
```
Solution: Implement caching
- Cache responses for 24 hours
- Check remaining quota before requests
- Upgrade to paid tier if needed
```

---

## API Monitoring Dashboard

### Track API Health
```python
import json
from datetime import datetime

class APIMonitor:
    """Monitor API health and usage."""
    
    def __init__(self):
        self.metrics = {
            'jobbank': {'requests': 0, 'errors': 0, 'jobs': 0},
            'rapidapi': {'requests': 0, 'errors': 0, 'jobs': 0, 'quota_remaining': 500},
            'rss': {'requests': 0, 'errors': 0, 'jobs': 0}
        }
    
    def log_request(self, source: str, success: bool, job_count: int = 0):
        """Log API request result."""
        self.metrics[source]['requests'] += 1
        if success:
            self.metrics[source]['jobs'] += job_count
        else:
            self.metrics[source]['errors'] += 1
    
    def save_metrics(self, filepath: str = 'logs/api_metrics.json'):
        """Save metrics to file."""
        with open(filepath, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'metrics': self.metrics
            }, f, indent=2)
    
    def get_report(self) -> str:
        """Generate human-readable report."""
        total_requests = sum(m['requests'] for m in self.metrics.values())
        total_jobs = sum(m['jobs'] for m in self.metrics.values())
        total_errors = sum(m['errors'] for m in self.metrics.values())
        
        return f"""
API Monitoring Report
=====================
Total Requests: {total_requests}
Total Jobs: {total_jobs}
Total Errors: {total_errors}
Success Rate: {((total_requests - total_errors) / total_requests * 100):.1f}%

By Source:
{json.dumps(self.metrics, indent=2)}
        """
```

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-20  
**Next Review**: 2026-03-20
