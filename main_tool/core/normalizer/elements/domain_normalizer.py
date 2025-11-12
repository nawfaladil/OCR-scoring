"""
Impose some specifi normalizations according to project needs
"""
import re
from typing import Optional
from main_tool.core.normalizer.elements.ab_class import Normalizer


class DomainNormalizer(Normalizer):
    """
    Normalize some special cases we get in some different projects
    """

    def normalize(self, value, field_name: Optional[str] = None) -> str:
        if field_name == "Merchandises":
            return str(value).split(':', maxsplit=1)[0].strip()

        elif field_name == "Formule déléguée":
            pattern = re.compile(
                r'(?<![A-Za-zÀ-ÖØ-öø-ÿ])'
                r'([A-Za-zÀ-ÖØ-öø-ÿ]+(?:\s*\+\s*[A-Za-zÀ-ÖØ-öø-ÿ]+)+)'
                r'(?![A-Za-zÀ-ÖØ-öø-ÿ])'
            )
            match = pattern.search(str(value))
            if not match:
                return str(value)
            phrases = match.group(1).split(' + ')
            phrases.sort()
            return " + ".join(phrases)

        elif field_name == "Etat d'avancement de l'assurance externe : Contrat signé"\
                and value == "certificat d'adhésion":

            return "Contrat signé"

        return "" if value is None else str(value)
