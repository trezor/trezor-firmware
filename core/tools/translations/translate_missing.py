import json
from typing import Any, Dict

from googletrans import Translator
from helpers import FOREIGN_LANGUAGES, TRANSLATIONS_DIR

MISSING_VALUE = "TODO:missing"


def translate_dict(
    d: Dict[str, Any], translator: Translator, from_lang: str, to_lang: str
) -> Dict[str, Any]:
    new_dict: dict[str, Any] = {}
    for key, value in d.items():
        if isinstance(value, dict):
            new_dict[key] = translate_dict(value, translator, from_lang, to_lang)
        else:
            try:
                translated_text = translator.translate(
                    value, src=from_lang, dest=to_lang
                ).text
                new_dict[key] = translated_text
            except Exception as e:
                print(f"Error translating {value}: {e}")
                new_dict[key] = MISSING_VALUE
    return new_dict


def update_nested_dict(target: dict, source: dict) -> None:
    for key, value in target.items():
        if key in source:
            if isinstance(value, dict):
                update_nested_dict(value, source[key])
            else:
                target[key] = source[key]


def extend_nested_dict(bigger: dict, smaller: dict) -> None:
    for key, value in smaller.items():
        if key in bigger:
            if isinstance(value, dict) and isinstance(bigger[key], dict):
                extend_nested_dict(bigger[key], value)
            else:
                bigger[key] = value
        else:
            bigger[key] = value


if __name__ == "__main__":
    translator = Translator()
    TRANSLATE = True

    with open(TRANSLATIONS_DIR / "en.json", "r") as f:
        en_dict = json.load(f)["translations"]
    en_keys = set(en_dict.keys())

    for language in FOREIGN_LANGUAGES:
        lang_file = TRANSLATIONS_DIR / f"{language}.json"
        lang_data = json.loads(lang_file.read_text())
        translations = lang_data["translations"]
        lang_keys = set(translations.keys())

        print(f"Translating to {language}")
        missing = en_keys - lang_keys
        print("missing", missing)
        missing_dict = {key: MISSING_VALUE for key in missing}
        if TRANSLATE:
            update_nested_dict(missing_dict, en_dict)
            translated_dict = translate_dict(missing_dict, translator, "en", language)
        else:
            translated_dict = missing_dict
        print("translated_dict", translated_dict)
        extend_nested_dict(lang_data["translations"], translated_dict)

        def remove_unmatched_items(
            main_dict: Dict[Any, Any], secondary_dict: Dict[Any, Any]
        ) -> None:
            keys_to_remove = [key for key in secondary_dict if key not in main_dict]
            for key in keys_to_remove:
                del secondary_dict[key]

            for key, value in secondary_dict.items():
                if isinstance(value, dict) and key in main_dict:
                    remove_unmatched_items(main_dict[key], value)

        remove_unmatched_items(en_dict, lang_data["translations"])

        lang_file.write_text(
            json.dumps(lang_data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        )
