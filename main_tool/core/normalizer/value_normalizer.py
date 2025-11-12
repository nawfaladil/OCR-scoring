"""
Value normalizer class, glues all normalizers for values field
"""
from typing import Optional
from main_tool.core.normalizer.elements.ab_class import Normalizer
from main_tool.core.normalizer.elements.bool_normalizer import BoolNormalizer
from main_tool.core.normalizer.elements.date_normalizer import DateNormalizer
from main_tool.core.normalizer.elements.domain_normalizer import DomainNormalizer
from main_tool.core.normalizer.elements.number_normalizer import NumberNormalizer
from main_tool.core.normalizer.elements.text_normalizer import TextNormalizer


class ValueNormalizer(Normalizer):
    """
    Composite normalizer applying (in order):
      1. boolean normalizer
      2. Domain normalizer
      3. Date normalizer
      4. Number normalizer
      5. Text normalizer

    Only the first successful specialized normalization is returned.
    """

    def __init__(self):
        self.bool_normalizer = BoolNormalizer()
        self.domain_normalizer = DomainNormalizer()
        self.date_normalizer = DateNormalizer()
        self.number_normalizer = NumberNormalizer()
        self.text_normalizer = TextNormalizer()


    def normalize(self, value, field_name: Optional[str] = None) -> str:
        if not value:
            return ""

        original = str(value).strip()
        if not original:
            return ""

        # Boolean normalizer

        bool_norm = self.bool_normalizer.normalize(original)
        if original != bool_norm:
            return bool_norm

        # Domain Normalizer

        original = self.domain_normalizer.normalize(
            original, field_name) # we still need to normalize the values

        # Date Normalizer:

        date_norm = self.date_normalizer.normalize(original)
        if date_norm != original or self.date_normalizer.is_iso(date_norm):
            return date_norm

        # Number Normalizer:

        number_norm = self.number_normalizer.normalize(original)
        if number_norm:
            return number_norm

        # Text Normalizer:

        return self.text_normalizer.normalize(original)


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    vn = ValueNormalizer()
    samples = [
        "Décès + PTIA + IPT + ITT",
        "Securimut - Macif - Garantie emprunteur",
        "27/07/2009"
    ]
    for s in samples:
        print(f"{s!r} -> {vn.normalize(s)}")
