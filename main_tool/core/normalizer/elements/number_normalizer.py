"""
Detect different number formats and transform them to a standard format.
Look at the end of the file for testing with examples.
"""
import re
from main_tool.core.normalizer.elements.ab_class import Normalizer

# Number units, add if units here if not already added.
UNIT_TOKENS = {
    'eur', 'euros', 'euro', '€',
    'mois', 'ans', 'an', 'year', 'years',
    'pourcent', 'percent', '%',
    '$'
}

# Number separators, add to list if not already added.
SEPARATOR_TOKENS = {'/', '-', '_'}

# A string suitable for inclusion in regex character classes, containing the separators.
# For example, if SEPARATOR_TOKENS = {'/', '-', '_'}, then SEP_CLASS == '/-_'
# This is useful for writing patterns like [SEP_CLASS] to match any separator character.
SEP_CLASS = ''.join(re.escape(s) for s in SEPARATOR_TOKENS)

# NUM_CORE: Matches the "core" of a number, with support
# for grouping/thousands separators and decimals.
# - (?:\d{1,3}(?:[ \u00A0\u202F.,]\d{3})+|\d+): Matches either
# a number with grouped thousands (e.g. 1 000, 1.000, 1,000)
#   or a plain integer (no separators).
# - (?:[.,]\d+)?: Optionally matches a decimal component (using a dot or comma).
# Examples matched: 1000, 1 000, 1,000, 900.25, 1.000.000, 2 000, 5 300,25
NUM_CORE = r'(?:\d{1,3}(?:[ \u00A0\u202F.,]\d{3})+|\d+)(?:[.,]\d+)?'

# UNIT_PATTERN: Matches any recognized "unit" token (e.g. €, $, %, kg, etc).
# - Built by joining all entries in UNIT_TOKENS, escaping them for regex.
# - Used to optionally match units before/after numbers.
# Example: If UNIT_TOKENS = {'€', '$', 'kg'}, then UNIT_PATTERN matches '€', '$', or 'kg'.
UNIT_PATTERN = r'(?:' + '|'.join(re.escape(u) for u in UNIT_TOKENS) + r')'

# NUMBER_MATCH is a regular expression for matching various forms of complex numeric expressions.
# It is designed to:
#   - Recognize numbers that may optionally be preceded
#     or followed by "unit" words (such as currency: €, $, or units like kg).
#   - Accept numbers that are optionally separated by
#     certain allowed separator characters (specified by SEP_CLASS),
#     supporting lists or ranges like "1,000 € + 2,000 €".
#   - Tolerate both tightly glued (e.g. "€100")
#     and separated (e.g. "100 €") unit/number patterns.
#   - Optionally allow a single leading word (such as a currency or descriptor, e.g. "prix 1000 €").
#   - Reject codes that are a single fused word+number sequence
#     (like "article99"), avoiding false positives.
NUMBER_MATCH = re.compile(
    rf"""^
        (?!\s*[A-Za-zÀ-ÖØ-öø-ÿ]+[0-9]+\s*$)        # reject pure fused letter+digit codes
        \s*
        (?:[A-Za-zÀ-ÖØ-öø-ÿ]+)?\s*                 # optional single leading word
        (?P<number_seq>
            (?:{UNIT_PATTERN}\s*)?                 # optional leading unit (spaced)
            (?:{UNIT_PATTERN})?                    # or glued unit (e.g. €1.234,56)
            [+-]?{NUM_CORE}
            (?:\s*(?:{UNIT_PATTERN}))?             # optional trailing unit
            (?:\s*[{SEP_CLASS}]\s*
                (?:{UNIT_PATTERN}\s*)?
                (?:{UNIT_PATTERN})?
                [+-]?{NUM_CORE}
                (?:\s*(?:{UNIT_PATTERN}))?
            )*
        )
        \s*$
    """,
    re.IGNORECASE | re.VERBOSE
)

# NUM_PATTERN is a regular expression that matches standalone numbers in text,
# supporting both integer and decimal formats and thousands separators.
# Example matches:
#   "1 000", "10,250.50", "3.1416", "1000000",
#   "1 000 000,99" (where the middle dot is a narrow no-break space)
# Not matched:
#   "A100", "3B", "foo123bar"
NUM_PATTERN = re.compile(
    r'(?<![A-Za-z0-9])(?:\d{1,3}(?:[ \u00A0\u202F.,]\d{3})+|\d+)(?:[.,]\d+)?(?![A-Za-z0-9])'
    )

