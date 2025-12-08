"""
Normalize all dates formats with dateuil library, ignoring extra words and timezone.
You can test the file with the examples at the end.
"""
import re
from dateutil.parser import parse as date_parse
from main_tool.core.normalizer.elements.ab_class import Normalizer

_FRENCH_MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre"
]

# We will use this regex in the date patterns to check if the input is already in
# date format.
_FRENCH_MONTHS_REGEX = r"|".join(_FRENCH_MONTHS)

# Broad patterns to cheaply identify something that "looks like a date"
_DATE_PATTERNS = [
    re.compile(r'\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2}'),      # 2024-08-01
    re.compile(r'\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}'),    # 01/08/2024
    re.compile(r'[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}'),    # August 1, 2024
    re.compile(r'\d{1,2},?\s*[A-Za-z]{3,9},?\s*\d{4}'),  # 1 August 2024
    re.compile(r'\d{8}'),                                # 20240801
    # this pattern is to check for correct french dates like : 1 janvier 2022
    re.compile(r'\d{1,2},?\s*(?:' + _FRENCH_MONTHS_REGEX + r'),?\s*\d{4}', re.IGNORECASE)
]

# The normalized ISO date format pattern
_ISO_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

# We will use this to change french months to english (dateuil library is english)
_FRENCH_TO_EN_MONTHS = {
    "janvier": "January", "février": "February", "mars": "March", "avril": "April",
    "mai": "May", "juin": "June", "juillet": "July", "août": "August",
    "septembre": "September", "octobre": "October", "novembre": "November", "décembre": "December"
}

# A regular expression pattern matching any full French month name.
# This is constructed by joining all the month names from _FRENCH_TO_EN_MONTHS with '|',
# and escaping special characters to ensure correct matching within regular expressions.
# Example: "janvier|février|mars|..." (case-insensitive)
_FRENCH_MONTHS_PATTERN = r'|'.join(re.escape(fr) for fr in _FRENCH_TO_EN_MONTHS.keys())

# Compiled regular expression to match any French month name in a string, ignoring case.
# Used to efficiently search for and replace month names in dates.
# Example: _MONTH_REGEX.findall("Il est né en février") -> ['février']
_MONTH_REGEX = re.compile(_FRENCH_MONTHS_PATTERN, re.IGNORECASE)

class DateNormalizer(Normalizer):
    """
    Normalizes textual date variants into ISO format: YYYY-MM-DD.
    If parsing fails, returns the original string unchanged.
    """

    def __init__(self, dayfirst: bool = False):
        """
        dayfirst:
            If True, interpret ambiguous numeric dates (e.g. 01/02/2024) as DD/MM/YYYY.
        You can check dateuil library for date_parse documentation for more details.
        """
        self.dayfirst = dayfirst

    def normalize(self, value: str | None) -> str:
        """
        We will directly return the value if it's already in correct date format,
        or if it's empty.
        """
        if value is None:
            return ""

        stripped_value = str(value).strip()

        # we also check if not s for the case where s = " ", it would be "" after strip()
        if not stripped_value or not self._looks_like_date(stripped_value):
            return stripped_value

        # Pre-process French dates by replacing them with english ones
        stripped_value = self._replace_french_months(stripped_value)

        try:
            # We ignore additional words with the date by using fuzzy = True
            # We also don't use a timezone with ignoretz = True
            # We send the date in year-month-date format
            dt = date_parse(stripped_value, dayfirst=self.dayfirst, fuzzy=True, ignoretz=True)
            return dt.strftime('%Y-%m-%d')

        except Exception:
            # We use a broad exception here on purpose,
            # it would signal that the string is not a date.
            # This could backfire if it is an unexpected bug.
            return stripped_value

    def is_iso(self, value: str) -> bool:
        """
        Check if value is a date with regex.
        """
        return bool(_ISO_RE.match(value))

    # ---------------- Internal Helpers ---------------- #

    def _looks_like_date(self, value: str) -> bool:
        return any(p.search(value) for p in _DATE_PATTERNS)

    def _replace_french_months(self, value: str) -> str:
        """
        This function searches the input text for any full French month names (case-insensitive)
        and replaces them with the corresponding English month names, using a predefined mapping.
        Non-matching text remains unchanged.
        """
        def repl(match):
            fr_month = match.group(0).lower()
            return _FRENCH_TO_EN_MONTHS.get(fr_month, match.group(0))
        return _MONTH_REGEX.sub(repl, value)


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
