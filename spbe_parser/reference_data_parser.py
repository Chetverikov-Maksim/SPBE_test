"""
Reference data parser for SPBE bonds
"""

import csv
import json
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

from .config import (
    SPBE_BASE_URL,
    SPBE_SECURITIES_LIST_URL,
    REFERENCE_DATA_DIR,
    FIELD_MAPPING,
    ADDITIONAL_FIELDS,
    get_reference_data_filename,
)
from .utils import (
    setup_logger,
    make_request,
    get_soup,
    normalize_text,
    parse_coupon_frequency,
    parse_boolean,
    parse_interest_payment_dates,
    extract_field_value,
)


class ReferenceDataParser:
    """Parser for SPBE reference data"""

    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize parser

        Args:
            log_file: Optional log file path
        """
        self.logger = setup_logger(__name__, log_file)
        self.bonds_data: List[Dict[str, Any]] = []

    def get_bonds_list(self) -> List[Dict[str, str]]:
        """
        Get list of bonds from the securities list page

        Returns:
            List of bonds with basic info (code, link)
        """
        bonds = []
        page = 0

        self.logger.info("Fetching bonds list from SPBE...")

        while True:
            # API endpoint for securities list (assuming it uses an API)
            # We'll need to check the actual implementation
            url = f"{SPBE_SECURITIES_LIST_URL}?page={page}&size=100"

            self.logger.debug(f"Fetching page {page}: {url}")

            # Try API approach first
            api_url = f"{SPBE_BASE_URL}/ru/listing/securities/api/securities"
            params = {
                'page': page,
                'size': 100,
                'sortBy': 'securityKind',
                'sortByDirection': 'desc',
                'securityKind': 'Облигация'  # Filter for bonds
            }

            response = make_request(api_url, self.logger, params=params)

            if response:
                try:
                    data = response.json()

                    # Extract bonds from response
                    if 'content' in data and isinstance(data['content'], list):
                        for item in data['content']:
                            security_code = item.get('securitySymbol', '')
                            isin = item.get('isin', '')
                            issuer_name = item.get('issuerName', '')

                            if security_code:
                                bond_url = f"{SPBE_BASE_URL}/listing/securities/{security_code}/"
                                bonds.append({
                                    'code': security_code,
                                    'isin': isin,
                                    'issuer_name': issuer_name,
                                    'url': bond_url,
                                })

                        # Check if there are more pages
                        if data.get('last', True):
                            break

                        page += 1
                    else:
                        self.logger.warning("Unexpected API response format")
                        break

                except (json.JSONDecodeError, KeyError) as e:
                    self.logger.error(f"Error parsing API response: {e}")
                    # Try HTML parsing fallback
                    bonds = self._get_bonds_list_html()
                    break
            else:
                # Fallback to HTML parsing
                self.logger.info("API request failed, trying HTML parsing...")
                bonds = self._get_bonds_list_html()
                break

        self.logger.info(f"Found {len(bonds)} bonds")
        return bonds

    def _get_bonds_list_html(self) -> List[Dict[str, str]]:
        """
        Fallback method to get bonds list from HTML with pagination

        Returns:
            List of bonds with basic info
        """
        bonds = []
        seen_codes = set()
        page = 0
        max_pages = 100  # Safety limit

        self.logger.info("Using HTML parsing to fetch bonds...")

        while page < max_pages:
            # Construct URL with page parameter
            url = f"{SPBE_SECURITIES_LIST_URL}?page={page}&size=100"
            self.logger.debug(f"Fetching HTML page {page}: {url}")

            soup = get_soup(url, self.logger)

            if not soup:
                self.logger.warning(f"Failed to fetch page {page}")
                break

            # Find all security links in the table
            # Look for table rows with security information
            page_bonds = []

            # Try multiple selectors to find bonds
            # Method 1: Find all links to securities pages
            security_links = soup.find_all('a', href=re.compile(r'/listing/securities/[A-Z0-9]+/?$'))

            for link in security_links:
                code = link.get_text(strip=True)
                href = link.get('href', '')

                # Skip if already seen
                if code in seen_codes:
                    continue

                # Extract security code from href
                match = re.search(r'/listing/securities/([A-Z0-9]+)/?$', href)
                if not match:
                    continue

                security_code = match.group(1)
                url = urljoin(SPBE_BASE_URL, href)

                # Try to determine if it's a bond by looking at the row context
                # Find parent row
                parent_row = link.find_parent('tr')
                is_bond = False

                if parent_row:
                    row_text = parent_row.get_text().lower()
                    # Check if row contains "облигация" or "bond"
                    if 'облигац' in row_text or 'bond' in row_text:
                        is_bond = True
                    # Check for bond patterns (usually have specific naming)
                    elif re.search(r'(бо-|облигац)', security_code, re.IGNORECASE):
                        is_bond = True
                else:
                    # If no parent row found, we'll check all securities
                    # and filter later in parse_bond_details
                    is_bond = True  # Assume it might be a bond

                if is_bond or True:  # For now, fetch all and filter during detail parsing
                    page_bonds.append({
                        'code': security_code,
                        'isin': '',
                        'issuer_name': '',
                        'url': url,
                    })
                    seen_codes.add(code)

            if not page_bonds:
                self.logger.info(f"No more securities found on page {page}, stopping pagination")
                break

            bonds.extend(page_bonds)
            self.logger.info(f"Page {page}: found {len(page_bonds)} securities (total: {len(bonds)})")

            # Check if there's a next page
            # Look for pagination controls
            next_button = soup.find('a', text=re.compile(r'next|след|›|»', re.IGNORECASE))
            if not next_button or 'disabled' in next_button.get('class', []):
                self.logger.info("No next page found, stopping pagination")
                break

            page += 1

        self.logger.info(f"HTML parsing complete: found {len(bonds)} securities total")
        return bonds

    def parse_bond_details(self, bond_url: str) -> Dict[str, str]:
        """
        Parse detailed information for a single bond

        Args:
            bond_url: URL to bond details page

        Returns:
            Dictionary with bond data in English field names, or empty dict if not a bond
        """
        self.logger.debug(f"Parsing bond details: {bond_url}")

        soup = get_soup(bond_url, self.logger)
        if not soup:
            self.logger.error(f"Failed to load bond page: {bond_url}")
            return {}

        # First, check if this is actually a bond
        security_category = extract_field_value(soup, "Вид, категория (тип) ценной бумаги", self.logger)

        # Filter: only process if it's a bond (облигация)
        if security_category:
            category_lower = security_category.lower()
            if 'облигац' not in category_lower and 'bond' not in category_lower:
                self.logger.debug(f"Skipping non-bond security: {security_category}")
                return {}

        # Also check page content for bond indicators
        page_text = soup.get_text().lower()
        if 'облигац' not in page_text and 'bond' not in page_text:
            # Likely not a bond page
            self.logger.debug(f"Page does not appear to be a bond (no bond keywords found)")
            return {}

        bond_data = {}

        # Extract all fields according to the mapping
        for russian_field, english_field in FIELD_MAPPING.items():
            value = extract_field_value(soup, russian_field, self.logger)

            # Apply special processing for certain fields
            if english_field == "Coupon Frequency":
                value = parse_coupon_frequency(value)
            elif english_field in ["Early Redemption Option", "Trading Restrictions (incl. qualified investors)",
                                   "Included in the exchange index universe"]:
                value = parse_boolean(value)
            elif english_field == "Interest Payment Dates":
                dates_str, first_date = parse_interest_payment_dates(value)
                bond_data[english_field] = dates_str
                bond_data["First Payment Date"] = first_date
                continue

            bond_data[english_field] = value

        return bond_data

    def parse_all_bonds(self, bonds_list: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
        """
        Parse all bonds and collect reference data

        Args:
            bonds_list: Optional list of bonds to parse. If None, will fetch automatically.

        Returns:
            List of bond data dictionaries
        """
        if bonds_list is None:
            bonds_list = self.get_bonds_list()

        self.bonds_data = []
        total = len(bonds_list)

        self.logger.info(f"Starting to parse {total} bonds...")

        for i, bond in enumerate(bonds_list, 1):
            self.logger.info(f"Processing bond {i}/{total}: {bond['code']}")

            try:
                bond_details = self.parse_bond_details(bond['url'])
                if bond_details:
                    # Add basic info from list
                    bond_details['Security Symbol'] = bond['code']
                    self.bonds_data.append(bond_details)
                else:
                    self.logger.warning(f"No data extracted for bond {bond['code']}")

            except Exception as e:
                self.logger.error(f"Error parsing bond {bond['code']}: {e}", exc_info=True)

        self.logger.info(f"Successfully parsed {len(self.bonds_data)} bonds")
        return self.bonds_data

    def save_to_csv(self, output_path: Optional[str] = None) -> str:
        """
        Save parsed data to CSV file

        Args:
            output_path: Optional custom output path. If None, uses default naming.

        Returns:
            Path to saved file
        """
        if not self.bonds_data:
            self.logger.warning("No data to save")
            return ""

        if output_path is None:
            output_path = f"{REFERENCE_DATA_DIR}/{get_reference_data_filename()}"

        self.logger.info(f"Saving data to {output_path}")

        # Get all unique field names
        all_fields = set()
        for bond in self.bonds_data:
            all_fields.update(bond.keys())

        # Order fields: common fields first, then the rest
        ordered_fields = ['Security Symbol', 'ISIN', 'Full Name Issuer']
        ordered_fields.extend([f for f in FIELD_MAPPING.values() if f not in ordered_fields])
        ordered_fields.extend(ADDITIONAL_FIELDS)

        # Filter to only fields that exist in data
        fieldnames = [f for f in ordered_fields if f in all_fields]
        # Add any remaining fields
        fieldnames.extend([f for f in all_fields if f not in fieldnames])

        try:
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(self.bonds_data)

            self.logger.info(f"Successfully saved {len(self.bonds_data)} bonds to {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Error saving CSV file: {e}", exc_info=True)
            return ""

    def run(self) -> str:
        """
        Run the complete reference data parsing process

        Returns:
            Path to output CSV file
        """
        self.logger.info("Starting reference data parser")

        try:
            # Get bonds list
            bonds_list = self.get_bonds_list()

            if not bonds_list:
                self.logger.error("No bonds found")
                return ""

            # Parse all bonds
            self.parse_all_bonds(bonds_list)

            # Save to CSV
            output_path = self.save_to_csv()

            self.logger.info("Reference data parsing completed successfully")
            return output_path

        except Exception as e:
            self.logger.error(f"Fatal error in reference data parser: {e}", exc_info=True)
            return ""


def main():
    """Main entry point for standalone execution"""
    parser = ReferenceDataParser(log_file='reference_data_parser.log')
    output_file = parser.run()

    if output_file:
        print(f"Reference data saved to: {output_file}")
    else:
        print("Reference data parsing failed")


if __name__ == "__main__":
    main()