class NumberNormalizer(Normalizer):
    """
    Extracts numeric tokens, normalizing:
      - Thousand separators (spaces, dots, commas).
      - Decimal separator (comma -> dot).
      - Percent values (15% -> 15).
      - Leading zeros and trailing fractional zeros.
    """

    # ---------------- Main function ---------------

    def normalize(self, value: str | None) -> str:
        """
        If the value doesn't contain numbers, we return None.
        Otherwise, we normalize the first series of numbers in value.
        example : "datadata 3323233 foo 1246", we would get : 3323233.
        I'm aware this seems incorrect, and is probably programming debt,
        but you could instead easily concatenate all existing series of numbers
        into a single one, but for now there is no need.
        """
        if value is None:
            return ""

        raw = str(value).strip()
        # if None or doesn't have any number, return None.
        if not raw or not self._is_number(raw):
            return None

        # We get the normalized first series of numbers or None if it doesn't exist
        numbers = self._extract_numbers(raw)

        if not numbers:
            return None

        return numbers

    # ------------- Internal Helpers -------------

    def _is_number(self, value: str) -> bool:
        # We use the regex to look for number patterns
        return bool(NUMBER_MATCH.fullmatch(value))

    def _extract_numbers(self, value: str) -> str:
        """
        remove units and separators from the value string
        match the first sequence of numbers
        normalize it with _normalize_token and return the normalized number string.
        """
        text = value.lower()
        text = self._remove_unit_tokens(text)
        text = self._remove_separator_tokens(text)

        number_match = NUM_PATTERN.findall(text)

        if not number_match:
            return None

        return self._normalize_token(number_match[0])

    def _remove_unit_tokens(self, value: str) -> str:
        pattern = r'\b(' + '|'.join(re.escape(u) for u in UNIT_TOKENS) + r')\b'
        text = re.sub(pattern, ' ', value) # replace unit tokens with space
        return text


    def _remove_separator_tokens(self, text: str) -> str:
        # remove separators : '10 - 20 / 3_4' -> '102034'
        token_alt = "|".join(re.escape(t) for t in SEPARATOR_TOKENS if t)
        pattern = r'(?<=\d)\s*(?:' + token_alt + r')\s*(?=\d)'
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _normalize_token(self, token: str) ->  str:
        """
        Normalize a numeric token string to standard decimal format.

        - Removes any thousand separators 
        (spaces, dots, or commas, including non-breaking and thin spaces).
        - Detects and standardizes the decimal marker to '.'
        according to the position and context of dots and commas.
        - Trims leading zeros (before the decimal) and trailing zeros (after the decimal point).
        - Returns '0' if the result would otherwise be an empty string.
        - Returns None if the normalized string is not a simple integer or decimal number.

        Handles complicated cases such as:
            - Mixed thousand and decimal separators ("1.234,56" → "1234.56", "1,234.56" → "1234.56")
            - Extra whitespace or nonstandard Unicode space separators.
            - Leftover grouping after naive splits ("10.000.50" → "10000.50")
            - Numbers with/without decimals, integer/decimal/leading-zero/trailing-zero cases.
        """

        t = token.strip()

        # Remove NBSP / thin spaces and normal spaces
        t = re.sub(r'[\u00A0\u202F ]', '', t)

        # Mixed separators (both . and ,)
        if ',' in t and '.' in t:
            last_comma = t.rfind(',')
            last_dot = t.rfind('.')
            if last_comma > last_dot:
                # comma decimal, dots thousands
                t = t.replace('.', '').replace(',', '.')
            else:
                # dot decimal, commas thousands
                t = t.replace(',', '')
        else:
            # Only comma
            if ',' in t:
                parts = t.split(',')
                if len(parts) == 2 and 1 <= len(parts[1]) <= 4:
                    # likely decimal
                    t = t.replace(',', '.')
                else:
                    t = t.replace(',', '')
            # Only dot
            elif '.' in t:
                if t.count('.') > 1:
                    pieces = t.split('.')
                    t = ''.join(pieces[:-1]) + '.' + pieces[-1]

                left, right = t.split('.')
                if (len(right) == 3 and len(left) >= 1):
                    t = left + right  # thousands grouping

        # Fallback if multiple decimals remain: keep first real decimal
        if t.count('.') > 1:
            first = t.find('.')
            t = t[:first + 1] + t[first + 1:].replace('.', '')

        # Normalize leading zeros & fractional zeros
        if '.' in t:
            int_part, frac_part = t.split('.', 1)
            int_part = int_part.lstrip('0') or '0'
            frac_part = frac_part.rstrip('0')
            t = int_part if frac_part == '' else f"{int_part}.{frac_part}"
        else:
            t = t.lstrip('0') or '0'

        if not re.match(r'^-?\d+(\.\d+)?$', t):
            return None

        return t

# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    vn = NumberNormalizer()
    samples = [
        "1541,04 Euros / 253 mois",
        "1 541,04 €",
        "1.541,04 EUR",
        "12.000",
        "15,0%",
        "2827/736",
        "134321/ 2424 / 2242 MOIS",
        "HAO HANG 2005",
        "IGTV3242",
        "$1,234.56",
        '€1.234,56'
    ]
    for s in samples:
        print(f"{s!r} -> {vn.normalize(s)}")
