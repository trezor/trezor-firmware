from __future__ import annotations

import json
from pathlib import Path

from helpers import FOREIGN_LANGUAGES, HERE, TRANSLATIONS_DIR


def get_lang_keys(lang: str) -> set[str]:
    lang_file = TRANSLATIONS_DIR / f"{lang}.json"
    lang_data = json.loads(lang_file.read_text())["translations"]
    return set(lang_data.keys())


def do_check(lang: str, missing_file: Path) -> bool:
    lang_keys = get_lang_keys(lang)
    en_keys = get_lang_keys("en")

    if lang_keys == en_keys:
        print(f"SUCCESS: {lang} and en files have the same keys")
        return True
    else:
        print(f"{lang} and en files have different keys")
        print(f"{lang} - en:", len(lang_keys - en_keys))
        print(f"en - {lang}:", len(en_keys - lang_keys))
        missing_lang = en_keys - lang_keys
        missing_en = lang_keys - en_keys
        missing_file.write_text(json.dumps(list(missing_lang), indent=2))
        print(f"Diff written into {missing_file}")
        if missing_en:
            print(f"Extra keys: {missing_en}")
        return False


if __name__ == "__main__":
    is_ok = True
    for lang in FOREIGN_LANGUAGES:
        is_ok &= do_check(lang, HERE / f"missing_{lang}.json")
    if not is_ok:
        print("ERROR: there were some inconsistencies")
        exit(1)
