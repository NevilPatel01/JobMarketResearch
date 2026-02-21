"""
Quick test of location parsing for Job Bank data.
"""

import re
from typing import Tuple

def parse_location(location: str) -> Tuple[str, str]:
    """
    Parse location string to city and province.
    
    Args:
        location: Location string (e.g., "Toronto, Ontario" or "Toronto (ON)")
        
    Returns:
        Tuple of (city, province_code)
    """
    province_map = {
        'ontario': 'ON', 'british columbia': 'BC', 'alberta': 'AB',
        'saskatchewan': 'SK', 'manitoba': 'MB', 'quebec': 'QC',
        'nova scotia': 'NS', 'new brunswick': 'NB',
        'newfoundland and labrador': 'NL', 'prince edward island': 'PE',
        'northwest territories': 'NT', 'nunavut': 'NU', 'yukon': 'YT'
    }
    
    # Try to match "City (PROV)" pattern first
    paren_match = re.search(r'^(.+?)\s*\(([A-Z]{2})\)$', location)
    if paren_match:
        city = paren_match.group(1).strip()
        province = paren_match.group(2).strip()
        return city, province
    
    # Otherwise use comma separation
    parts = [p.strip() for p in location.split(',')]
    city = parts[0] if parts else "Unknown"
    
    province = ""
    if len(parts) > 1:
        prov_text = parts[1].lower()
        # Check if it's already a 2-letter code
        if len(parts[1].strip()) == 2:
            province = parts[1].strip().upper()
        else:
            # Look up full name
            province = province_map.get(prov_text, parts[1].strip()[:2].upper())
    
    return city, province

# Test locations from the HTML we saw
test_locations = [
    "Toronto (ON)",
    "Ayr (ON)",
    "Montréal (QC)",
    "Toronto",
    "Vancouver, British Columbia",
    "Calgary, AB"
]

print("Testing location parsing:")
print("="*60)
for loc in test_locations:
    city, province = parse_location(loc)
    valid = "✓" if province else "✗"
    print(f"{valid} Input: '{loc:30s}' => City: '{city:15s}' Province: '{province}'")
