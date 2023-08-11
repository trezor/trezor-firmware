from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Dict

HERE = Path(__file__).parent
CORE = HERE.parent.parent

DIR = CORE / "embed" / "rust" / "src" / "ui" / "translations"

MISSING_VALUE = "TODO:missing"

if TYPE_CHECKING:
    DoubleDict = Dict[str, Dict[str, str]]


def get_all_json_keys(data: "DoubleDict") -> set[str]:
    keys: set[str] = set()
    for section_name, section in data.items():
        for k, _v in section.items():
            keys.add(f"{section_name}__{k}")
    return keys


def get_missing_dict(missing_set: set[str]) -> "DoubleDict":
    missing_dict: "DoubleDict" = {}
    for missing in sorted(missing_set):
        section_name, key = missing.split("__")
        if section_name not in missing_dict:
            missing_dict[section_name] = {}
        missing_dict[section_name][key] = MISSING_VALUE
    return missing_dict


def get_lang_keys(lang: str) -> set[str]:
    lang_file = DIR / f"{lang}.json"
    lang_data = json.loads(lang_file.read_text())["translations"]
    return get_all_json_keys(lang_data)


def get_missing_lang_dict(lang: str) -> "DoubleDict":
    lang_keys = get_lang_keys(lang)
    en_keys = get_lang_keys("en")
    return get_missing_dict(en_keys - lang_keys)


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
        missing_lang = get_missing_dict(en_keys - lang_keys)
        missing_en = get_missing_dict(lang_keys - en_keys)
        missing_file.write_text(json.dumps(missing_lang, indent=2))
        print(f"Diff written into {missing_file}")
        if missing_en:
            print(f"Extra keys: {missing_en}")
        return False


if __name__ == "__main__":
    is_ok = True
    is_ok &= do_check("cs", HERE / "missing_cs.json")
    is_ok &= do_check("fr", HERE / "missing_fr.json")
    if not is_ok:
        print("ERROR: there were some inconsistencies")
        exit(1)
