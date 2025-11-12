"""
Detect different number formats and transform them to a uniform structure
"""
import re
from main_tool.core.normalizer.elements.ab_class import Normalizer

UNIT_TOKENS = {
    'eur', 'euros', 'euro', '€',
    'mois', 'ans', 'an', 'year', 'years',
    'pourcent', 'percent', '%',
    '$'
}

SEPARATOR_TOKENS = {'/', '-', '_'}

SEP_CLASS = ''.join(re.escape(s) for s in SEPARATOR_TOKENS)

NUM_CORE = r'(?:\d{1,3}(?:[ \u00A0\u202F.,]\d{3})+|\d+)(?:[.,]\d+)?'
UNIT_PATTERN = r'(?:' + '|'.join(re.escape(u) for u in UNIT_TOKENS) + r')'

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

    # ---------------- Public API ----------------

    def normalize(self, value) -> str:
        if value is None:
            return ""

        raw = str(value).strip()
        if not raw or not self._is_number(raw):
            return None

        numbers = self._extract_numbers(raw)

        if not numbers:
            return None

        return numbers

    # ------------- Internal Helpers -------------

    @staticmethod
    def _is_number(value: str) -> bool:
        return bool(NUMBER_MATCH.fullmatch(value))

    def _extract_numbers(self, value: str) -> str:
        """
        returns the first sequence of numbers in the string
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
        token_alt = "|".join(re.escape(t) for t in SEPARATOR_TOKENS if t)
        pattern = r'(?<=\d)\s*(?:' + token_alt + r')\s*(?=\d)'
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _normalize_token(self, token: str) ->  str:
        """
        Remove thousand separators, fix decimal marker, trim zeros.
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
