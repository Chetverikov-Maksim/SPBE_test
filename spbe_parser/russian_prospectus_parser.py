"""
Russian issuers prospectus parser for SPBE bonds
"""

import os
import re
from typing import List, Dict, Optional
from urllib.parse import urljoin

from .config import (
    SPBE_ISSUERS_URL,
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


class RussianProspectusParser:
    """Parser for Russian issuers prospectus documents"""

    def __init__(self, log_file: Optional[str] = None, include_cancelled: bool = False):
        """
        Initialize parser

        Args:
            log_file: Optional log file path
            include_cancelled: Include cancelled bonds (first run should be True)
        """
        self.logger = setup_logger(__name__, log_file)
        self.include_cancelled = include_cancelled
        self.downloaded_files: List[str] = []

    def get_issuers_list(self) -> List[Dict[str, str]]:
        """
        Get list of Russian issuers from the issuers page

        Returns:
            List of issuers with name and URL
        """
        self.logger.info(f"Fetching issuers list from {SPBE_ISSUERS_URL}")

        soup = get_soup(SPBE_ISSUERS_URL, self.logger)
        if not soup:
            self.logger.error("Failed to load issuers page")
            return []

        issuers = []

        # Find all issuer links
        # The actual selector needs to be adjusted based on the page structure
        issuer_links = soup.find_all('a', href=re.compile(r'/issuers/[^/]+/?$'))

        for link in issuer_links:
            issuer_name = normalize_text(link.get_text())
            issuer_url = urljoin(SPBE_ISSUERS_URL, link.get('href', ''))

            if issuer_name and issuer_url:
                issuers.append({
                    'name': issuer_name,
                    'url': issuer_url,
                })

        # Alternative: look for issuer cards/blocks
        if not issuers:
            issuer_cards = soup.find_all(['div', 'li'], class_=re.compile(r'issuer|company', re.IGNORECASE))
            for card in issuer_cards:
                link = card.find('a', href=True)
                if link:
                    issuer_name = normalize_text(link.get_text())
                    issuer_url = urljoin(SPBE_ISSUERS_URL, link.get('href', ''))
                    if issuer_name and issuer_url:
                        issuers.append({
                            'name': issuer_name,
                            'url': issuer_url,
                        })

        self.logger.info(f"Found {len(issuers)} issuers")
        return issuers

    def get_issuer_bonds(self, issuer_url: str) -> List[Dict[str, str]]:
        """
        Get list of bonds for a specific issuer

        Args:
            issuer_url: URL to issuer page

        Returns:
            List of bonds with URL and other info
        """
        self.logger.debug(f"Fetching bonds for issuer: {issuer_url}")

        soup = get_soup(issuer_url, self.logger)
        if not soup:
            return []

        bonds = []

        # Look for bonds section/tab
        # Try to find and click on "Облигации" tab if needed
        bonds_section = soup.find(['a', 'button', 'div'], string=re.compile(r'облигации', re.IGNORECASE))

        if bonds_section:
            # If it's a link to bonds page
            if bonds_section.name == 'a' and bonds_section.get('href'):
                bonds_url = urljoin(issuer_url, bonds_section.get('href'))
                soup = get_soup(bonds_url, self.logger)
                if not soup:
                    return []

        # Find all bond entries
        # Look for table rows or cards with bond information
        bond_rows = soup.find_all('tr', class_=re.compile(r'bond|security', re.IGNORECASE))

        if not bond_rows:
            # Alternative: look for any table rows in bonds section
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')[1:]  # Skip header
                bond_rows.extend(rows)

        for row in bond_rows:
            # Extract bond information
            cells = row.find_all(['td', 'th'])

            # Look for bond link
            bond_link = row.find('a', href=re.compile(r'/bonds?/|/securities?/'))

            if bond_link:
                bond_url = urljoin(issuer_url, bond_link.get('href', ''))
                bond_name = normalize_text(bond_link.get_text())

                bonds.append({
                    'name': bond_name,
                    'url': bond_url,
                })

        # Check if we need to show cancelled bonds
        if self.include_cancelled:
            # Look for "Показать аннулированные" button/link
            show_cancelled = soup.find(['a', 'button'], string=re.compile(r'показать.*аннулированные', re.IGNORECASE))
            if show_cancelled and show_cancelled.get('href'):
                cancelled_url = urljoin(issuer_url, show_cancelled.get('href'))
                # Fetch cancelled bonds
                cancelled_soup = get_soup(cancelled_url, self.logger)
                if cancelled_soup:
                    # Parse cancelled bonds similarly
                    cancelled_rows = cancelled_soup.find_all('tr', class_=re.compile(r'bond|security', re.IGNORECASE))
                    for row in cancelled_rows:
                        bond_link = row.find('a', href=re.compile(r'/bonds?/|/securities?/'))
                        if bond_link:
                            bond_url = urljoin(issuer_url, bond_link.get('href', ''))
                            bond_name = normalize_text(bond_link.get_text())
                            bonds.append({
                                'name': bond_name,
                                'url': bond_url,
                            })

        self.logger.debug(f"Found {len(bonds)} bonds for issuer")
        return bonds

    def get_bond_documents(self, bond_url: str) -> tuple[List[Dict[str, str]], str]:
        """
        Get list of documents for a specific bond

        Args:
            bond_url: URL to bond page

        Returns:
            Tuple of (list of documents with URLs, ISIN code)
        """
        self.logger.debug(f"Fetching documents for bond: {bond_url}")

        soup = get_soup(bond_url, self.logger)
        if not soup:
            return [], ""

        documents = []

        # Find all document links (PDFs and other formats)
        doc_links = soup.find_all('a', href=re.compile(r'\.(pdf|doc|docx|xls|xlsx)$', re.IGNORECASE))

        for link in doc_links:
            doc_url = urljoin(bond_url, link.get('href', ''))
            doc_name = normalize_text(link.get_text())

            # If doc_name is empty, extract from URL
            if not doc_name:
                doc_name = os.path.basename(link.get('href', ''))

            documents.append({
                'url': doc_url,
                'filename': doc_name,
            })

        # Also look for documents in a documents section/table
        doc_sections = soup.find_all(['div', 'section', 'table'], class_=re.compile(r'document|файл', re.IGNORECASE))
        for section in doc_sections:
            links = section.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                # Check if it's a document
                if re.search(r'\.(pdf|doc|docx|xls|xlsx)$', href, re.IGNORECASE):
                    doc_url = urljoin(bond_url, href)
                    # Check if already added
                    if not any(d['url'] == doc_url for d in documents):
                        doc_name = normalize_text(link.get_text()) or os.path.basename(href)
                        documents.append({
                            'url': doc_url,
                            'filename': doc_name,
                        })

        # Extract ISIN from the page (usually at the bottom of the table)
        isin = ""

        # Look for ISIN in the page text
        isin_patterns = [
            r'ISIN[:\s]+([A-Z]{2}[A-Z0-9]{10})',
            r'ISIN код[:\s]+([A-Z]{2}[A-Z0-9]{10})',
            r'([A-Z]{2}[A-Z0-9]{10})'  # Generic ISIN pattern
        ]

        page_text = soup.get_text()
        for pattern in isin_patterns:
            match = re.search(pattern, page_text)
            if match:
                potential_isin = match.group(1) if len(match.groups()) > 0 else match.group(0)
                # Validate ISIN format
                if re.match(r'^[A-Z]{2}[A-Z0-9]{10}$', potential_isin):
                    isin = potential_isin
                    break

        # Alternative: look in tables at the bottom
        if not isin:
            tables = soup.find_all('table')
            for table in tables[-3:]:  # Check last 3 tables
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    for i, cell in enumerate(cells):
                        cell_text = cell.get_text()
                        if 'isin' in cell_text.lower() and i + 1 < len(cells):
                            isin_value = normalize_text(cells[i + 1].get_text())
                            if re.match(r'^[A-Z]{2}[A-Z0-9]{10}$', isin_value):
                                isin = isin_value
                                break

        self.logger.info(f"Found {len(documents)} documents for bond (ISIN: {isin})")
        return documents, isin

    def download_bond_documents(self, issuer_name: str, isin: str, documents: List[Dict[str, str]]) -> int:
        """
        Download documents for a bond

        Args:
            issuer_name: Issuer name
            isin: ISIN code
            documents: List of documents to download

        Returns:
            Number of successfully downloaded files
        """
        if not documents or not isin:
            return 0

        # Create directory structure
        output_dir = create_directory_structure(issuer_name, isin, PROSPECTUSES_DIR)

        downloaded_count = 0

        for doc in documents:
            url = doc['url']
            filename = doc['filename']

            # Ensure proper extension
            if not any(filename.lower().endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx']):
                # Try to get extension from URL
                url_ext = os.path.splitext(url)[1]
                if url_ext:
                    filename += url_ext

            # Full output path
            output_path = os.path.join(output_dir, filename)

            # Download file (skip if already exists)
            if download_file(url, output_path, self.logger, force=False):
                downloaded_count += 1
                self.downloaded_files.append(output_path)

        return downloaded_count

    def parse_issuer(self, issuer: Dict[str, str]) -> int:
        """
        Parse all bonds and documents for a single issuer

        Args:
            issuer: Issuer information dictionary

        Returns:
            Number of downloaded files
        """
        issuer_name = issuer['name']
        issuer_url = issuer['url']

        self.logger.info(f"Processing issuer: {issuer_name}")

        total_downloaded = 0

        try:
            # Get bonds for this issuer
            bonds = self.get_issuer_bonds(issuer_url)

            if not bonds:
                self.logger.warning(f"No bonds found for issuer {issuer_name}")
                return 0

            self.logger.info(f"Found {len(bonds)} bonds for {issuer_name}")

            # Process each bond
            for i, bond in enumerate(bonds, 1):
                bond_name = bond['name']
                bond_url = bond['url']

                self.logger.info(f"Processing bond {i}/{len(bonds)}: {bond_name}")

                try:
                    # Get documents for this bond
                    documents, isin = self.get_bond_documents(bond_url)

                    if not isin:
                        self.logger.warning(f"No ISIN found for bond {bond_name}, using bond name as fallback")
                        isin = bond_name[:20]  # Use truncated bond name

                    if documents:
                        # Download documents
                        downloaded = self.download_bond_documents(issuer_name, isin, documents)
                        total_downloaded += downloaded
                        self.logger.info(f"Downloaded {downloaded} documents for {bond_name}")
                    else:
                        self.logger.warning(f"No documents found for bond {bond_name}")

                except Exception as e:
                    self.logger.error(f"Error processing bond {bond_name}: {e}", exc_info=True)

        except Exception as e:
            self.logger.error(f"Error processing issuer {issuer_name}: {e}", exc_info=True)

        return total_downloaded

    def parse_all_issuers(self) -> int:
        """
        Parse all Russian issuers and their bonds

        Returns:
            Total number of downloaded files
        """
        # Get issuers list
        issuers = self.get_issuers_list()

        if not issuers:
            self.logger.error("No issuers found")
            return 0

        total_downloaded = 0
        total = len(issuers)

        self.logger.info(f"Starting to parse {total} issuers...")

        for i, issuer in enumerate(issuers, 1):
            self.logger.info(f"Processing issuer {i}/{total}: {issuer['name']}")

            try:
                downloaded = self.parse_issuer(issuer)
                total_downloaded += downloaded

            except Exception as e:
                self.logger.error(f"Error processing issuer {issuer['name']}: {e}", exc_info=True)

        self.logger.info(f"Total documents downloaded: {total_downloaded}")
        return total_downloaded

    def run(self) -> int:
        """
        Run the complete Russian prospectus parsing process

        Returns:
            Total number of downloaded files
        """
        self.logger.info("Starting Russian issuers prospectus parser")
        self.logger.info(f"Include cancelled bonds: {self.include_cancelled}")

        try:
            total_downloaded = self.parse_all_issuers()

            self.logger.info(f"Russian prospectus parsing completed. Downloaded {total_downloaded} files")
            return total_downloaded

        except Exception as e:
            self.logger.error(f"Fatal error in Russian prospectus parser: {e}", exc_info=True)
            return 0


def main():
    """Main entry point for standalone execution"""
    import argparse

    parser = argparse.ArgumentParser(description='Russian issuers prospectus parser')
    parser.add_argument('--include-cancelled', action='store_true',
                       help='Include cancelled bonds (use on first run)')
    args = parser.parse_args()

    prospectus_parser = RussianProspectusParser(
        log_file='russian_prospectus_parser.log',
        include_cancelled=args.include_cancelled
    )
    total_files = prospectus_parser.run()

    print(f"Russian prospectus parsing completed. Downloaded {total_files} files")


if __name__ == "__main__":
    main()
