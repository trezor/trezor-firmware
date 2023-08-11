from googletrans import Translator
from typing import Any, Dict
import json

from validate_same_keys import get_missing_lang_dict, DIR, MISSING_VALUE


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

    with open(DIR / "en.json", "r") as f:
        en_dict = json.load(f)["translations"]

    for language in ["cs", "fr"]:
        print(f"Translating to {language}")
        missing = get_missing_lang_dict(language)
        if TRANSLATE:
            update_nested_dict(missing, en_dict)
            translated_dict = translate_dict(missing, translator, "en", language)
        else:
            translated_dict = missing
        print("translated_dict", translated_dict)
        lang_file = DIR / f"{language}.json"
        lang_data = json.loads(lang_file.read_text())
        extend_nested_dict(lang_data["translations"], translated_dict)
        lang_file.write_text(
            json.dumps(lang_data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        )
