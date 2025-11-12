"""
File Name normalizer class
"""
import re
import os
from main_tool.core.normalizer.elements.ab_class import Normalizer

class FileNameNormalizer(Normalizer):
    """
    Build a canonical file key shared by GT and predictions:
      - lowercases
      - strips extension
      - if pattern matches (e.g. 6+ digits + letter) returns that group
      - otherwise splits at first '.' and collapses whitespace -> underscores
    """

    def normalize(self, filepath_or_name: str) -> str:
        pattern = re.compile(r"\d{6,}")
        name = os.path.basename(str(filepath_or_name)).lower()
        match = pattern.search(name)
        if match:
            return match.group(0)
        if '.' in name:
            name = name.split('.', 1)[0]
        name = name.strip()
        name = re.sub(r'\s+', '_', name)
        return name

# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    vn = FileNameNormalizer()
    samples = [
        "MACIF 7903793",
        "MACIF DEVIS 5869224",
        "MAIF MUTLI IMPACT 5607529",
        "MACIF DEVIS 5869224 2"
    ]
    for s in samples:
        print(f"{s!r} -> {vn.normalize(s)}")
