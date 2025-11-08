"""
Utility functions for SPBE parser
"""

import os
import re
import time
import logging
import json
from typing import Optional, Dict, Any
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import urllib3

from .config import (
    REQUEST_TIMEOUT,
    REQUEST_DELAY,
    MAX_RETRIES,
    USER_AGENT,
    LOG_FORMAT,
    LOG_LEVEL,
    COUPON_FREQUENCY_MAPPING,
    BOOLEAN_MAPPING,
    VERIFY_SSL,
    USE_SELENIUM,
    SELENIUM_HEADLESS,
    SELENIUM_PAGE_LOAD_TIMEOUT,
    SELENIUM_IMPLICIT_WAIT,
)

# Disable SSL warnings if verification is disabled
if not VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Global Selenium driver instance (lazy-loaded)
_selenium_driver = None


def get_selenium_driver(logger: logging.Logger):
    """
    Get or create Selenium WebDriver instance

    Args:
        logger: Logger instance

    Returns:
        WebDriver instance
    """
    global _selenium_driver

    if _selenium_driver is not None:
        return _selenium_driver

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager

        logger.info("Initializing Selenium WebDriver...")

        # Configure Chrome options
        chrome_options = Options()

        if SELENIUM_HEADLESS:
            chrome_options.add_argument('--headless=new')
            logger.debug("Running Chrome in headless mode")

        # Additional options to appear more like a real browser
        chrome_options.add_argument(f'--user-agent={USER_AGENT}')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')

        # Exclude automation flags
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Initialize driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Set timeouts
        driver.set_page_load_timeout(SELENIUM_PAGE_LOAD_TIMEOUT)
        driver.implicitly_wait(SELENIUM_IMPLICIT_WAIT)

        # Execute script to hide webdriver property
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        _selenium_driver = driver
        logger.info("Selenium WebDriver initialized successfully")

        return _selenium_driver

    except Exception as e:
        logger.error(f"Failed to initialize Selenium WebDriver: {e}")
        raise


def close_selenium_driver(logger: logging.Logger):
    """
    Close Selenium WebDriver instance

    Args:
        logger: Logger instance
    """
    global _selenium_driver

    if _selenium_driver is not None:
        try:
            logger.info("Closing Selenium WebDriver...")
            _selenium_driver.quit()
            _selenium_driver = None
            logger.info("Selenium WebDriver closed")
        except Exception as e:
            logger.warning(f"Error closing Selenium WebDriver: {e}")


def fetch_with_selenium(url: str, logger: logging.Logger, wait_time: int = 3) -> Optional[str]:
    """
    Fetch HTML content using Selenium

    Args:
        url: URL to fetch
        logger: Logger instance
        wait_time: Time to wait for page to load (seconds)

    Returns:
        HTML content as string or None if failed
    """
    try:
        driver = get_selenium_driver(logger)

        logger.debug(f"Fetching with Selenium: {url}")
        driver.get(url)

        # Wait for page to load
        time.sleep(wait_time)

        # Get page source
        html = driver.page_source

        logger.debug(f"Successfully fetched {len(html)} bytes from {url}")
        return html

    except Exception as e:
        logger.error(f"Selenium fetch failed for {url}: {e}")
        return None


