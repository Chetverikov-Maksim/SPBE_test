#!/usr/bin/env python3
"""Debug script to analyze HTML structure from SPBE"""

import re
from spbe_parser.utils import get_html, setup_logger

logger = setup_logger("debug", log_file=None)

url = "https://spbexchange.ru/listing/securities/list/?page=0&size=100&sortBy=securityKind&sortByDirection=desc&securityKind=%D0%9E%D0%B1%D0%BB%D0%B8%D0%B3%D0%B0%D1%86%D0%B8%D0%B8"

print("\n" + "="*80)
print("DEBUG: Analyzing HTML Structure")
print("="*80 + "\n")

print(f"Fetching: {url[:80]}...")
html = get_html(url, logger)

if not html:
    print("✗ Failed to fetch HTML")
    exit(1)

print(f"✓ HTML fetched: {len(html)} bytes\n")

# Save HTML to file
with open('output/debug_html_latest.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Saved to: output/debug_html_latest.html\n")

# Check for Next.js markers
has_next_f = 'self.__next_f' in html
has_next_data = '__NEXT_DATA__' in html
has_next_div = '<div id="__next"' in html

print("Next.js Markers:")
print(f"  self.__next_f:     {has_next_f}")
print(f"  __NEXT_DATA__:     {has_next_data}")
print(f"  <div id=\"__next\">: {has_next_div}")

# Find all self.__next_f.push calls
pattern = r'self\.__next_f\.push\(\[1,"(.+?)"\]\)'
matches = re.findall(pattern, html, re.DOTALL)
print(f"\nFound {len(matches)} self.__next_f.push() matches")

if matches:
    for i, match in enumerate(matches[:3], 1):
        print(f"\nMatch {i} (first 200 chars):")
        print(f"  {match[:200]}...")

        # Check what's inside
        has_pagedata = '"pageData"' in match or '\\"pageData\\"' in match
        has_content = '"content"' in match or '\\"content\\"' in match
        has_escaped = '\\' in match

        print(f"  Contains 'pageData': {has_pagedata}")
        print(f"  Contains 'content': {has_content}")
        print(f"  Has escape chars: {has_escaped}")

# Check for __NEXT_DATA__
if '__NEXT_DATA__' in html:
    print("\n__NEXT_DATA__ script found!")
    next_data_pattern = r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>'
    next_data_matches = re.findall(next_data_pattern, html, re.DOTALL)
    if next_data_matches:
        print(f"__NEXT_DATA__ content (first 500 chars):")
        print(next_data_matches[0][:500])

print("\n" + "="*80)
print("Check output/debug_html_latest.html for full HTML")
print("="*80)
