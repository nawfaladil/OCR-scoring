"""
Normalize all dates formats with dateuil library, ignoring extra words and timezone.
"""
import re
from dateutil.parser import parse as date_parse
from main_tool.core.normalizer.elements.ab_class import Normalizer


# Broad patterns to cheaply identify something that "looks like a date"
_FRENCH_MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre"
]

_FRENCH_MONTHS_REGEX = r"|".join(_FRENCH_MONTHS)

_DATE_PATTERNS = [
    re.compile(r'\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}'),      # 2024-08-01
    re.compile(r'\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}'),    # 01/08/2024
    re.compile(r'[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}'),    # August 1, 2024
    re.compile(r'\d{1,2},?\s*[A-Za-z]{3,9},?\s*\d{4}'),  # 1 August 2024
    re.compile(r'\d{8}'),                                # 20240801
    re.compile(r'\d{1,2},?\s*(?:' + _FRENCH_MONTHS_REGEX + r'),?\s*\d{4}', re.IGNORECASE)
]

_ISO_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

_FRENCH_TO_EN_MONTHS = {
    "janvier": "January", "février": "February", "mars": "March", "avril": "April",
    "mai": "May", "juin": "June", "juillet": "July", "août": "August",
    "septembre": "September", "octobre": "October", "novembre": "November", "décembre": "December"
}

class DateNormalizer(Normalizer):
    """
    Normalizes textual date variants into ISO format: YYYY-MM-DD.
    If parsing fails, returns the original string unchanged.
    """

    def __init__(self, dayfirst: bool = False):
        """
        dayfirst:
            If True, interpret ambiguous numeric dates (e.g. 01/02/2024) as DD/MM/YYYY.
        """
        self.dayfirst = dayfirst

    def normalize(self, value) -> str:
        if value is None:
            return ""

        s = str(value).strip()
        if not s or not self._looks_like_date(s):
            return s
        
        # Pre-process French dates
        s = self._replace_french_months(s)

        try:
            dt = date_parse(s, dayfirst=self.dayfirst, fuzzy=True, ignoretz=True)
            return dt.strftime('%Y-%m-%d')

        except Exception:
            return s

    def is_iso(self, s: str) -> bool:
        """
        Check if s is a date with regex.
        """
        return bool(_ISO_RE.match(s))

    # ---------------- Internal Helpers ---------------- #

    def _looks_like_date(self, s: str) -> bool:
        return any(p.search(s) for p in _DATE_PATTERNS)

    def _replace_french_months(self, s: str) -> str:
        for fr, en in _FRENCH_TO_EN_MONTHS.items():
            s = re.sub(fr, en, s, flags=re.IGNORECASE)
        return s


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    vn = DateNormalizer()
    samples = [
        "27/07/2009",
        "5 FévrIer 2025",
        "15 mai 2025"
    ]
    for s in samples:
        print(f"{s!r} -> {vn.normalize(s)}")
