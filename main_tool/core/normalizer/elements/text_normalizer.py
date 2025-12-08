"""
Text normalization applied to strings
"""
import unicodedata
import re
from main_tool.core.normalizer.elements.ab_class import Normalizer

class TextNormalizer(Normalizer):
    """
    Aggressive canonical text normalization:
      - NFKD accent removal
      - Remove punctuation & symbols
      - Lowercase
      - Collapse & remove whitespace
    """

    def normalize(self, value) -> str:
        if value is None:
            return ""

        s = str(value)
        s = unicodedata.normalize('NFKD', s)
        s = ''.join(c for c in s if not unicodedata.combining(c))
        s = ''.join(c for c in s if unicodedata.category(c)[0] not in ('P', 'S'))
        s = s.lower()
        s = re.sub(r'\s+', '', s)
        return s
