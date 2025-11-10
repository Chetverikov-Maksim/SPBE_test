"""
Check what dates are in HTML when using UTC timezone
"""

import logging
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOND_URL = "https://spbexchange.ru/listing/securities/card_bond/?issue=7563"  # XS2063279959

playwright = sync_playwright().start()
browser = playwright.firefox.launch(headless=True)

# Create context with UTC timezone
context = browser.new_context(
    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    ignore_https_errors=True,
    timezone_id='UTC',
    locale='en-US'
)

page = context.new_page()

logger.info(f"Loading bond page with UTC timezone: {BOND_URL}")
page.goto(BOND_URL, wait_until='networkidle', timeout=30000)

import time
time.sleep(3)

# Wait for fields
page.wait_for_selector('li.SecuritiesField_item__7TKJg', timeout=10000)

# Get HTML
page_html = page.evaluate('() => document.documentElement.outerHTML')
soup = BeautifulSoup(page_html, 'html.parser')

logger.info("\n" + "="*80)
logger.info("Searching for date fields in HTML (with UTC timezone)")
logger.info("="*80)

# Find all fields
fields = soup.find_all('li', class_='SecuritiesField_item__7TKJg')
logger.info(f"\nFound {len(fields)} fields total")

date_field_names = ['Дата выпуска', 'Дата погашения', 'Дата принятия решения', 'Дата включения']

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
            logger.info(f"  Value in HTML: {value}")

            # Also check raw HTML
            raw_html = str(desc_element)
            logger.info(f"  Raw HTML: {raw_html[:300]}")

# Also try via Playwright methods
logger.info("\n" + "="*80)
logger.info("Same fields via Playwright methods")
logger.info("="*80)

fields_pw = page.query_selector_all('li.SecuritiesField_item__7TKJg')
for field in fields_pw:
    title_elem = field.query_selector('h3.SecuritiesField_itemTitle__7dfHY div')
    if not title_elem:
        continue

    title = title_elem.inner_text().strip()

    is_date_field = any(date_name in title for date_name in date_field_names)

    if is_date_field:
        desc_elem = field.query_selector('div.SecuritiesField_itemDesc__JZ7w7')
        if desc_elem:
            value_inner = desc_elem.inner_text()
            value_text = desc_elem.text_content()

            logger.info(f"\n{title}:")
            logger.info(f"  inner_text(): {value_inner}")
            logger.info(f"  text_content(): {value_text}")

browser.close()
playwright.stop()

logger.info("\n" + "="*80)
logger.info("Debug completed")
logger.info("="*80)
