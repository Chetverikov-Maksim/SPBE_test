"""
Debug script to investigate issuer page structure
"""

import logging
import time
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_issuer_page():
    """Debug issuer page to find securities section"""

    BASE_URL = "https://spbexchange.ru"
    # Используем первого эмитента из логов: АК "АЛРОСА" (ПАО) - 1021400967092
    ISSUER_URL = f"{BASE_URL}/ru/issuers/securities/?ogrn=1021400967092"

    playwright = sync_playwright().start()
    browser = playwright.firefox.launch(headless=True)

    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        ignore_https_errors=True
    )

    page = context.new_page()
    page.set_default_timeout(30000)

    logger.info(f"Navigating to issuer page: {ISSUER_URL}")
    page.goto(ISSUER_URL, wait_until='domcontentloaded')
    time.sleep(3)

    # Save screenshot and HTML
    page.screenshot(path='/home/user/SPBE_test/debug_issuer.png')
    logger.info("Screenshot saved: /home/user/SPBE_test/debug_issuer.png")

    html_content = page.content()
    with open('/home/user/SPBE_test/debug_issuer.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    logger.info("HTML saved: /home/user/SPBE_test/debug_issuer.html")

    # Search for various link patterns
    logger.info("\n=== Searching for links ===")

    # Look for all links
    all_links = page.query_selector_all('a')
    logger.info(f"Total links on page: {len(all_links)}")

    # Look for links with specific keywords
    keywords = ['ценные бумаги', 'Ценные бумаги', 'облигаци', 'Облигаци', 'проспект', 'Проспект']

    for keyword in keywords:
        try:
            matching_links = page.locator(f'a:has-text("{keyword}")').all()
            logger.info(f"\nLinks containing '{keyword}': {len(matching_links)}")

            for i, link in enumerate(matching_links[:5]):
                try:
                    href = link.get_attribute('href')
                    text = link.inner_text()
                    logger.info(f"  Link {i}: text='{text[:80]}', href='{href}'")
                except:
                    pass
        except Exception as e:
            logger.error(f"Error searching for '{keyword}': {e}")

    # Look for tabs/sections
    logger.info("\n=== Searching for tabs/sections ===")

    tab_selectors = [
        '[role="tab"]',
        '.tab',
        '[class*="Tab"]',
        '[class*="tab"]',
        'button[class*="tab"]',
        'a[class*="tab"]'
    ]

    for selector in tab_selectors:
        try:
            tabs = page.query_selector_all(selector)
            if tabs:
                logger.info(f"\nFound {len(tabs)} elements for selector: {selector}")
                for i, tab in enumerate(tabs[:5]):
                    try:
                        text = tab.inner_text()
                        logger.info(f"  Tab {i}: {text[:80]}")
                    except:
                        pass
        except:
            pass

    # Look for tables
    logger.info("\n=== Searching for tables ===")
    tables = page.query_selector_all('table')
    logger.info(f"Found {len(tables)} tables")

    # Look for download/PDF links
    logger.info("\n=== Searching for download links ===")
    download_links = page.query_selector_all('a[href*=".pdf"], a[download], a[href*="download"]')
    logger.info(f"Found {len(download_links)} download links")

    for i, link in enumerate(download_links[:10]):
        try:
            href = link.get_attribute('href')
            text = link.inner_text()
            logger.info(f"  Download link {i}: text='{text[:50]}', href='{href[:100]}'")
        except:
            pass

    # Look for text "проспект" anywhere on page
    logger.info("\n=== Searching for 'проспект' text ===")
    prospectus_elements = page.locator('text=/проспект/i').all()
    logger.info(f"Found {len(prospectus_elements)} elements containing 'проспект'")

    for i, elem in enumerate(prospectus_elements[:10]):
        try:
            text = elem.inner_text()
            logger.info(f"  Element {i}: {text[:100]}")
        except:
            pass

    logger.info("\n=== Waiting 5 seconds before closing ===")
    time.sleep(5)

    browser.close()
    playwright.stop()

    logger.info("\nDebug completed. Check debug_issuer.html and debug_issuer.png")

if __name__ == "__main__":
    debug_issuer_page()
