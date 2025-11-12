"""
Normalize booleans to oui/non
"""
from main_tool.core.normalizer.elements.ab_class import Normalizer

TRUE_SET = {"true", "vrai", "yes", "y", "1", "oui"}
FALSE_SET = {"false", "faux", "no", "n", "0", "non"}

class BoolNormalizer(Normalizer):
    """
    Change all booleans to standard "oui" / "non"
    """

    def normalize(self, value):
        lowered_stripped_value = value.lower().strip()

        if lowered_stripped_value in TRUE_SET:
            return "oui"

        elif lowered_stripped_value in FALSE_SET:
            return "non"

        return value
