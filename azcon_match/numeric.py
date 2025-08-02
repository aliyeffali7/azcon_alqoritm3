"""
Lightweight number+unit extraction helpers.
Recognises patterns like
    50 mm
    d=50 mm
    Ø32mm
Returns list of (value:int, unit:str) tuples.
"""

import re
from typing import List, Tuple

# mm, m, cm, ton, m2, m(2) … extend as needed
UNIT_RE = r"(mm|cm|m(?:\\(2\\)|2)?|ton)"

# captures '50', '50mm', 'd=50 mm'
PATTERN = re.compile(
    rf"(?:d\\s*=\\s*)?"
    rf"(\\d+(?:[.,]\\d+)?)\\s*{UNIT_RE}",
    flags=re.I,
)

def extract(text: str) -> List[Tuple[float, str]]:
    out = []
    for num, unit in PATTERN.findall(text or ""):
        out.append((float(num.replace(",", ".")), unit.lower()))
    return out