def setup_logger(name: str, log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up logger with console and optional file handler

    Args:
        name: Logger name
        log_file: Optional log file path

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL))

    # Remove existing handlers
    logger.handlers = []

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, LOG_LEVEL))
    console_formatter = logging.Formatter(LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, LOG_LEVEL))
        file_formatter = logging.Formatter(LOG_FORMAT)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def make_request(url: str, logger: logging.Logger, method: str = "GET", **kwargs) -> Optional[requests.Response]:
    """
    Make HTTP request with retry logic

    Args:
        url: URL to request
        logger: Logger instance
        method: HTTP method (GET, POST, etc.)
        **kwargs: Additional arguments to pass to requests

    Returns:
        Response object or None if all retries failed
    """
    # Set comprehensive browser-like headers
    headers = kwargs.get('headers', {})

    # Add all necessary headers to look like a real browser
    default_headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }

    # Merge with provided headers (provided headers take priority)
    for key, value in default_headers.items():
        if key not in headers:
            headers[key] = value

    kwargs['headers'] = headers

    if 'timeout' not in kwargs:
        kwargs['timeout'] = REQUEST_TIMEOUT

    # Set SSL verification
    if 'verify' not in kwargs:
        kwargs['verify'] = VERIFY_SSL

    # Create session for persistent cookies
    session = requests.Session()

    for attempt in range(MAX_RETRIES):
        try:
            logger.debug(f"Requesting {url} (attempt {attempt + 1}/{MAX_RETRIES})")

            if method.upper() == "GET":
                response = session.get(url, **kwargs)
            elif method.upper() == "POST":
                response = session.post(url, **kwargs)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None

            response.raise_for_status()

            # Check if we got blocked (403 with "Access denied" or similar)
            if response.status_code == 403 or (response.status_code == 200 and len(response.content) < 100 and b'denied' in response.content.lower()):
                logger.warning(f"Possible access block detected (status: {response.status_code}, content length: {len(response.content)})")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(3 * (2 ** attempt))  # Longer wait when blocked
                    continue

            time.sleep(REQUEST_DELAY)
            return response

        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 403:
                logger.warning(f"403 Forbidden - Site may be blocking requests (attempt {attempt + 1}/{MAX_RETRIES})")
            else:
                logger.warning(f"HTTP error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")

            if attempt < MAX_RETRIES - 1:
                time.sleep(3 * (2 ** attempt))
            else:
                logger.error(f"All retry attempts failed for {url}")
                return None

        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                logger.error(f"All retry attempts failed for {url}")
                return None

    return None


def get_html(url: str, logger: logging.Logger) -> Optional[str]:
    """
    Get HTML content from URL (works with both Selenium and requests)

    Args:
        url: URL to fetch
        logger: Logger instance

    Returns:
        HTML content as string or None if failed
    """
    if USE_SELENIUM:
        # Use Selenium to fetch HTML
        return fetch_with_selenium(url, logger)
    else:
        # Use requests library
        response = make_request(url, logger)
        if response:
            return response.text
        return None


def get_soup(url: str, logger: logging.Logger) -> Optional[BeautifulSoup]:
    """
    Get BeautifulSoup object from URL

    Args:
        url: URL to parse
        logger: Logger instance

    Returns:
        BeautifulSoup object or None if failed
    """
    html = get_html(url, logger)
    if html:
        return BeautifulSoup(html, 'html.parser')
    return None


def extract_json_from_nextjs_html(html_content: str, logger: logging.Logger) -> Optional[Dict[str, Any]]:
    """
    Extract JSON data from Next.js server-side rendered HTML

    Next.js embeds data in <script> tags in the format:
    self.__next_f.push([1,"...JSON data..."])

    Args:
        html_content: HTML content as string
        logger: Logger instance

    Returns:
        Extracted pageData dictionary or None
    """
    try:
        # Find all script tags with self.__next_f.push
        script_pattern = r'self\.__next_f\.push\(\[1,"(.+?)"\]\)'
        matches = re.findall(script_pattern, html_content, re.DOTALL)

        if not matches:
            logger.warning("No Next.js data found in HTML")
            return None

        # Concatenate all matched data
        full_data = ''.join(matches)

        # Look for pageData in the concatenated string
        page_data_match = re.search(r'"pageData":\{(.+?)\},"params"', full_data)

        if not page_data_match:
            logger.warning("No pageData found in Next.js scripts")
            return None

        # Extract the pageData JSON
        page_data_json = '{' + page_data_match.group(1) + '}'

        # Unescape the JSON string
        page_data_json = page_data_json.replace('\\', '')

        # Parse JSON
        page_data = json.loads(page_data_json)

        logger.debug(f"Successfully extracted pageData with {len(page_data.get('content', []))} items")
        return page_data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from HTML: {e}")
        return None
    except Exception as e:
        logger.error(f"Error extracting JSON from HTML: {e}")
        return None


def download_file(url: str, output_path: str, logger: logging.Logger, force: bool = False) -> bool:
    """
    Download file from URL to local path

    Args:
        url: URL to download from
        output_path: Local path to save file
        logger: Logger instance
        force: Force download even if file exists

    Returns:
        True if successful, False otherwise
    """
    # Check if file already exists
    if os.path.exists(output_path) and not force:
        logger.debug(f"File already exists, skipping: {output_path}")
        return True

    # Create directory if needed
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Download file
    response = make_request(url, logger, stream=True)
    if not response:
        logger.error(f"Failed to download file from {url}")
        return False

    try:
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"Downloaded: {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving file {output_path}: {e}")
        return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing or replacing invalid characters

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    # Limit length
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200-len(ext)] + ext
    return filename


