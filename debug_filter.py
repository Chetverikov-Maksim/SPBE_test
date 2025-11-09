"""
Debug script to investigate the filter button and modal structure
"""

import logging
import time
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_filter():
    """Debug the filter modal to see what appears after clicking filter button"""

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

    # Navigate to bonds list
    logger.info(f"Navigating to: {BONDS_LIST_URL}")
    page.goto(BONDS_LIST_URL, wait_until='domcontentloaded')

    # Wait for table
    try:
        page.wait_for_selector('.Table_root__2EkV0', timeout=10000)
        logger.info("Table found")
    except:
        logger.warning("Table not found")

    time.sleep(3)

    # Save screenshot BEFORE clicking filter
    page.screenshot(path='/home/user/SPBE_test/before_filter_click.png')
    logger.info("Screenshot saved: /home/user/SPBE_test/before_filter_click.png")

    # Find and click filter button
    logger.info("\n=== Clicking filter button ===")
    filter_button_selector = 'button:has(svg path[d*="M3.6 3h12.8"])'
    filter_button = page.query_selector(filter_button_selector)

    if filter_button:
        logger.info("Filter button found")
        filter_button.click()
        logger.info("Clicked filter button")
    else:
        logger.error("Filter button NOT found")

        # Try to find all buttons
        all_buttons = page.query_selector_all('button')
        logger.info(f"Total buttons on page: {len(all_buttons)}")

        # Try to find all SVG icons
        all_svgs = page.query_selector_all('svg')
        logger.info(f"Total SVG icons on page: {len(all_svgs)}")
        browser.close()
        playwright.stop()
        return

    # Wait a bit for modal to appear
    time.sleep(3)

    # Save screenshot AFTER clicking filter
    page.screenshot(path='/home/user/SPBE_test/after_filter_click.png')
    logger.info("Screenshot saved: /home/user/SPBE_test/after_filter_click.png")

    # Save HTML after click
    html_content = page.content()
    with open('/home/user/SPBE_test/after_filter_click.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    logger.info("HTML saved: /home/user/SPBE_test/after_filter_click.html")

    # Check for modal/popup
    logger.info("\n=== Looking for modal/popup ===")

    modal_selectors = [
        '[role="dialog"]',
        '[role="modal"]',
        '.modal',
        '.Modal',
        '[class*="modal"]',
        '[class*="Modal"]',
        '[class*="popup"]',
        '[class*="Popup"]',
        '[class*="dialog"]',
        '[class*="Dialog"]',
    ]

    for selector in modal_selectors:
        elements = page.query_selector_all(selector)
        if elements:
            logger.info(f"Found {len(elements)} elements for selector: {selector}")
            for i, elem in enumerate(elements[:3]):
                logger.info(f"  Element {i}: visible={elem.is_visible()}, class={elem.get_attribute('class')}")

    # Look for checkboxes
    logger.info("\n=== Looking for checkboxes ===")
    all_checkboxes = page.query_selector_all('input[type="checkbox"]')
    logger.info(f"Total checkboxes found: {len(all_checkboxes)}")

    for i, cb in enumerate(all_checkboxes[:10]):
        try:
            visible = cb.is_visible()
            parent = cb.evaluate('element => element.parentElement')
            parent_class = cb.evaluate('element => element.parentElement?.className || "N/A"')
            parent_text = cb.evaluate('element => element.parentElement?.textContent || "N/A"')
            logger.info(f"Checkbox {i}: visible={visible}, parent_class={parent_class[:50]}, text={parent_text[:50]}")
        except Exception as e:
            logger.error(f"Error checking checkbox {i}: {e}")

    # Look for labels
    logger.info("\n=== Looking for labels ===")
    all_labels = page.query_selector_all('label')
    logger.info(f"Total labels found: {len(all_labels)}")

    for i, label in enumerate(all_labels[:10]):
        try:
            visible = label.is_visible()
            text = label.inner_text()
            logger.info(f"Label {i}: visible={visible}, text={text[:50]}")
        except Exception as e:
            logger.error(f"Error checking label {i}: {e}")

    # Try locator approach
    logger.info("\n=== Trying locator approach ===")
    try:
        облигации_locator = page.locator('text="Облигации"')
        count = облигации_locator.count()
        logger.info(f"Found {count} elements with text 'Облигации'")

        for i in range(min(count, 5)):
            elem = облигации_locator.nth(i)
            visible = elem.is_visible()
            logger.info(f"  Element {i}: visible={visible}")
    except Exception as e:
        logger.error(f"Locator error: {e}")

    # Search for security type section
    logger.info("\n=== Searching for 'Вид ценной бумаги' section ===")
    try:
        security_type_locator = page.locator('text="Вид ценной бумаги"')
        count = security_type_locator.count()
        logger.info(f"Found {count} elements with text 'Вид ценной бумаги'")

        for i in range(min(count, 3)):
            elem = security_type_locator.nth(i)
            visible = elem.is_visible()
            tag = elem.evaluate('el => el.tagName')
            text = elem.inner_text()
            logger.info(f"  Element {i}: visible={visible}, tag={tag}, text={text[:100]}")
    except Exception as e:
        logger.error(f"Error searching for security type: {e}")

    # Look for all visible text on page
    logger.info("\n=== Looking for all visible text containing 'бумаги' ===")
    try:
        all_text = page.locator('*:visible')
        count = all_text.count()
        logger.info(f"Total visible elements: {count}")

        # Search for elements containing specific keywords
        for keyword in ['бумаги', 'фильтр', 'Применить', 'Облигаци']:
            keyword_locator = page.locator(f'text=/{keyword}/i')
            keyword_count = keyword_locator.count()
            logger.info(f"Elements containing '{keyword}': {keyword_count}")

            for i in range(min(keyword_count, 3)):
                try:
                    elem = keyword_locator.nth(i)
                    if elem.is_visible():
                        text = elem.inner_text()
                        logger.info(f"  {keyword} #{i}: {text[:80]}")
                except:
                    pass
    except Exception as e:
        logger.error(f"Error searching for keywords: {e}")

    # Wait a bit before closing
    logger.info("\n=== Waiting 10 seconds before closing (check the browser window) ===")
    time.sleep(10)

    browser.close()
    playwright.stop()

    logger.info("\nDebug completed. Check screenshots and HTML files.")

if __name__ == "__main__":
    debug_filter()
