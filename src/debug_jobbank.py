"""
Debug Job Bank HTML structure to fix collector.

This script fetches a Job Bank search page and helps identify the correct CSS selectors.
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent
sys.path.insert(0, str(src_path))

import requests
from bs4 import BeautifulSoup

# Job Bank search URL (data analyst in Toronto)
SEARCH_URL = "https://www.jobbank.gc.ca/jobsearch/jobsearch?searchstring=data+analyst&locationstring=Toronto%2C+ON"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

def main():
    """Fetch Job Bank page and analyze structure."""
    print("="*80)
    print("Job Bank HTML Structure Debugger")
    print("="*80)
    print(f"\nFetching: {SEARCH_URL}\n")
    
    try:
        # Fetch page
        response = requests.get(SEARCH_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        html = response.text
        
        print(f"✅ Successfully fetched page ({len(html)} bytes)")
        print(f"Status code: {response.status_code}\n")
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Save HTML for inspection
        output_file = Path(__file__).parent.parent / "debug_jobbank.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print(f"✅ Saved HTML to: {output_file}\n")
        
        print("="*80)
        print("ANALYZING HTML STRUCTURE")
        print("="*80)
        
        # Look for common job listing patterns
        patterns_to_check = [
            ('article', None),
            ('article', {'class': 'resultJobItem'}),
            ('article', {'class': 'job'}),
            ('div', {'class': 'job'}),
            ('div', {'class': 'job-listing'}),
            ('div', {'class': 'result'}),
            ('li', {'class': 'job'}),
            ('div', {'id': re.compile(r'job')}),
        ]
        
        print("\n📋 SEARCHING FOR JOB LISTINGS:\n")
        
        for tag, attrs in patterns_to_check:
            if attrs is None:
                elements = soup.find_all(tag)
            else:
                elements = soup.find_all(tag, attrs)
            
            if elements:
                count = len(elements)
                print(f"✅ Found {count} <{tag}> elements with {attrs}")
                
                if count > 0 and count < 100:  # Reasonable number
                    # Show first element structure
                    first = elements[0]
                    print(f"\n   First element structure:")
                    print(f"   Tag: {first.name}")
                    print(f"   Classes: {first.get('class', [])}")
                    print(f"   ID: {first.get('id', 'None')}")
                    
                    # Look for title
                    title_candidates = [
                        first.find('h3'),
                        first.find('h2'),
                        first.find('h4'),
                        first.find('a', {'class': re.compile(r'title')}),
                        first.find('span', {'class': re.compile(r'title')}),
                    ]
                    
                    for candidate in title_candidates:
                        if candidate and candidate.get_text(strip=True):
                            print(f"\n   📌 TITLE FOUND: {candidate.name} - {candidate.get('class', [])}")
                            print(f"      Text: {candidate.get_text(strip=True)[:60]}...")
                            break
                    
                    # Look for company
                    company_candidates = [
                        first.find('span', {'class': re.compile(r'business|company|employer')}),
                        first.find('div', {'class': re.compile(r'business|company|employer')}),
                        first.find('p', {'class': re.compile(r'business|company|employer')}),
                    ]
                    
                    for candidate in company_candidates:
                        if candidate and candidate.get_text(strip=True):
                            print(f"\n   🏢 COMPANY FOUND: {candidate.name} - {candidate.get('class', [])}")
                            print(f"      Text: {candidate.get_text(strip=True)[:60]}...")
                            break
                    
                    # Look for location
                    location_candidates = [
                        first.find('span', {'class': re.compile(r'location')}),
                        first.find('div', {'class': re.compile(r'location')}),
                        first.find('p', {'class': re.compile(r'location')}),
                    ]
                    
                    for candidate in location_candidates:
                        if candidate and candidate.get_text(strip=True):
                            print(f"\n   📍 LOCATION FOUND: {candidate.name} - {candidate.get('class', [])}")
                            print(f"      Text: {candidate.get_text(strip=True)[:60]}...")
                            break
                    
                    print("\n" + "─"*80)
        
        # Check page title
        print(f"\n📄 Page Title: {soup.title.string if soup.title else 'No title'}")
        
        # Check for "no results" messages
        no_results = soup.find_all(text=re.compile(r'no (results|jobs|postings|listings) found', re.IGNORECASE))
        if no_results:
            print(f"\n⚠️  WARNING: Found 'no results' message:")
            for msg in no_results[:3]:
                print(f"   - {msg.strip()}")
        
        # Check for pagination
        pagination = soup.find('nav', {'class': re.compile(r'pagination')}) or soup.find('div', {'class': re.compile(r'pagination')})
        if pagination:
            print(f"\n📄 Pagination found: {pagination.name} - {pagination.get('class', [])}")
        
        print("\n" + "="*80)
        print("RECOMMENDED NEXT STEPS:")
        print("="*80)
        print("1. Open debug_jobbank.html in browser")
        print("2. Search for job title text to find correct elements")
        print("3. Update CSS selectors in jobbank_collector.py")
        print("4. Re-run test_collection.py")
        print("="*80)
        
    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    import re
    sys.exit(main())
