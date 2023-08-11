import json

from validate_same_keys import DIR

for lang in ["en", "cs", "fr"]:
    lang_file = DIR / f"{lang}.json"
    lang_data = json.loads(lang_file.read_text())

    for section_name, section in lang_data["translations"].items():
        for key in section:
            if "title" in key:
                lang_data["translations"][section_name][key] = lang_data["translations"][section_name][key].upper()

    lang_file.write_text(
        json.dumps(lang_data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    )
