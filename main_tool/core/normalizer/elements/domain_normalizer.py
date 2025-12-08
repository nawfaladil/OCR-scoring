"""
Impose some domain specific normalizations according to project needs
"""
import re
from typing import Optional
from main_tool.core.normalizer.elements.ab_class import Normalizer


class DomainNormalizer(Normalizer):
    """
    Normalize some special cases we get in some different projects
    """

    def normalize(self, value, field_name: Optional[str] = None) -> str:
        """
        You can easily add any special case normalisation here according to your needs.
        """
        if field_name == "Merchandises":
            # Special case in the trade project, we take the first part of data before " : ",
            # in the Merchandises field.
            return str(value).split(':', maxsplit=1)[0].strip()

        elif field_name == "Formule déléguée":
            # Normalize plus-separated word groups (e.g. 'Décès + PTIA + IPT + ITT') by:
            #   - Extracting sequences joined by '+'
            #   - Removing extra words (ignored if not part of a '+' sequence)
            #   - Sorting the items alphabetically
            #   - Returning the normalized, ordered string
            # If no such sequence is found, returns the input unchanged.

            pattern = re.compile(
                r'(?<![A-Za-zÀ-ÖØ-öø-ÿ])' # Ensures no letter just before (not inside a word)
                # Main capture group, one or more words separated by '+',
                # Allowing extra spaces, accented/unicode
                r'([A-Za-zÀ-ÖØ-öø-ÿ]+(?:\s*\+\s*[A-Za-zÀ-ÖØ-öø-ÿ]+)+)'
                r'(?![A-Za-zÀ-ÖØ-öø-ÿ])' # Ensures no letter after (not inside a word)
            )
            match = pattern.search(str(value))
            if not match:
                # Return as-is if no matching phrase is found
                return str(value)
            # Split on plus with optional whitespace to get list of words
            phrases = match.group(1).split(' + ')
            # Sort alphabetically for normalization
            phrases.sort()
            # Join back together with single '+' and spaces for standard form
            return " + ".join(phrases)

        elif field_name == "Etat d'avancement de l'assurance externe : Contrat signé"\
                and value == "certificat d'adhésion":
            # Very simple special case
            return "Contrat signé"

        return "" if value is None else str(value)
