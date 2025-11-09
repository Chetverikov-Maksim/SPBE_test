"""
Advanced debug script to investigate date parsing issue
Tests multiple approaches to get correct dates without +1 day shift
"""

import logging
import time
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_dates_advanced():
    """Advanced debugging for date fields"""

    # Bond XS2063279959
    BOND_URL = "https://spbexchange.ru/listing/securities/card_bond/?issue=6198"

    playwright = sync_playwright().start()

    # Test 1: Normal browser
    logger.info("="*80)
    logger.info("TEST 1: Normal Firefox with JavaScript enabled")
    logger.info("="*80)

    browser = playwright.firefox.launch(headless=True)
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        ignore_https_errors=True
    )
    page = context.new_page()
    page.goto(BOND_URL, wait_until='networkidle', timeout=30000)
    time.sleep(3)

    # Get Issue Date field using different methods
    page.wait_for_selector('li.SecuritiesField_item__7TKJg', timeout=10000)

    # Method 1: via Playwright query_selector
    logger.info("\nMethod 1: Playwright query_selector + inner_text()")
    fields = page.query_selector_all('li.SecuritiesField_item__7TKJg')
    for field in fields:
        title_elem = field.query_selector('h3.SecuritiesField_itemTitle__7dfHY div')
        if title_elem and 'Дата выпуска' in title_elem.inner_text():
            desc_elem = field.query_selector('div.SecuritiesField_itemDesc__JZ7w7')
            if desc_elem:
                value = desc_elem.inner_text()
                logger.info(f"  Issue Date (inner_text): {value}")

                # Try text_content
                value2 = desc_elem.text_content()
                logger.info(f"  Issue Date (text_content): {value2}")

                # Try innerHTML
                inner_html = desc_elem.inner_html()
                logger.info(f"  Issue Date (inner_html): {inner_html[:200]}")

                # Try outerHTML
                outer_html = desc_elem.evaluate('el => el.outerHTML')
                logger.info(f"  Issue Date (outerHTML): {outer_html[:200]}")
            break

    # Method 2: Get via evaluate and document.querySelector
    logger.info("\nMethod 2: page.evaluate with document.querySelector")
    result = page.evaluate('''() => {
        const fields = document.querySelectorAll('li.SecuritiesField_item__7TKJg');
        for (const field of fields) {
            const title = field.querySelector('h3.SecuritiesField_itemTitle__7dfHY div');
            if (title && title.textContent.includes('Дата выпуска')) {
                const desc = field.querySelector('div.SecuritiesField_itemDesc__JZ7w7');
                if (desc) {
                    return {
                        textContent: desc.textContent,
                        innerText: desc.innerText,
                        innerHTML: desc.innerHTML,
                        outerHTML: desc.outerHTML
                    };
                }
            }
        }
        return null;
    }''')
    if result:
        logger.info(f"  textContent: {result['textContent']}")
        logger.info(f"  innerText: {result['innerText']}")
        logger.info(f"  innerHTML: {result['innerHTML'][:200]}")
        logger.info(f"  outerHTML: {result['outerHTML'][:200]}")

    # Method 3: Get full page HTML via different ways
    logger.info("\nMethod 3: Full page HTML via different methods")

    html1 = page.content()
    logger.info(f"  page.content() length: {len(html1)}")
    if 'Дата выпуска' in html1:
        idx = html1.find('Дата выпуска')
        snippet = html1[idx:idx+500]
        logger.info(f"  Snippet around 'Дата выпуска': {snippet[:300]}")

    html2 = page.evaluate('() => document.documentElement.outerHTML')
    logger.info(f"  evaluate outerHTML length: {len(html2)}")
    if 'Дата выпуска' in html2:
        idx = html2.find('Дата выпуска')
        snippet = html2[idx:idx+500]
        logger.info(f"  Snippet around 'Дата выпуска': {snippet[:300]}")

    # Check if dates are in data attributes
    logger.info("\nMethod 4: Check for data-* attributes")
    date_elements = page.query_selector_all('[data-date], [data-value], [datetime]')
    logger.info(f"  Found {len(date_elements)} elements with date-related attributes")
    for i, elem in enumerate(date_elements[:5]):
        attrs = elem.evaluate('''el => {
            const result = {};
            for (let attr of el.attributes) {
                result[attr.name] = attr.value;
            }
            return result;
        }''')
        logger.info(f"  Element {i} attributes: {attrs}")

    browser.close()

    # Test 2: Browser with JavaScript disabled
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Firefox with JavaScript DISABLED")
    logger.info("="*80)

    browser2 = playwright.firefox.launch(headless=True)
    context2 = browser2.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        ignore_https_errors=True,
        java_script_enabled=False  # Disable JavaScript
    )
    page2 = context2.new_page()

    try:
        page2.goto(BOND_URL, wait_until='domcontentloaded', timeout=30000)
        time.sleep(3)

        html_no_js = page2.content()
        logger.info(f"  HTML length with JS disabled: {len(html_no_js)}")

        if 'Дата выпуска' in html_no_js:
            idx = html_no_js.find('Дата выпуска')
            snippet = html_no_js[idx:idx+500]
            logger.info(f"  Snippet around 'Дата выпуска': {snippet[:300]}")
        else:
            logger.info("  'Дата выпуска' not found in HTML (expected for React app)")

        # Save HTML for inspection
        with open('/home/user/SPBE_test/debug_bond_no_js.html', 'w', encoding='utf-8') as f:
            f.write(html_no_js)
        logger.info("  Saved HTML to debug_bond_no_js.html")

    except Exception as e:
        logger.error(f"  Error with JS disabled: {e}")

    browser2.close()

    # Test 3: Intercept network response
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Intercept initial HTML from network")
    logger.info("="*80)

    browser3 = playwright.firefox.launch(headless=True)
    context3 = browser3.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        ignore_https_errors=True
    )
    page3 = context3.new_page()

    initial_html = None

    def handle_response(response):
        nonlocal initial_html
        if response.url == BOND_URL and response.status == 200:
            try:
                initial_html = response.text()
                logger.info(f"  Intercepted HTML response, length: {len(initial_html)}")
            except:
                pass

    page3.on("response", handle_response)
    page3.goto(BOND_URL, wait_until='networkidle', timeout=30000)
    time.sleep(1)

    if initial_html and 'Дата выпуска' in initial_html:
        idx = initial_html.find('Дата выпуска')
        snippet = initial_html[idx:idx+500]
        logger.info(f"  Snippet from initial response: {snippet[:300]}")

        # Save for inspection
        with open('/home/user/SPBE_test/debug_bond_initial_response.html', 'w', encoding='utf-8') as f:
            f.write(initial_html)
        logger.info("  Saved to debug_bond_initial_response.html")
    else:
        logger.info("  'Дата выпуска' not found in initial response")

    browser3.close()
    playwright.stop()

    logger.info("\n" + "="*80)
    logger.info("Debug completed. Check saved HTML files.")
    logger.info("="*80)

if __name__ == "__main__":
    debug_dates_advanced()