def normalize_text(text: str) -> str:
    """
    Normalize text by removing extra whitespace and newlines

    Args:
        text: Original text

    Returns:
        Normalized text
    """
    if not text:
        return ""
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    # Strip leading/trailing whitespace
    text = text.strip()
    return text


def parse_coupon_frequency(text: str) -> str:
    """
    Parse coupon frequency text to number

    Args:
        text: Coupon frequency description in Russian

    Returns:
        Number as string (1, 2, 4, 12, etc.) or original text if not found
    """
    if not text:
        return ""

    text_lower = text.lower().strip()

    # Try to find match in mapping
    for key, value in COUPON_FREQUENCY_MAPPING.items():
        if key in text_lower:
            return value

    # Try to extract number directly
    match = re.search(r'(\d+)', text)
    if match:
        return match.group(1)

    return text


def parse_boolean(text: str) -> str:
    """
    Parse boolean text to Yes/No

    Args:
        text: Boolean text in Russian

    Returns:
        "Yes", "No", or original text
    """
    if not text:
        return "No"

    text_lower = text.lower().strip()

    for key, value in BOOLEAN_MAPPING.items():
        if key in text_lower:
            return value

    return text


def parse_interest_payment_dates(text: str) -> tuple[str, str]:
    """
    Parse interest payment dates text

    Args:
        text: Interest payment dates description

    Returns:
        Tuple of (formatted dates, first payment date)
    """
    if not text:
        return "", ""

    # Extract dates in format "DD month"
    date_pattern = r'(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)'
    matches = re.findall(date_pattern, text.lower())

    month_mapping = {
        'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04',
        'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08',
        'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12'
    }

    formatted_dates = []
    for day, month in matches:
        month_num = month_mapping.get(month, '??')
        formatted_dates.append(f"{month_num}/{day.zfill(2)}")

    # Format as [MM/DD ; MM/DD]
    dates_str = "[" + " ; ".join(formatted_dates) + "]" if formatted_dates else ""

    # Extract first payment date (year)
    first_date = ""
    year_match = re.search(r'начиная с (\d{1,2})\s+(\w+)\s+(\d{4})', text.lower())
    if year_match:
        day, month, year = year_match.groups()
        month_num = month_mapping.get(month, '??')
        first_date = f"{month_num}/{day.zfill(2)}/{year}"

    return dates_str, first_date


def create_directory_structure(issuer_name: str, isin: str, base_dir: str) -> str:
    """
    Create directory structure for prospectus files

    Args:
        issuer_name: Issuer name
        isin: ISIN code
        base_dir: Base directory for prospectuses

    Returns:
        Full path to the directory
    """
    # Sanitize names
    issuer_dir = sanitize_filename(issuer_name)
    isin_dir = sanitize_filename(isin)

    # Create full path
    full_path = os.path.join(base_dir, issuer_dir, isin_dir)
    os.makedirs(full_path, exist_ok=True)

    return full_path


def extract_field_value(soup: BeautifulSoup, field_label: str, logger: logging.Logger) -> str:
    """
    Extract field value from HTML by label

    Args:
        soup: BeautifulSoup object
        field_label: Field label to search for
        logger: Logger instance

    Returns:
        Field value or empty string if not found
    """
    try:
        # Try multiple strategies to find the field

        # Strategy 1: Look for label in dt/dd structure
        dt_elements = soup.find_all(['dt', 'div', 'span', 'td'], string=re.compile(re.escape(field_label), re.IGNORECASE))
        for dt in dt_elements:
            # Check next sibling
            dd = dt.find_next_sibling(['dd', 'div', 'span', 'td'])
            if dd:
                value = normalize_text(dd.get_text())
                if value:
                    return value

            # Check parent's next sibling
            parent = dt.parent
            if parent:
                next_elem = parent.find_next_sibling()
                if next_elem:
                    value = normalize_text(next_elem.get_text())
                    if value:
                        return value

        # Strategy 2: Look for label in table rows
        rows = soup.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                label_text = normalize_text(cells[0].get_text())
                if field_label.lower() in label_text.lower():
                    return normalize_text(cells[1].get_text())

        return ""

    except Exception as e:
        logger.warning(f"Error extracting field '{field_label}': {e}")
        return ""
