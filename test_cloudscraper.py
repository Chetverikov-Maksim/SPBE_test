"""
Test cloudscraper to bypass Cloudflare protection
"""

import cloudscraper
from bs4 import BeautifulSoup

# Create scraper instance
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'mobile': False
    }
)

print("="*80)
print("TESTING WITH CLOUDSCRAPER")
print("="*80)

# Test securities page
print("\n1. Testing securities page...")
url = "https://spbexchange.ru/listing/securities/list/"
print(f"URL: {url}")

try:
    response = scraper.get(url, timeout=30)
    print(f"Status: {response.status_code}")
    print(f"Content length: {len(response.content)} bytes")

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        # Save to file
        with open('output/cloudscraper_securities.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())

        # Check content
        links = soup.find_all('a', href=True)
        security_links = [a for a in links if '/listing/securities/' in a.get('href', '')]

        print(f"Total links: {len(links)}")
        print(f"Security links: {len(security_links)}")

        if security_links:
            print("\nFirst 5 security links:")
            for i, link in enumerate(security_links[:5], 1):
                print(f"  {i}. {link.get_text(strip=True)[:50]} -> {link.get('href')}")

        print(f"✓ Success! Saved to output/cloudscraper_securities.html")
    else:
        print(f"✗ Failed with status {response.status_code}")
        print(f"Response: {response.text[:200]}")

except Exception as e:
    print(f"✗ Error: {e}")

# Test API
print("\n2. Testing API endpoint...")
api_url = "https://spbexchange.ru/ru/listing/securities/api/securities"
params = {'page': 0, 'size': 10}
print(f"URL: {api_url}")

try:
    response = scraper.get(api_url, params=params, timeout=30)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        try:
            data = response.json()
            print(f"✓ Got JSON response!")
            print(f"Keys: {list(data.keys())}")

            if 'content' in data:
                print(f"Items: {len(data.get('content', []))}")

                # Save to file
                import json
                with open('output/cloudscraper_api.json', 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"✓ Saved to output/cloudscraper_api.json")
        except:
            print(f"✗ Not JSON: {response.text[:200]}")
    else:
        print(f"✗ Failed with status {response.status_code}")

except Exception as e:
    print(f"✗ Error: {e}")

# Test Russian issuers
print("\n3. Testing Russian issuers page...")
url = "https://issuers.spbexchange.ru/"
print(f"URL: {url}")

try:
    response = scraper.get(url, timeout=30)
    print(f"Status: {response.status_code}")
    print(f"Content length: {len(response.content)} bytes")

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        # Save to file
        with open('output/cloudscraper_issuers.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())

        links = soup.find_all('a', href=True)
        print(f"Total links: {len(links)}")

        print("\nFirst 10 links:")
        for i, link in enumerate(links[:10], 1):
            print(f"  {i}. {link.get_text(strip=True)[:40]} -> {link.get('href')[:60]}")

        print(f"✓ Success! Saved to output/cloudscraper_issuers.html")
    else:
        print(f"✗ Failed with status {response.status_code}")

except Exception as e:
    print(f"✗ Error: {e}")

print("\n" + "="*80)
print("TESTING COMPLETED")
print("="*80)
