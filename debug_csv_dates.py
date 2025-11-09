"""
Debug script to track what happens to dates from parsing to CSV
"""

import sys
sys.path.insert(0, '/home/user/SPBE_test')

from spbe_parser import SPBEParser
import logging
import csv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test with one bond
BOND_URL = "https://spbexchange.ru/listing/securities/card_bond/?issue=7563"  # XS2063279959

parser = SPBEParser(headless=True)
parser.setup_browser()

logger.info("="*80)
logger.info("STEP 1: Parse bond from HTML")
logger.info("="*80)

bond_data = parser.parse_bond_details(BOND_URL)

# Show dates immediately after parsing
logger.info("\nDates immediately after parsing:")
date_fields = ['Issue Date', 'Maturity Date', 'Decision date to include in the List',
               'Listing Inclusion Date', 'Start Date Organized Trading']

for field in date_fields:
    value = bond_data.get(field, 'NOT FOUND')
    logger.info(f"  {field}: {value}")
    logger.info(f"    Type: {type(value)}")
    logger.info(f"    Repr: {repr(value)}")

logger.info("\n" + "="*80)
logger.info("STEP 2: Save to CSV using parser method")
logger.info("="*80)

# Save using parser's method
parser.save_to_csv([bond_data], filename='test_dates.csv')
logger.info("Saved to test_dates.csv")

logger.info("\n" + "="*80)
logger.info("STEP 3: Read back from CSV")
logger.info("="*80)

# Read back from CSV
with open('test_dates.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        logger.info("\nDates read back from CSV:")
        for field in date_fields:
            value = row.get(field, 'NOT FOUND')
            logger.info(f"  {field}: {value}")

logger.info("\n" + "="*80)
logger.info("STEP 4: Check raw CSV content")
logger.info("="*80)

with open('test_dates.csv', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    logger.info(f"Total lines in CSV: {len(lines)}")

    # Find Issue Date column
    header = lines[0].strip().split(',')
    logger.info(f"\nHeader has {len(header)} columns")

    if 'Issue Date' in header:
        idx = header.index('Issue Date')
        logger.info(f"'Issue Date' is column #{idx}")

        if len(lines) > 1:
            data_row = lines[1].strip().split(',')
            if idx < len(data_row):
                logger.info(f"Raw value in CSV: '{data_row[idx]}'")

parser.close_browser()

logger.info("\n" + "="*80)
logger.info("Debug completed. Check test_dates.csv file")
logger.info("="*80)
