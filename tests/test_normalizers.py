"""
Tests for the normalization module
"""
import pytest
from main_tool.core.normalizer.value_normalizer import ValueNormalizer
from main_tool.core.normalizer.file_name_normalizer import FileNameNormalizer


@pytest.fixture
def normalizer():
    """
    Fixture to use normalizer class
    """
    return ValueNormalizer()

@pytest.fixture
def file_normalizer():
    return FileNameNormalizer()

# --- Date-like values ---
@pytest.mark.parametrize("raw,expected", [
    ("2024-08-01", "2024-08-01"),
    ("2024/08/01", "2024-08-01"),
    ("2024.08.01", "2024-08-01"),
    ("08/01/2024", "2024-08-01"),
    ("August 1, 2024", "2024-08-01"),
    ("1 August 2024", "2024-08-01"),
    ("20240801", "2024-08-01"),
    ("Date: 2024-08-01", "2024-08-01"),
    ("08/01/2024 (deadline)", "2024-08-01"),
])

def test_dates(normalizer, raw, expected):
    """
    Test date inputs
    """
    assert normalizer.normalize(raw) == expected

# --- Number-like values ---
@pytest.mark.parametrize("raw,expected", [
    ("1234", "1234"),
    ("1,234.56", "1234.56"),
    ("1.234,56", "1234.56"),
    ("1234,56", "1234.56"),
    ("1234.56", "1234.56"),
    ("-1234.56", "1234.56"),
    ("1 234,56", "1234.56"),
    ("00123", "123"),
    ("0.0", "0"),
])

def test_numbers(normalizer, raw, expected):
    """
    Test number inputs
    """
    assert normalizer.normalize(raw) == expected

# --- String/Accent/Whitespace/Case normalization ---
@pytest.mark.parametrize("raw,expected", [
    ("Résumé.", "resume"),
    ("  Résumé. ", "resume"),
    ("Café", "cafe"),
    ("HELLO", "hello"),
    ("Hello World!", "helloworld"),
    ("Test-Case", "testcase"),
    ("Spaces   and   tabs", "spacesandtabs"),
])


def test_strings(normalizer, raw, expected):
    """
    Test text inputs
    """
    assert normalizer.normalize(raw) == expected

# --- Mixed and edge cases ---
@pytest.mark.parametrize("raw,expected", [
    ("12 apples", "12apples"),
    ("ITGV102024", "itgv102024"),
    ("EMPG1024", "empg1024"),
    ("COM17070-V02 24", "com17070v0224"),
    ("HAO HANG 2005", "haohang2005"),
    ("", ""),
    (None, ""),
    ("----", ""),
    ("   ", ""),
])

def test_mixed(normalizer, raw, expected):
    """
    Test mixed inputs
    """
    assert normalizer.normalize(raw) == expected

# --- Non-Latin alphabets (should be normalized, accents removed if possible) ---
@pytest.mark.parametrize("raw,expected", [
    ("façade", "facade"),
    ("über-cool", "ubercool"),
    ("mañana", "manana"),
    ("élève", "eleve"),
])

def test_non_latin(normalizer, raw, expected):
    """
    Test special inputs
    """
    assert normalizer.normalize(raw) == expected

# --- Currency and percent (should normalize to numbers) ---
def test_currency_percent(normalizer):
    """
    Test currency inputs
    """
    assert normalizer.normalize('$1,234.56') == '1234.56'
    assert normalizer.normalize('€1.234,56') == '1234.56'
    assert normalizer.normalize('99%') == '99'

# --- Booleans in different formats

@pytest.mark.parametrize("raw,expected", [
    ("true", "oui"),
    ("TRUE", "oui"),
    ("TrUe", "oui"),
    ("vrai", "oui"),
    ("VRAI", "oui"),
    (" yes ", "oui"),
    ("\ty\n", "oui"),
    ("1", "oui"),
    ("oui", "oui"),
    ("OuI", "oui"),
    ("false", "non"),
    ("FALSE", "non"),
    ("FaLsE", "non"),
    ("faux", "non"),
    ("FAUX", "non"),
    (" no ", "non"),
    ("\tn\n", "non"),
    ("0", "non"),
    ("non", "non"),
    ("NoN", "non"),
])

def test_booleans(normalizer, raw, expected):
    """
    Test boolean inputs
    """
    assert normalizer.normalize(raw) == expected

# ---File Name normalizer tests
@pytest.mark.parametrize(
    "raw, expected",
    [
        # Pattern (6+ digits followed by a letter) should win and be returned as-is (lowercased)
        ("123456a", "123456a"),
        ("123456A", "123456a"),
        ("some/path/000001b.JPG", "000001b"),
        ("report_202312345x_final.docx", "202312345x"),
        ("1234567Z.extra.txt", "1234567z"),   # early match before any splitting

        # No pattern match -> strip extension at first '.' only
        ("MyFile.TXT", "myfile"),
        ("Project.Plan.v1.docx", "project"),
        ("abc.def.ghi.txt", "abc"),
        ("SIMPLE", "simple"),                 # no dot, just lowercase

        # Whitespace collapse to underscores (after trimming, before return)
        ("  spaced   name.txt", "spaced_name"),
        ("spaced   name", "spaced_name"),

        # Mixed case & spaces before first dot
        ("  Mixed Case.Name.pdf", "mixed_case"),

        # Digits but not enough for pattern (needs >=6)
        ("12345.txt", "12345"),
        ("12345a.txt", "12345a"),        # 5 digits + letter -> NOT matched, extension stripped

        # Trailing spaces around base
        ("  name .pdf", "name"),
        (" name.aux.extra", "name"),          # split only at first '.'

        # Hyphens and underscores preserved (whitespace only becomes underscores)
        ("File-Name Version 2.pdf", "file-name_version_2"),
        ("multi   space---dash.TXT", "multi_space---dash"),

        # Path handling
        ("/deep/path/To/Some File 001.txt", "some_file_001"),
        ("./rel/anotherFile   123456b.png", "123456b"),  # pattern overrides

        # None & non-string input are coerced via str() then processed
        (None, "none"),
        (1234567, "1234567"),     # becomes "1234567" (no trailing letter so not a pattern)
        ("1234567", "1234567"),               # still not a pattern (needs trailing letter)

        # Edge: filename starts with a dot (hidden file)
        (".hiddenfile", ""),    # split at first '.' gives '' then strip -> '' (no whitespace to collapse)
        (".hidden.name.txt", ""),             # first split gives '' again

        # Edge: only dots
        ("....", ""),                         # split at first '.' => '' -> ''
        ("..a123456b", "123456b"),                
    ],
)

def test_file_name_normalization(file_normalizer, raw, expected):
    assert file_normalizer.normalize(raw) == expected