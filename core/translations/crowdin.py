from pathlib import Path
import json

import click

from cli import TranslationsDir
from trezorlib._internal import translations
from trezorlib.debuglink import LayoutType


HERE = Path(__file__).parent

# staging directory for layout-specific translation JSON files
CROWDIN_DIR = HERE / "crowdin"

# layouts with translation support
ALL_LAYOUTS = frozenset(LayoutType) - {LayoutType.T1}


@click.group()
def cli() -> None:
    pass


@cli.command()
def prepare() -> None:
    """Prepare translation files for Crowdin upload.

    Create a separate JSON file for each language and layout.
    """
    tdir = TranslationsDir()

    for lang in tdir.all_languages():
        blob_json = tdir.load_lang(lang)
        for layout_type in ALL_LAYOUTS:
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


if __name__ == "__main__":
    cli()
