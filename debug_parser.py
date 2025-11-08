"""
Debug script to test SPBE parsing and see actual HTML structure
"""

import requests
from bs4 import BeautifulSoup
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Browser-like headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}


def test_securities_page():
    """Test fetching securities list page"""
    print("\n" + "="*80)
    print("TESTING SECURITIES LIST PAGE")
    print("="*80 + "\n")

    url = "https://spbexchange.ru/listing/securities/list/"

    print(f"Fetching: {url}")

    try:
        session = requests.Session()
        response = session.get(url, verify=False, timeout=30, headers=HEADERS)

        print(f"Status code: {response.status_code}")
        print(f"Content length: {len(response.content)} bytes")

        soup = BeautifulSoup(response.content, 'html.parser')

        # Save HTML to file for inspection
        with open('output/debug_securities_page.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print("Saved HTML to: output/debug_securities_page.html")

        # Check for tables
        tables = soup.find_all('table')
        print(f"\nFound {len(tables)} tables")

        # Check for links
        all_links = soup.find_all('a', href=True)
        print(f"Found {len(all_links)} links total")

        # Check for securities links
        security_links = [a for a in all_links if '/listing/securities/' in a.get('href', '')]
        print(f"Found {len(security_links)} security links")

        if security_links:
            print("\nFirst 5 security links:")
            for i, link in enumerate(security_links[:5], 1):
                print(f"  {i}. {link.get_text(strip=True)[:50]} -> {link.get('href')}")

        # Check for specific text content
        page_text = soup.get_text()
        print(f"\nPage contains 'облигация': {'Yes' if 'облигация' in page_text.lower() else 'No'}")
        print(f"Page contains 'акция': {'Yes' if 'акция' in page_text.lower() else 'No'}")

        # Check for JavaScript/React indicators
        scripts = soup.find_all('script')
        print(f"\nFound {len(scripts)} script tags")

        # Check if it's a React/SPA app
        is_react = any('react' in str(script).lower() for script in scripts)
        is_spa = any(div.get('id') in ['root', 'app', 'main'] for div in soup.find_all('div'))

        print(f"Appears to be React app: {is_react}")
        print(f"Appears to be SPA: {is_spa}")

        return soup

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_issuers_page():
    """Test fetching Russian issuers page"""
    print("\n" + "="*80)
    print("TESTING RUSSIAN ISSUERS PAGE")
    print("="*80 + "\n")

    url = "https://issuers.spbexchange.ru/"

    print(f"Fetching: {url}")

    try:
        session = requests.Session()
        response = session.get(url, verify=False, timeout=30, headers=HEADERS)

        print(f"Status code: {response.status_code}")
        print(f"Content length: {len(response.content)} bytes")

        soup = BeautifulSoup(response.content, 'html.parser')

        # Save HTML to file for inspection
        with open('output/debug_issuers_page.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print("Saved HTML to: output/debug_issuers_page.html")

        # Check for links
        all_links = soup.find_all('a', href=True)
        print(f"\nFound {len(all_links)} links total")

        print("\nFirst 20 links:")
        for i, link in enumerate(all_links[:20], 1):
            text = link.get_text(strip=True)[:50]
            href = link.get('href')
            print(f"  {i}. '{text}' -> {href}")

        # Check for company names
        page_text = soup.get_text()
        has_pao = 'ПАО' in page_text or 'пао' in page_text.lower()
        has_ooo = 'ООО' in page_text or 'ооо' in page_text.lower()

        print(f"\nPage contains 'ПАО': {has_pao}")
        print(f"\nPage contains 'ООО': {has_ooo}")

        return soup

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_api_endpoints():
    """Test API endpoints"""
    print("\n" + "="*80)
    print("TESTING API ENDPOINTS")
    print("="*80 + "\n")

    # Test securities API
    api_url = "https://spbexchange.ru/ru/listing/securities/api/securities"
    params = {
        'page': 0,
        'size': 10,
    }

    print(f"Testing: {api_url}")
    print(f"Params: {params}")

    try:
        session = requests.Session()
        response = session.get(api_url, params=params, verify=False, timeout=30, headers=HEADERS)

        print(f"Status code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")

        if response.status_code == 200:
            try:
                data = response.json()
                print(f"JSON response received!")
                print(f"Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")

                if 'content' in data:
                    print(f"Number of items: {len(data.get('content', []))}")
                    if data.get('content'):
                        print(f"First item keys: {list(data['content'][0].keys())}")
                        print(f"First item: {data['content'][0]}")

                # Save to file
                import json
                with open('output/debug_api_response.json', 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print("Saved API response to: output/debug_api_response.json")

            except Exception as e:
                print(f"Failed to parse JSON: {e}")
                print(f"Response text (first 500 chars): {response.text[:500]}")
        else:
            print(f"Response text: {response.text[:500]}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import os
    os.makedirs('output', exist_ok=True)

    print("\n" + "="*80)
    print("SPBE PARSER DEBUG SCRIPT")
    print("="*80)

    # Test API endpoints
    test_api_endpoints()

    # Test securities page
    test_securities_page()

    # Test issuers page
    test_issuers_page()

    print("\n" + "="*80)
    print("DEBUG COMPLETED")
    print("="*80)
    print("\nCheck output/ directory for saved HTML and JSON files")
