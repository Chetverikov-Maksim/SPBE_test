"""
Simple test to parse one specific bond and show all extracted dates
"""

import sys
sys.path.insert(0, '/home/user/SPBE_test')

from spbe_parser import SPBEParser
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Bond XS2063279959
BOND_URL = "https://spbexchange.ru/listing/securities/card_bond/?issue=6198"

parser = SPBEParser(headless=True)
parser.setup_browser()

logger.info(f"Parsing bond: {BOND_URL}")
bond_data = parser.parse_bond_details(BOND_URL)

logger.info("\n" + "="*80)
logger.info("EXTRACTED BOND DATA")
logger.info("="*80)

# Show all date fields
date_fields = ['Issue Date', 'Maturity Date', 'Decision date to include in the List',
               'Listing Inclusion Date', 'Start Date Organized Trading', 'Interest Payment Dates']

for field in date_fields:
    value = bond_data.get(field, 'NOT FOUND')
    logger.info(f"{field}: {value}")

logger.info("\n" + "="*80)
logger.info("ALL FIELDS")
logger.info("="*80)

for key, value in sorted(bond_data.items()):
    logger.info(f"{key}: {value}")

parser.close_browser()
