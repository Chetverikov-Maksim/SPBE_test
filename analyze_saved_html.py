#!/usr/bin/env python3
"""Analyze HTML file to understand why parsing fails"""

import os
import re
import sys

# First, try to fetch new HTML
print("\n" + "="*80)
print("Attempting to fetch HTML from SPBE...")
print("="*80 + "\n")

try:
    from spbe_parser.utils import get_html, setup_logger

    logger = setup_logger("analyze", log_file=None)
    url = "https://spbexchange.ru/listing/securities/list/?page=0&size=100&sortBy=securityKind&sortByDirection=desc&securityKind=%D0%9E%D0%B1%D0%BB%D0%B8%D0%B3%D0%B0%D1%86%D0%B8%D0%B8"

    html = get_html(url, logger)

    if html:
        print(f"✓ Successfully fetched HTML: {len(html)} bytes")

        # Save it
        os.makedirs('output', exist_ok=True)
        with open('output/fetched_html.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("Saved to: output/fetched_html.html\n")
        html_file = 'output/fetched_html.html'
    else:
        print("✗ Failed to fetch HTML. Will try to find saved file...\n")
        html = None
except Exception as e:
    print(f"✗ Error fetching HTML: {e}\n")
    html = None

# If fetch failed, look for saved HTML
if not html:
    print("Looking for previously saved HTML files...")

    possible_files = []
    for root, dirs, files in os.walk('output'):
        for file in files:
            if file.endswith('.html'):
                possible_files.append(os.path.join(root, file))

    if possible_files:
        html_file = possible_files[0]
        print(f"Found: {html_file}")
        with open(html_file, 'r', encoding='utf-8') as f:
            html = f.read()
    else:
        print("No HTML files found. Please save HTML manually to output/sample.html")
        sys.exit(1)

# Analyze HTML
print("\n" + "="*80)
print("ANALYZING HTML STRUCTURE")
print("="*80 + "\n")

print(f"HTML size: {len(html)} bytes")

# Check for Next.js markers
print("\n1. Checking for Next.js markers:")
has_next_f = 'self.__next_f' in html
has_next_data = '__NEXT_DATA__' in html
next_div = '<div id="__next"'
has_next_div = next_div in html
print(f"   Contains 'self.__next_f': {has_next_f}")
print(f"   Contains '__NEXT_DATA__': {has_next_data}")
print(f"   Contains '{next_div}': {has_next_div}")

# Find self.__next_f.push calls
print("\n2. Searching for self.__next_f.push() calls...")
pattern = r'self\.__next_f\.push\(\[1,"(.+?)"\]\)'
matches = re.findall(pattern, html, re.DOTALL)
print(f"   Found {len(matches)} matches")

if matches:
    for i, match in enumerate(matches[:5], 1):
        print(f"\n   Match {i}:")
        print(f"   Length: {len(match)} chars")
        print(f"   First 300 chars: {match[:300]}")

        # Check content
        has_pagedata_escaped = '\\"pageData\\"' in match
        has_pagedata_normal = '"pageData"' in match
        has_content_escaped = '\\"content\\"' in match
        has_content_normal = '"content"' in match
        has_backslash = '\\' in match

        print(f"   Has \\\"pageData\\\": {has_pagedata_escaped}")
        print(f"   Has \"pageData\": {has_pagedata_normal}")
        print(f"   Has \\\"content\\\": {has_content_escaped}")
        print(f"   Has \"content\": {has_content_normal}")
        print(f"   Has backslashes: {has_backslash}")

# Try to extract with current function
print("\n3. Testing extraction with current function...")
try:
    from spbe_parser.utils import extract_json_from_nextjs_html, setup_logger

    logger = setup_logger("test", log_file=None)
    result = extract_json_from_nextjs_html(html, logger)

    if result:
        print(f"   ✓ Extraction successful!")
        print(f"   Keys: {list(result.keys())}")
        if 'content' in result:
            print(f"   Content items: {len(result.get('content', []))}")
    else:
        print(f"   ✗ Extraction failed (returned None)")
except Exception as e:
    print(f"   ✗ Extraction error: {e}")

# Check for __NEXT_DATA__
print("\n4. Checking for __NEXT_DATA__ script...")
next_data_pattern = r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>'
next_data_matches = re.findall(next_data_pattern, html, re.DOTALL)

if next_data_matches:
    print(f"   Found __NEXT_DATA__ script")
    print(f"   Content (first 500 chars): {next_data_matches[0][:500]}")
else:
    print(f"   No __NEXT_DATA__ script found")

print("\n" + "="*80)
print("Analysis complete. Check output above for details.")
print("="*80)
