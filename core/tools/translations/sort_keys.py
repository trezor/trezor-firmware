import json

from helpers import ALL_LANGUAGES, TRANSLATIONS_DIR

for lang in ALL_LANGUAGES:
    lang_file = TRANSLATIONS_DIR / f"{lang}.json"
    lang_data = json.loads(lang_file.read_text())

    for section_name, section in lang_data["translations"].items():
        for key in section:
            if "title" in key:
                lang_data["translations"][section_name][key] = lang_data[
                    "translations"
                ][section_name][key].upper()

    lang_file.write_text(
        json.dumps(lang_data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    )
