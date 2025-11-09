#!/usr/bin/env python3
"""Test with real HTML from user"""

from spbe_parser.utils import extract_json_from_nextjs_html, setup_logger

# Real HTML snippet from the site
html = '''<script>self.__next_f.push([1,"5:[\\"$\\",\\"$L18\\",null,{\\"pageData\\":{\\"content\\":[{\\"idSecurities\\":7468,\\"fullName\\":\\"CK Hutchison Holdings Limited\\",\\"securityCategory\\":\\"Акции иностранного эмитента обыкновенные\\",\\"pcbCfiCurrent\\":null,\\"pcbIsinCode\\":\\"-\\",\\"siGosRegNum\\":\\"-\\",\\"siGosRegDate\\":\\"-\\",\\"classCurrency\\":\\"Гонконгский доллар\\",\\"sdateDefolt\\":\\"-\\",\\"srtsCode\\":\\"1\\",\\"slevelName\\":\\"Некотировальная часть Списка\\",\\"einnCode\\":\\"-\\",\\"sisinCode\\":\\"KYG217651051\\",\\"sfaceValue\\":\\"1\\",\\"squotListInDate\\":\\"2022-06-20T00:00:00Z\\",\\"ssegment\\":\\"-\\",\\"sdateTechnicDefolt\\":\\"-\\",\\"fisExchanged\\":null,\\"ssecFormNameFull\\":\\"Акции иностранного эмитента обыкновенные\\",\\"srtsCodeDop\\":null,\\"ssecSiteRts\\":null,\\"ssecTypeName\\":\\"акция\\",\\"scfiListing\\":\\"ESVUFR\\",\\"scfiCurrent\\":\\"ESVUFR\\",\\"sisNominal\\":true,\\"sisNotSite\\":false,\\"securityKind\\":\\"Акции\\"}],\\"pageable\\":{\\"sort\\":{\\"empty\\":true,\\"sorted\\":false,\\"unsorted\\":true},\\"offset\\":0,\\"pageNumber\\":0,\\"pageSize\\":20,\\"paged\\":true,\\"unpaged\\":false},\\"totalPages\\":119,\\"totalElements\\":2363,\\"last\\":false,\\"size\\":20,\\"number\\":0,\\"sort\\":{\\"empty\\":true,\\"sorted\\":false,\\"unsorted\\":true},\\"numberOfElements\\":20,\\"first\\":true,\\"empty\\":false},\\"params\\":{}}}]"])</script>'''

logger = setup_logger("test_real", log_file=None)

print("="*80)
print("Testing with REAL HTML from spbexchange.ru")
print("="*80)
print()

result = extract_json_from_nextjs_html(html, logger)

if result:
    print("✓ SUCCESS! Data extracted")
    print(f"  Keys: {list(result.keys())}")

    content = result.get('content', [])
    print(f"  Content items: {len(content)}")
    print(f"  Total pages: {result.get('totalPages')}")
    print(f"  Total elements: {result.get('totalElements')}")

    if content:
        print()
        print("  First item:")
        item = content[0]
        print(f"    idSecurities: {item.get('idSecurities')}")
        print(f"    fullName: {item.get('fullName')}")
        print(f"    srtsCode: {item.get('srtsCode')}")
        print(f"    sisinCode: {item.get('sisinCode')}")
        print(f"    securityKind: {item.get('securityKind')}")
else:
    print("✗ FAILED - extraction returned None")
    print("This means the patterns don't match the real HTML structure")
