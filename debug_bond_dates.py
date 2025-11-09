"""
Debug script to investigate date fields and TIN field for specific bond
"""

import logging
import time
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_bond_dates():
    """Debug date fields to understand why dates are shifted by +1 day"""

    # Bond XS2063279959
    BOND_URL = "https://spbexchange.ru/listing/securities/card_bond/?issue=6198"

    playwright = sync_playwright().start()
    browser = playwright.firefox.launch(headless=True)

    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        ignore_https_errors=True
    )

    page = context.new_page()
    page.set_default_timeout(30000)

    logger.info(f"Navigating to bond page: {BOND_URL}")
    page.goto(BOND_URL, wait_until='networkidle', timeout=30000)
    time.sleep(3)

    # Wait for fields
    page.wait_for_selector('li.SecuritiesField_item__7TKJg', timeout=10000)

    # Find all fields
    fields = page.query_selector_all('li.SecuritiesField_item__7TKJg')
    logger.info(f"\nFound {len(fields)} fields total")

    # Focus on date fields and TIN field
    target_fields = ['Дата выпуска', 'Дата погашения', 'Идентификационный номер налогоплательщика эмитента (при наличии)']

    for field in fields:
        try:
            title_element = field.query_selector('h3.SecuritiesField_itemTitle__7dfHY div')
            if not title_element:
                continue

            title = title_element.inner_text().strip()
            if '[' in title:
                title = title.split('[')[0].strip()

            if title not in target_fields:
                continue

            logger.info(f"\n{'='*80}")
            logger.info(f"FIELD: {title}")
            logger.info(f"{'='*80}")

            desc_element = field.query_selector('div.SecuritiesField_itemDesc__JZ7w7')
            if not desc_element:
                logger.warning("Description element not found")
                continue

            # Get value different ways
            inner_text_value = desc_element.inner_text()
            text_content_value = desc_element.text_content()
            outer_html = desc_element.evaluate('el => el.outerHTML')

            logger.info(f"inner_text(): {inner_text_value}")
            logger.info(f"text_content(): {text_content_value}")
            logger.info(f"\nHTML:\n{outer_html[:500]}")

            # Check for time/datetime elements
            time_elements = desc_element.query_selector_all('time')
            if time_elements:
                logger.info(f"\nFound {len(time_elements)} <time> elements:")
                for i, time_elem in enumerate(time_elements):
                    datetime_attr = time_elem.get_attribute('datetime')
                    title_attr = time_elem.get_attribute('title')
                    data_value = time_elem.get_attribute('data-value')
                    inner = time_elem.inner_text()

                    logger.info(f"  Time element {i}:")
                    logger.info(f"    datetime attribute: {datetime_attr}")
                    logger.info(f"    title attribute: {title_attr}")
                    logger.info(f"    data-value attribute: {data_value}")
                    logger.info(f"    inner_text: {inner}")

            # Check for any data-* attributes on desc element
            all_attributes = desc_element.evaluate('''el => {
                const attrs = {};
                for (let attr of el.attributes) {
                    attrs[attr.name] = attr.value;
                }
                return attrs;
            }''')

            if all_attributes:
                logger.info(f"\nAll attributes on desc element:")
                for attr_name, attr_value in all_attributes.items():
                    logger.info(f"  {attr_name}: {attr_value}")

        except Exception as e:
            logger.error(f"Error processing field: {e}")

    # Save full page HTML for inspection
    html_content = page.content()
    with open('/home/user/SPBE_test/debug_bond_XS2063279959.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    logger.info(f"\nFull HTML saved to: /home/user/SPBE_test/debug_bond_XS2063279959.html")

    browser.close()
    playwright.stop()

if __name__ == "__main__":
    debug_bond_dates()
