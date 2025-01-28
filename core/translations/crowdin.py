from __future__ import annotations

from pathlib import Path
import collections
import json

import click

from cli import TranslationsDir
from trezorlib._internal import translations


HERE = Path(__file__).parent

# staging directory for layout-specific translation JSON files
CROWDIN_DIR = HERE / "crowdin"

@click.group()
def cli() -> None:
    pass


@cli.command()
def split() -> None:
    """Split translation files for Crowdin upload.

    Create a separate JSON file for each language and layout.
    """
    tdir = TranslationsDir()

    for lang in tdir.all_languages():
        blob_json = tdir.load_lang(lang)
        for layout_type in translations.ALL_LAYOUTS:
            # extract translations specific to this layout
            layout_specific_translations = {
                key: translations.get_translation(blob_json, key, layout_type)
                for key in blob_json["translations"].keys()
            }
            # create a JSON file with only the "translations" item
            result = {"translations": layout_specific_translations}
            with open(CROWDIN_DIR / f"{lang}_{layout_type.name}.json", "w") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

    click.echo(f"Successfully generated layout-specific translation files in '{CROWDIN_DIR}'")


@cli.command()
def merge() -> None:
    """Merge back translation files downloaded from Crowdin."""
    tdir = TranslationsDir()

    for lang in sorted(tdir.all_languages()):
        merged_translations: dict[str, str | dict[str, str]] = collections.defaultdict(dict)
        for layout_type in translations.ALL_LAYOUTS:
            with open(CROWDIN_DIR / f"{lang}_{layout_type.name}.json", "r") as f:
                blob_json = json.load(f)

            # mapping string name to its translation (for the current layout)
            layout_specific_translations: dict[str, str] = blob_json["translations"]
            for key, value in layout_specific_translations.items():
                merged_translations[key][layout_type.name] = value

        for key in merged_translations.keys():
            # deduplicate entries if all translations are the same
            unique_translations = set(merged_translations[key].values())
            if len(unique_translations) == 1:
                merged_translations[key] = unique_translations.pop()

        blob_json = tdir.load_lang(lang)
        blob_json["translations"] = merged_translations
        tdir.save_lang(lang, blob_json)
        click.echo(f"Updated {lang}")

    click.echo(f"Successfully merged back layout-specific translation files from '{CROWDIN_DIR}'")


if __name__ == "__main__":
    cli()
