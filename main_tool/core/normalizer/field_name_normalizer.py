"""
Field Name normalizer class
"""
from pandas import DataFrame
from main_tool.core.normalizer.elements.ab_class import Normalizer

FIELD_ALIASES = {
        "email mandataire": "Email du mandataire",
        "quotité": "Quot",
        "nom de l'assuré" : "Nom assuré",
        "prénom de l'assuré" : "Prénom assuré"
        }

class FieldNameNormalizer(Normalizer):
    """
    map some output field names to GT field names
    """

    def normalize(self, value: DataFrame) -> DataFrame:
        value["Field Name"] = value["Field Name"].apply(
                    lambda x: FIELD_ALIASES.get(str(x).lower(), x)
                    )
        return value
