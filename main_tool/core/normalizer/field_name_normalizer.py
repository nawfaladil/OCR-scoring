"""
Field Name normalizer class
"""
from pandas import DataFrame
from main_tool.core.normalizer.elements.ab_class import Normalizer

# Similarly to domain specific normalization, we put here
# any field name that we want to change to what we want specifically.
# We use it here to change field names in output file
# to the field name format it's in ground truth file
# key: value where key is the original field name and value is what we wanna map it to
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
