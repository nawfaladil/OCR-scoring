"""
Normalize booleans to oui/non
"""
from main_tool.core.normalizer.elements.ab_class import Normalizer

TRUE_SET = {"true", "vrai", "yes", "y", "1", "oui"}
FALSE_SET = {"false", "faux", "no", "n", "0", "non"}

class BoolNormalizer(Normalizer):
    """
    Change all booleans to standard "oui" / "non"
    If you have a boolean that's not included in the sets, feel free to add it.
    """

    def normalize(self, value: str) -> str:
        """
        we use TRUE_SET to check if it's a true boolean,
        and the FALSE_SET if it's a false boolean.
        """
        lowered_stripped_value = value.lower().strip()

        if lowered_stripped_value in TRUE_SET:
            return "oui"

        elif lowered_stripped_value in FALSE_SET:
            return "non"

        return value
