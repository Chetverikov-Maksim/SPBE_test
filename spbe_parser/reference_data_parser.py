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
    get_html,
    normalize_text,
    parse_coupon_frequency,
    parse_boolean,
    parse_interest_payment_dates,
    extract_field_value,
    extract_json_from_nextjs_html,
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
        Get list of bonds from the securities list page using Next.js JSON extraction

        Returns:
            List of bonds with basic info (code, isin, issuer_name, url)
        """
        bonds = []
        page = 0
        max_pages = 200  # Safety limit

        self.logger.info("Fetching bonds list from SPBE using Next.js JSON extraction...")

        while page < max_pages:
            # Build URL with correct parameters format and bond filter
            # Using securityKind=Облигации to filter only bonds on server side
            url = f"{SPBE_SECURITIES_LIST_URL}?page={page}&size=100&sortBy=securityKind&sortByDirection=desc&securityKind=Облигации"

            self.logger.debug(f"Fetching page {page}: {url}")

            # Fetch HTML (uses Selenium if USE_SELENIUM is True)
            html = get_html(url, self.logger)
            if not html:
                self.logger.warning(f"Failed to fetch page {page}")
                break

            # Extract JSON from Next.js HTML
            page_data = extract_json_from_nextjs_html(html, self.logger)

            if not page_data:
                self.logger.warning(f"No Next.js data found on page {page}")
                break

            # Process bonds from content array
            content = page_data.get('content', [])
            if not content:
                self.logger.info(f"No content found on page {page}, stopping pagination")
                break

            page_bonds = 0
            for item in content:
                # Double-check that it's a bond (should be filtered by URL param already)
                security_kind = item.get('securityKind', '')
                if 'Облигац' not in security_kind:
                    self.logger.debug(f"Skipping non-bond: {security_kind}")
                    continue

                # Extract bond information
                security_code = item.get('srtsCode', '').strip()
                isin = item.get('sisinCode', '').strip()
                issuer_name = item.get('fullName', '').strip()

                if security_code:
                    bond_url = f"{SPBE_BASE_URL}/listing/securities/{security_code}/"
                    bonds.append({
                        'code': security_code,
                        'isin': isin,
                        'issuer_name': issuer_name,
                        'url': bond_url,
                    })
                    page_bonds += 1
                else:
                    self.logger.warning(f"Bond without security code: {item}")

            self.logger.info(f"Page {page}: found {page_bonds} bonds (total: {len(bonds)})")

            # Check pagination info
            total_pages = page_data.get('totalPages', 0)
            total_elements = page_data.get('totalElements', 0)

            self.logger.debug(f"Pagination: page {page + 1}/{total_pages}, total bonds: {total_elements}")

            # Check if this is the last page
            if page >= total_pages - 1:
                self.logger.info(f"Reached last page ({page + 1}/{total_pages})")
                break

            page += 1

        self.logger.info(f"Found {len(bonds)} bonds in total")
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
