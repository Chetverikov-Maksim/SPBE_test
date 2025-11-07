"""
Foreign issuers prospectus parser for SPBE bonds
"""

import os
import re
from typing import List, Dict, Optional
from urllib.parse import urljoin

from .config import (
    SPBE_BASE_URL,
    PROSPECTUSES_DIR,
)
from .utils import (
    setup_logger,
    get_soup,
    download_file,
    create_directory_structure,
    normalize_text,
    extract_field_value,
)


class ForeignProspectusParser:
    """Parser for foreign issuers prospectus documents"""

    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize parser

        Args:
            log_file: Optional log file path
        """
        self.logger = setup_logger(__name__, log_file)
        self.downloaded_files: List[str] = []

    def get_foreign_bonds(self, bonds_list: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Filter bonds list to get only foreign issuers

        Args:
            bonds_list: Complete list of bonds

        Returns:
            List of foreign issuer bonds
        """
        foreign_bonds = []

        for bond in bonds_list:
            # Check if it's a foreign issuer bond
            # According to TZ: "Облигации иностранного эмитента"
            issuer_name = bond.get('issuer_name', '')
            code = bond.get('code', '')

            # We need to check the actual bond page to determine if it's foreign
            # For now, we'll pass all bonds and filter during detail parsing
            foreign_bonds.append(bond)

        return foreign_bonds

    def is_foreign_issuer(self, soup) -> bool:
        """
        Check if the bond is from a foreign issuer

        Args:
            soup: BeautifulSoup object of the bond page

        Returns:
            True if foreign issuer, False otherwise
        """
        # Look for "Облигации иностранного эмитента" in the page
        page_text = soup.get_text()

        if 'иностранного эмитента' in page_text.lower():
            return True

        # Also check the security category field
        security_category = extract_field_value(soup, "Вид, категория (тип) ценной бумаги", self.logger)
        if security_category and 'иностран' in security_category.lower():
            return True

        return False

    def parse_prospectus_links(self, bond_url: str) -> List[Dict[str, str]]:
        """
        Parse prospectus download links from bond page

        Args:
            bond_url: URL to bond details page

        Returns:
            List of prospectus documents with URLs and names
        """
        self.logger.debug(f"Parsing prospectus links from: {bond_url}")

        soup = get_soup(bond_url, self.logger)
        if not soup:
            self.logger.error(f"Failed to load bond page: {bond_url}")
            return []

        # Check if it's a foreign issuer
        if not self.is_foreign_issuer(soup):
            self.logger.debug(f"Not a foreign issuer: {bond_url}")
            return []

        prospectus_docs = []

        # Look for "Резюме проспекта ценных бумаг" section
        # Try to find the download link
        prospectus_keywords = [
            'резюме проспекта',
            'проспект ценных бумаг',
            'prospectus',
        ]

        # Find all links that might be prospectus documents
        all_links = soup.find_all('a', href=True)

        for link in all_links:
            link_text = normalize_text(link.get_text()).lower()
            href = link.get('href', '')

            # Check if link text contains prospectus keywords
            is_prospectus = any(keyword in link_text for keyword in prospectus_keywords)

            # Check if it's a PDF link
            is_pdf = href.lower().endswith('.pdf') or 'pdf' in link_text

            if is_prospectus or (is_pdf and any(kw in link_text for kw in ['документ', 'файл', 'скачать'])):
                # Get full URL
                full_url = urljoin(SPBE_BASE_URL, href) if not href.startswith('http') else href

                # Get filename from link text or URL
                filename = normalize_text(link.get_text())
                if not filename or len(filename) > 200:
                    # Extract filename from URL
                    filename = os.path.basename(href)

                # Ensure .pdf extension
                if not filename.lower().endswith('.pdf'):
                    filename += '.pdf'

                prospectus_docs.append({
                    'url': full_url,
                    'filename': filename,
                })

        # Also look in specific sections
        # Look for divs/sections with prospectus information
        prospectus_sections = soup.find_all(['div', 'section', 'tr'],
                                           string=re.compile('|'.join(prospectus_keywords), re.IGNORECASE))

        for section in prospectus_sections:
            # Find PDF links in this section and its siblings
            parent = section.parent if section.parent else section
            pdf_links = parent.find_all('a', href=re.compile(r'\.pdf$', re.IGNORECASE))

            for link in pdf_links:
                href = link.get('href', '')
                full_url = urljoin(SPBE_BASE_URL, href) if not href.startswith('http') else href

                # Check if already added
                if not any(doc['url'] == full_url for doc in prospectus_docs):
                    filename = normalize_text(link.get_text()) or os.path.basename(href)
                    if not filename.lower().endswith('.pdf'):
                        filename += '.pdf'

                    prospectus_docs.append({
                        'url': full_url,
                        'filename': filename,
                    })

        self.logger.info(f"Found {len(prospectus_docs)} prospectus documents")
        return prospectus_docs

    def download_prospectus(self, bond: Dict[str, str], prospectus_docs: List[Dict[str, str]]) -> int:
        """
        Download prospectus documents for a bond

        Args:
            bond: Bond information dictionary
            prospectus_docs: List of prospectus documents to download

        Returns:
            Number of successfully downloaded files
        """
        if not prospectus_docs:
            return 0

        # Get issuer name and ISIN
        issuer_name = bond.get('issuer_name', 'Unknown')
        isin = bond.get('isin', bond.get('code', 'Unknown'))

        # Create directory structure
        output_dir = create_directory_structure(issuer_name, isin, PROSPECTUSES_DIR)

        downloaded_count = 0

        for doc in prospectus_docs:
            url = doc['url']
            filename = doc['filename']

            # Full output path
            output_path = os.path.join(output_dir, filename)

            # Download file (skip if already exists)
            if download_file(url, output_path, self.logger, force=False):
                downloaded_count += 1
                self.downloaded_files.append(output_path)

        return downloaded_count

    def parse_all_prospectuses(self, bonds_list: List[Dict[str, str]]) -> int:
        """
        Parse and download prospectuses for all foreign issuer bonds

        Args:
            bonds_list: List of bonds to process

        Returns:
            Total number of downloaded files
        """
        total_downloaded = 0
        total = len(bonds_list)

        self.logger.info(f"Starting to parse prospectuses for {total} bonds...")

        for i, bond in enumerate(bonds_list, 1):
            code = bond.get('code', 'Unknown')
            self.logger.info(f"Processing bond {i}/{total}: {code}")

            try:
                # Parse prospectus links
                prospectus_docs = self.parse_prospectus_links(bond['url'])

                if prospectus_docs:
                    # Download prospectuses
                    downloaded = self.download_prospectus(bond, prospectus_docs)
                    total_downloaded += downloaded
                    self.logger.info(f"Downloaded {downloaded} prospectus files for {code}")
                else:
                    self.logger.debug(f"No prospectus documents found for {code}")

            except Exception as e:
                self.logger.error(f"Error processing bond {code}: {e}", exc_info=True)

        self.logger.info(f"Total prospectus files downloaded: {total_downloaded}")
        return total_downloaded

    def run(self, bonds_list: List[Dict[str, str]]) -> int:
        """
        Run the complete foreign prospectus parsing process

        Args:
            bonds_list: List of bonds to process

        Returns:
            Total number of downloaded files
        """
        self.logger.info("Starting foreign issuers prospectus parser")

        try:
            # Parse and download all prospectuses
            total_downloaded = self.parse_all_prospectuses(bonds_list)

            self.logger.info(f"Foreign prospectus parsing completed. Downloaded {total_downloaded} files")
            return total_downloaded

        except Exception as e:
            self.logger.error(f"Fatal error in foreign prospectus parser: {e}", exc_info=True)
            return 0


def main():
    """Main entry point for standalone execution"""
    # This would typically be called with bonds_list from reference data parser
    parser = ForeignProspectusParser(log_file='foreign_prospectus_parser.log')
    print("Foreign prospectus parser initialized. Use run() with bonds_list parameter.")


if __name__ == "__main__":
    main()
