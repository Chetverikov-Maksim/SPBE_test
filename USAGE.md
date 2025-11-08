# SPBE Parser Usage Guide

## Status

✓ **Next.js extraction fix implemented and tested**
✗ **Live testing blocked by 403 Forbidden errors from spbexchange.ru**

## What was fixed

The `extract_json_from_nextjs_html()` function now correctly handles escaped quotes in Next.js server-side rendered data:

**Before:** Pattern matching failed because Next.js escapes quotes like `\"pageData\":{\"content\":[...]}`
**After:** Data is unescaped BEFORE pattern matching, allowing successful extraction

## Testing

Run the unit test to verify the fix:
```bash
python test_extraction_fix.py
```

Expected output:
```
✓ SUCCESS: Extraction worked!
  Number of items: 2
  Total pages: 5
  Total elements: 250
```

## Running the Parser

### Option 1: Using Selenium (Recommended)

To bypass 403 Forbidden errors, use Selenium with Chrome/Chromium:

1. Install Chrome or Chromium browser
2. Edit `spbe_parser/config.py`:
   ```python
   USE_SELENIUM = True
   DEBUG_SAVE_HTML = True  # Optional: save HTML for debugging
   ```
3. Run the parser:
   ```bash
   python -m spbe_parser.main --reference-data
   ```

### Option 2: Using requests library (Currently Blocked)

Default configuration uses the requests library, but spbexchange.ru blocks automated requests:
```bash
python -m spbe_parser.main --reference-data
```

**Result:** 403 Forbidden errors

### Option 3: Testing with local HTML files

If you have saved HTML files from the website:

1. Enable debug mode in `spbe_parser/config.py`:
   ```python
   DEBUG_SAVE_HTML = True
   LOG_LEVEL = "DEBUG"
   ```

2. Place HTML files in `output/debug/` directory

3. Modify parser to read from local files instead of fetching

## Available Commands

```bash
# Run all parsers
python -m spbe_parser.main --all

# Run only reference data parser
python -m spbe_parser.main --reference-data

# Run only prospectus parsers
python -m spbe_parser.main --prospectus

# Run Russian prospectus parser with cancelled bonds
python -m spbe_parser.main --russian-prospectus --include-cancelled

# Run with custom log file
python -m spbe_parser.main --reference-data --log-file custom.log

# Run without log file (console only)
python -m spbe_parser.main --reference-data --no-log-file
```

## Output

- **Reference data:** `output/SPBE_ReferenceData_YYYY-MM-DD.csv`
- **Prospectuses:** `output/Prospectuses/{Issuer}/{ISIN}/`
- **Logs:** `output/spbe_parser_YYYYMMDD_HHMMSS.log`
- **Debug HTML:** `output/debug/html_*.html` (if DEBUG_SAVE_HTML=True)

## Troubleshooting

### 403 Forbidden errors

**Problem:** spbexchange.ru blocks automated requests
**Solution:** Enable Selenium (USE_SELENIUM = True) with Chrome/Chromium installed

### "No module named 'selenium'"

**Problem:** Selenium not installed
**Solution:**
```bash
pip install selenium webdriver-manager
```

### "cannot find Chrome binary"

**Problem:** Chrome/Chromium not installed
**Solution:** Install Chrome or Chromium browser:
```bash
# Ubuntu/Debian
sudo apt-get install chromium-browser

# Or download Chrome from https://www.google.com/chrome/
```

### No bonds found (0 bonds)

**Problem:** Parser cannot fetch or extract data
**Solution:**
1. Check if using Selenium (USE_SELENIUM = True)
2. Enable debug logging (LOG_LEVEL = "DEBUG")
3. Check saved HTML files in output/debug/
4. Verify Next.js data structure hasn't changed

## Development

### Running tests

```bash
# Test Next.js extraction fix
python test_extraction_fix.py

# Test live extraction (requires working connection)
python test_nextjs_extraction.py
```

### Configuration

Edit `spbe_parser/config.py` to customize:
- Selenium settings
- Request timeouts and retries
- Debug options
- Output paths
- Logging level

## Notes

- The Next.js extraction handles multiple pattern types:
  1. Standard `pageData` structure with params
  2. Content array with pagination (no pageData wrapper)
  3. Bracket matching for content arrays

- All patterns now work with escaped quotes in Next.js data
- The fix has been tested and verified with unit tests
