import json
import sys

(RUN_ID, LANGS_JSON) = sys.argv[1:]
MAIN = json.loads(LANGS_JSON)

REPORT_URL = f"https://data.trezor.io/dev/firmware/ui_report/{RUN_ID}"
CI_RUN_URL = f"https://github.com/trezor/trezor-firmware/actions/runs/{RUN_ID}"
MODELS_INFO = [
    {"id": "T2T1", "name": "Trezor Model T", "layout": "Bolt"},
    {"id": "T3B1", "name": "Trezor Safe 3", "layout": "Caesar"},
    {"id": "T3T1", "name": "Trezor Safe 5", "layout": "Delizia"},
    {"id": "T3W1", "name": "Trezor Safe 7", "layout": "Eckhart"},
]
LANG_NAMES = {
    "cs": "Czech",
    "de": "German",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "pt": "Portuguese",
}


def display_lang(code: str) -> str:
    return LANG_NAMES.get(code, code)  # fallback to the code if unknown


def main():
    # a special marker for finding this comment (via CI)
    print("<!-- ui-comment-Crowdin -->")
    for lang in MAIN:
        print_table(lang)


def format_table_row(cells: list[str]) -> str:
    """Format a list of cells as a markdown table row with proper delimiters."""
    return "| " + " | ".join(cells) + " |"


def print_table(lang):
    print(f"\n# `{display_lang(lang)}`\n")

    header = ["layout", "context tests"]

    print(format_table_row(header))
    print(format_table_row(["---"] * len(header)))

    for model in MODELS_INFO:
        test_prefix = f"{REPORT_URL}/{model['id']}-{lang}-core_context_tests"
        row = [
            f"{model['layout']} / {model['name']}",
            f"[UI flows]({test_prefix}-index.html)",
        ]

        print(format_table_row(row))


if __name__ == "__main__":
    main()
