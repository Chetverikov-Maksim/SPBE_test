#!/usr/bin/env python3
"""Unit test for Next.js extraction fix"""

import logging
from spbe_parser.utils import extract_json_from_nextjs_html, setup_logger

# Sample HTML with Next.js data structure (based on user's sample)
SAMPLE_HTML = '''
<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
<div id="__next"></div>
<script>
self.__next_f.push([1,"5:[\\"$\\",\\"$L18\\",null,{\\"pageData\\":{\\"content\\":[{\\"idSecurities\\":12345,\\"srtsCode\\":\\"TEST001\\",\\"sisinCode\\":\\"RU000TEST001\\",\\"fullName\\":\\"Test Issuer Corp\\",\\"securityKind\\":\\"Облигации\\"},{\\"idSecurities\\":67890,\\"srtsCode\\":\\"TEST002\\",\\"sisinCode\\":\\"RU000TEST002\\",\\"fullName\\":\\"Another Issuer LLC\\",\\"securityKind\\":\\"Облигации\\"}],\\"totalPages\\":5,\\"totalElements\\":250}}]"])
</script>
</body>
</html>
'''

def test_extraction():
    """Test Next.js data extraction with escaped quotes"""
    logger = setup_logger("test")

    print("\n" + "="*80)
    print("Testing Next.js Extraction with Escaped Quotes")
    print("="*80 + "\n")

    print("Sample HTML structure:")
    print("  Contains: self.__next_f.push([1,\"...\"])")
    print("  Data format: Escaped JSON with \\\" quotes")
    print("  Structure: {\"pageData\":{\"content\":[...],\"totalPages\":5,\"totalElements\":250}}")
    print()

    print("Running extraction...")
    result = extract_json_from_nextjs_html(SAMPLE_HTML, logger)

    if result:
        print("\n✓ SUCCESS: Extraction worked!")
        print(f"\n  Extracted keys: {list(result.keys())}")

        content = result.get('content', [])
        print(f"  Number of items: {len(content)}")
        print(f"  Total pages: {result.get('totalPages', 'N/A')}")
        print(f"  Total elements: {result.get('totalElements', 'N/A')}")

        if content:
            print(f"\n  First item:")
            for key, value in content[0].items():
                print(f"    {key}: {value}")

        print("\n" + "="*80)
        print("✓ Fix verified: Next.js extraction now handles escaped quotes correctly")
        print("="*80)
        return True
    else:
        print("\n✗ FAILED: Extraction returned None")
        print("\n" + "="*80)
        print("✗ Fix did not work as expected")
        print("="*80)
        return False

if __name__ == "__main__":
    success = test_extraction()
    exit(0 if success else 1)
