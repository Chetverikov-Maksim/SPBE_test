#!/usr/bin/env python3
"""Test Next.js data extraction from SPBE"""

from spbe_parser.reference_data_parser import ReferenceDataParser

def main():
    print("\n" + "="*80)
    print("Testing Next.js Data Extraction")
    print("="*80 + "\n")

    parser = ReferenceDataParser()

    print("Fetching bonds list...")
    bonds = parser.get_bonds_list()

    print(f"\n✓ Found {len(bonds)} bonds")

    if bonds:
        print(f"\nFirst 5 bonds:")
        for i, bond in enumerate(bonds[:5], 1):
            print(f"  {i}. {bond['code']}: {bond['issuer_name']}")
            print(f"      ISIN: {bond['isin']}")
            print(f"      URL: {bond['url']}")
    else:
        print("\n✗ No bonds found - check debug output above")

    print("\n" + "="*80)
    print("Test completed")
    print("="*80)

if __name__ == "__main__":
    main()
