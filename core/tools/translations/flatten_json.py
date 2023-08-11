from __future__ import annotations

import json

from helpers import ALL_LANGUAGES, TRANSLATIONS_DIR


def flatten_data(data: dict[str, dict[str, str]]) -> dict[str, str]:
    items: list[tuple[str, str]] = []
    for section_name, section in data.items():
        for k, v in section.items():
            name = f"{section_name}__{k}"
            items.append((name, v))
    items.sort(key=lambda x: x[0])
    return dict(items)


for lang in ALL_LANGUAGES:
    lang_file = TRANSLATIONS_DIR / f"{lang}.json"
    lang_data = json.loads(lang_file.read_text())
    translations_data = lang_data["translations"]
    lang_data["translations"] = flatten_data(translations_data)

    lang_file.write_text(
        json.dumps(lang_data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    )
