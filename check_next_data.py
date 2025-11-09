"""
Check if Next.js stores data in __NEXT_DATA__ script tag
"""

import logging
import json
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOND_URL = "https://spbexchange.ru/listing/securities/card_bond/?issue=7563"  # XS2063279959

playwright = sync_playwright().start()
browser = playwright.firefox.launch(headless=True)

context = browser.new_context(
    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    ignore_https_errors=True
)

page = context.new_page()
page.goto(BOND_URL, wait_until='networkidle', timeout=30000)

import time
time.sleep(3)

# Get HTML
page_html = page.evaluate('() => document.documentElement.outerHTML')
soup = BeautifulSoup(page_html, 'html.parser')

logger.info("="*80)
logger.info("Searching for Next.js data in script tags")
logger.info("="*80)

# Look for __NEXT_DATA__ script
next_data_script = soup.find('script', id='__NEXT_DATA__')
if next_data_script:
    logger.info("\nFound __NEXT_DATA__ script!")
    try:
        data = json.loads(next_data_script.string)
        logger.info(f"JSON data keys: {data.keys()}")

        # Pretty print the data
        logger.info("\nFull JSON data:")
        logger.info(json.dumps(data, indent=2, ensure_ascii=False)[:5000])

        # Save to file
        with open('/home/user/SPBE_test/next_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("\nSaved to next_data.json")

    except Exception as e:
        logger.error(f"Error parsing JSON: {e}")
else:
    logger.info("\n__NEXT_DATA__ script not found")

# Look for all script tags
logger.info("\n" + "="*80)
logger.info("All script tags on page")
logger.info("="*80)

scripts = soup.find_all('script')
logger.info(f"\nFound {len(scripts)} script tags")

for i, script in enumerate(scripts[:10]):
    script_id = script.get('id', 'no-id')
    script_type = script.get('type', 'no-type')
    script_src = script.get('src', 'inline')

    logger.info(f"\nScript {i}:")
    logger.info(f"  ID: {script_id}")
    logger.info(f"  Type: {script_type}")
    logger.info(f"  Src: {script_src}")

    if script.string and len(script.string) > 0:
        preview = script.string[:200].replace('\n', ' ')
        logger.info(f"  Content preview: {preview}")

browser.close()
playwright.stop()
