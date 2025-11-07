"""
Main entry point for SPBE parsers
"""

import os
import sys
import argparse
from datetime import datetime
from typing import Optional

from .reference_data_parser import ReferenceDataParser
from .foreign_prospectus_parser import ForeignProspectusParser
from .russian_prospectus_parser import RussianProspectusParser
from .config import OUTPUT_DIR, PROSPECTUSES_DIR
from .utils import setup_logger


def ensure_directories():
    """Ensure output directories exist"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(PROSPECTUSES_DIR, exist_ok=True)


def run_reference_data_parser(log_file: Optional[str] = None) -> tuple[bool, str]:
    """
    Run reference data parser

    Args:
        log_file: Optional log file path

    Returns:
        Tuple of (success, output_file_path)
    """
    print("\n" + "="*80)
    print("STARTING REFERENCE DATA PARSER")
    print("="*80 + "\n")

    parser = ReferenceDataParser(log_file=log_file)
    output_file = parser.run()

    success = bool(output_file and os.path.exists(output_file))

    if success:
        print(f"\n✓ Reference data parser completed successfully")
        print(f"  Output file: {output_file}")
        print(f"  Total bonds: {len(parser.bonds_data)}")
    else:
        print("\n✗ Reference data parser failed")

    return success, output_file


def run_foreign_prospectus_parser(bonds_list: list, log_file: Optional[str] = None) -> bool:
    """
    Run foreign prospectus parser

    Args:
        bonds_list: List of bonds from reference data parser
        log_file: Optional log file path

    Returns:
        Success status
    """
    print("\n" + "="*80)
    print("STARTING FOREIGN PROSPECTUS PARSER")
    print("="*80 + "\n")

    parser = ForeignProspectusParser(log_file=log_file)
    total_files = parser.run(bonds_list)

    success = total_files > 0

    if success:
        print(f"\n✓ Foreign prospectus parser completed successfully")
        print(f"  Total files downloaded: {total_files}")
    else:
        print("\n⚠ Foreign prospectus parser completed with no files downloaded")

    return success


def run_russian_prospectus_parser(include_cancelled: bool = False, log_file: Optional[str] = None) -> bool:
    """
    Run Russian prospectus parser

    Args:
        include_cancelled: Include cancelled bonds
        log_file: Optional log file path

    Returns:
        Success status
    """
    print("\n" + "="*80)
    print("STARTING RUSSIAN PROSPECTUS PARSER")
    print("="*80 + "\n")

    parser = RussianProspectusParser(log_file=log_file, include_cancelled=include_cancelled)
    total_files = parser.run()

    success = total_files > 0

    if success:
        print(f"\n✓ Russian prospectus parser completed successfully")
        print(f"  Total files downloaded: {total_files}")
    else:
        print("\n⚠ Russian prospectus parser completed with no files downloaded")

    return success


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='SPBE Bond Data Parser',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all parsers
  python -m spbe_parser.main --all

  # Run only reference data parser
  python -m spbe_parser.main --reference-data

  # Run only prospectus parsers
  python -m spbe_parser.main --prospectus

  # Run Russian prospectus parser with cancelled bonds (first run)
  python -m spbe_parser.main --russian-prospectus --include-cancelled

  # Run specific parsers
  python -m spbe_parser.main --reference-data --foreign-prospectus
        """
    )

    parser.add_argument('--all', action='store_true',
                       help='Run all parsers (reference data + prospectus)')

    parser.add_argument('--reference-data', action='store_true',
                       help='Run reference data parser')

    parser.add_argument('--prospectus', action='store_true',
                       help='Run both prospectus parsers (foreign + Russian)')

    parser.add_argument('--foreign-prospectus', action='store_true',
                       help='Run foreign prospectus parser')

    parser.add_argument('--russian-prospectus', action='store_true',
                       help='Run Russian prospectus parser')

    parser.add_argument('--include-cancelled', action='store_true',
                       help='Include cancelled bonds (for Russian parser, use on first run)')

    parser.add_argument('--log-file', type=str,
                       help='Custom log file path (default: auto-generated)')

    parser.add_argument('--no-log-file', action='store_true',
                       help='Do not write to log file, only console output')

    args = parser.parse_args()

    # If no specific parser selected, show help
    if not any([args.all, args.reference_data, args.prospectus,
                args.foreign_prospectus, args.russian_prospectus]):
        parser.print_help()
        sys.exit(1)

    # Set up logging
    if args.no_log_file:
        log_file = None
    elif args.log_file:
        log_file = args.log_file
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(OUTPUT_DIR, f"spbe_parser_{timestamp}.log")

    # Ensure directories exist
    ensure_directories()

    # Print header
    print("\n" + "="*80)
    print("SPBE BOND DATA PARSER")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if log_file:
        print(f"Log file: {log_file}")
    print("="*80)

    # Determine what to run
    run_ref_data = args.all or args.reference_data
    run_foreign = args.all or args.prospectus or args.foreign_prospectus
    run_russian = args.all or args.prospectus or args.russian_prospectus

    results = {}
    bonds_list = []

    # Run reference data parser
    if run_ref_data:
        success, output_file = run_reference_data_parser(log_file)
        results['reference_data'] = success

        # Load bonds list for prospectus parsers
        if success:
            ref_parser = ReferenceDataParser()
            bonds_list = ref_parser.bonds_data if ref_parser.bonds_data else []

    # If prospectus parsers requested but no bonds_list, fetch it
    if (run_foreign or run_russian) and not bonds_list and not run_ref_data:
        print("\nFetching bonds list for prospectus parsers...")
        ref_parser = ReferenceDataParser(log_file=log_file)
        bonds_list = ref_parser.get_bonds_list()

    # Run foreign prospectus parser
    if run_foreign:
        if bonds_list:
            success = run_foreign_prospectus_parser(bonds_list, log_file)
            results['foreign_prospectus'] = success
        else:
            print("\n✗ Cannot run foreign prospectus parser: no bonds list available")
            results['foreign_prospectus'] = False

    # Run Russian prospectus parser
    if run_russian:
        success = run_russian_prospectus_parser(args.include_cancelled, log_file)
        results['russian_prospectus'] = success

    # Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    for parser_name, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"{parser_name:30s}: {status}")

    print("\n" + "="*80)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")

    # Exit with appropriate code
    if all(results.values()):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
