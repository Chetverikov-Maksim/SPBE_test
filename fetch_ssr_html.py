"""
Fetch initial Server-Side Rendered HTML via HTTP request
without browser to check what server actually sends
"""

import requests
import logging
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOND_URL = "https://spbexchange.ru/listing/securities/card_bond/?issue=7563"  # XS2063279959

logger.info("="*80)
logger.info("Fetching initial HTML from server via HTTP request")
logger.info("="*80)

# Make HTTP request without browser
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

logger.info(f"\nFetching: {BOND_URL}")
response = requests.get(BOND_URL, headers=headers, verify=False, timeout=30)

logger.info(f"Response status: {response.status_code}")
logger.info(f"Response length: {len(response.text)}")

# Parse HTML
soup = BeautifulSoup(response.text, 'html.parser')

# Look for date fields
fields = soup.find_all('li', class_='SecuritiesField_item__7TKJg')
logger.info(f"\nFound {len(fields)} fields in SSR HTML")

date_field_names = ['Дата выпуска', 'Дата погашения', 'Дата принятия', 'Дата включения']

for field in fields:
    title_element = field.find('h3', class_='SecuritiesField_itemTitle__7dfHY')
    if not title_element:
        continue

    title_div = title_element.find('div')
    if not title_div:
        continue

    title = title_div.get_text(strip=True)

    # Check if it's a date field
    is_date_field = any(date_name in title for date_name in date_field_names)

    if is_date_field:
        desc_element = field.find('div', class_='SecuritiesField_itemDesc__JZ7w7')
        if desc_element:
            value = desc_element.get_text(strip=True)
            logger.info(f"\n{title}:")
            logger.info(f"  Value in SSR HTML: {value}")

# Save HTML for inspection
with open('/home/user/SPBE_test/ssr_html.html', 'w', encoding='utf-8') as f:
    f.write(response.text)
logger.info("\nSaved SSR HTML to ssr_html.html")

logger.info("\n" + "="*80)
logger.info("Done. Check ssr_html.html file")
logger.info("="*80)
