"""
Debug script to investigate the bonds list page structure
"""

import logging
import time
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_bonds_page():
    """Debug the bonds list page to see actual structure"""

    BASE_URL = "https://spbexchange.ru"
    BONDS_LIST_URL = f"{BASE_URL}/listing/securities/list/"

    playwright = sync_playwright().start()

    browser = playwright.firefox.launch(headless=True)

    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        ignore_https_errors=True
    )

    page = context.new_page()
    page.set_default_timeout(30000)

    # Navigate to bonds list with filter
    bonds_url = f"{BONDS_LIST_URL}?page=0&size=50&sortBy=securityKind&sortByDirection=desc&securityKind=Облигации"
    logger.info(f"Navigating to: {bonds_url}")

    page.goto(bonds_url, wait_until='networkidle')

    # Wait for spinner to disappear
    try:
        page.wait_for_selector('.LoadingSpinner_root__K9Qwq', state='detached', timeout=30000)
        logger.info("Spinner disappeared")
    except:
        logger.warning("Spinner not found or didn't disappear")

    time.sleep(5)  # Extra wait

    # Save screenshot
    page.screenshot(path='debug_bonds_page.png')
    logger.info("Screenshot saved to debug_bonds_page.png")

    # Save HTML
    html_content = page.content()
    with open('debug_bonds_page.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    logger.info("HTML saved to debug_bonds_page.html")

    # Try different selectors
    logger.info("\n=== Testing different selectors ===")

    selectors = [
        'a[href*="/listing/securities/card_bond/"]',
        'a[href*="?issue="]',
        'a[href*="card_bond"]',
        'table a',
        'tbody a',
        'tr a',
        '.securities-table a',
        'a',
    ]

    for selector in selectors:
        try:
            elements = page.query_selector_all(selector)
            logger.info(f"Selector '{selector}': found {len(elements)} elements")

            if elements and len(elements) <= 10:
                for i, elem in enumerate(elements[:5]):
                    href = elem.get_attribute('href')
                    text = elem.inner_text()[:50] if elem.inner_text() else 'N/A'
                    logger.info(f"  [{i}] href={href}, text={text}")
        except Exception as e:
            logger.error(f"Selector '{selector}': error - {e}")

    # Check if table exists
    logger.info("\n=== Checking for tables ===")
    tables = page.query_selector_all('table')
    logger.info(f"Found {len(tables)} tables")

    # Check for specific classes
    logger.info("\n=== Checking for specific classes ===")
    classes_to_check = [
        '.SecuritiesTable_table__7h3Kw',
        '.securities-table',
        '[class*="Table"]',
        '[class*="Securities"]',
    ]

    for cls in classes_to_check:
        elements = page.query_selector_all(cls)
        logger.info(f"Class '{cls}': found {len(elements)} elements")

    browser.close()
    playwright.stop()

    logger.info("\nDebug completed. Check debug_bonds_page.html and debug_bonds_page.png")

if __name__ == "__main__":
    debug_bonds_page()
