from pathlib import Path

HERE = Path(__file__).parent
CORE = HERE.parent.parent

TRANSLATIONS_DIR = CORE / "translations"

ENGLISH_LANG = "en"
FOREIGN_LANGUAGES = ["cs", "de", "es", "fr", "it", "pt", "tr"]
ALL_LANGUAGES = [ENGLISH_LANG] + FOREIGN_LANGUAGES
