from __future__ import annotations

import json
from dataclasses import dataclass
import sys

from helpers import HERE, TRANSLATIONS_DIR


@dataclass
class TooLong:
    key: str
    value: str
    lines: list[str]
    en: str
    lines_en: list[str]

    def __str__(self) -> str:
        return f"{self.key} : {self.value} --- {self.en} ({len(self.lines)} / {len(self.lines_en)})"


ALTCOINS = [
    "binance",
    "cardano",
    "ethereum",
    "eos",
    "monero",
    "nem",
    "stellar",
    "solana",
    "ripple",
    "tezos",
]

SCREEN_TEXT_WIDTHS = {"TT": 240 - 12, "TS3": 128}
MAX_BUTTON_WIDTH = {"TT": 162, "TS3": 88}

FONT_MAPPING = {
    "TT": {
        "title": "bold",
        "text": "normal",
        "bold": "bold",
        "button": "bold",
    },
    "TS3": {
        "title": "bold",
        "text": "normal",
        "bold": "bold",
        "button": "normal",
    },
}

DEVICES = ["TT", "TS3"]

FONTS_FILE = HERE / "font_widths.json"

FONTS: dict[str, dict[str, dict[str, int]]] = json.loads(FONTS_FILE.read_text())


def will_fit(text: str, type: str, device: str, lines: int) -> bool:
    if type == "button":
        return get_text_width(text, type, device) <= MAX_BUTTON_WIDTH[device]
    else:
        needed_lines = get_needed_lines(text, type, device)
        return needed_lines <= lines


def get_needed_lines(text: str, type: str, device: str) -> int:
    return len(assemble_lines(text, type, device))


def assemble_lines(text: str, type: str, device: str) -> list[str]:
    space_width = get_text_width(" ", type, device)
    words = text.replace("\r", "\n").split(" ")  # Splitting explicitly by space
    current_line_length = 0
    current_line = []
    assembled_lines: list[str] = []

    screen_width = SCREEN_TEXT_WIDTHS[device]

    for word in words:
        segments = word.split("\n")
        for i, segment in enumerate(segments):
            if segment:
                segment_width = get_text_width(segment, type, device)
                if current_line_length + segment_width <= screen_width:
                    current_line.append(segment)
                    current_line_length += segment_width + space_width
                else:
                    assembled_lines.append(" ".join(current_line))
                    current_line = [segment]
                    current_line_length = segment_width + space_width
            # If this is not the last segment, add a newline
            if i < len(segments) - 1:
                assembled_lines.append(" ".join(current_line))
                current_line = []
                current_line_length = 0

    if current_line:  # Append the last line if it's not empty
        assembled_lines.append(" ".join(current_line))

    return assembled_lines


def fill_line_with_underscores(lines: list[str], type: str, device: str) -> list[str]:
    filled_lines: list[str] = []
    screen_width = SCREEN_TEXT_WIDTHS[device]

    for line in lines:
        line_width = get_text_width(line, type, device)
        while line_width < screen_width:
            line += "_"
            line_width = get_text_width(line, type, device)
        filled_lines.append(line[:-1])

    return filled_lines


def print_lines(lines: list[str]) -> None:
    for line in lines:
        print(line)


def get_text_width(text: str, type: str, device: str) -> int:
    font = FONT_MAPPING[device][type]
    widths = FONTS[device][font]
    return sum(widths.get(c, 8) for c in text)


def check(language: str) -> list[TooLong]:
    en_file = TRANSLATIONS_DIR / "en.json"
    en_content = json.loads(en_file.read_text())["translations"]

    translation_file = TRANSLATIONS_DIR / f"{language}.json"
    rules_file = HERE / "rules.json"
    rules_content = json.loads(rules_file.read_text())

    translation_content = json.loads(translation_file.read_text())["translations"]
    translation_content = {
        k: v.replace(" (TODO)", "") for k, v in translation_content.items()
    }
    translation_content = {
        k: v.replace(" (TOO LONG)", "") for k, v in translation_content.items()
    }

    wrong: dict[str, TooLong] = {}

    for k, v in list(translation_content.items())[:]:
        if k.split("__")[0] in ALTCOINS:
            continue
        if k.split("__")[0] == "plurals":
            continue

        rule = rules_content.get(k)
        if not rule:
            print(f"Missing rule for {k}")
            continue
        type, lines = rule.split(",")
        lines = int(lines)

        for model in DEVICES:
            if model == "TT" and k.startswith("tutorial"):
                continue

            if not will_fit(v, type, model, lines):
                too_long = TooLong(
                    k,
                    v,
                    assemble_lines(v, type, model),
                    en_content[k],
                    assemble_lines(en_content[k], type, model),
                )
                wrong[k] = too_long

    for _, too_long in wrong.items():
        print(too_long)

    print(len(wrong))

    return list(wrong.values())


def test() -> None:
    def test_fits_exactly(text: str, type: str, device: str, lines: int) -> None:
        assert not will_fit(text, type, device, lines - 1)
        assert will_fit(text, type, device, lines)

    for model in DEVICES:
        assert will_fit("Hello world", "title", model, 2)
        assert will_fit("Hello world", "title", model, 1)
        assert will_fit("By continuing you agree", "text", model, 1)
        assert not will_fit("Confirming a transaction", "text", model, 1)
        assert will_fit("Confirming a transaction", "text", model, 2)
        assert will_fit("Loading private seed is not recommended.", "text", model, 2)
        assert will_fit("CONFIRM TRANSACTION", "title", model, 1)
        assert not will_fit("RECEIVE ADDRESS (MULTISIG)", "title", model, 1)
        test_fits_exactly(
            "I have\nfour\nlines\rhere",
            "text",
            model,
            4,
        )
        assert will_fit("HOLD TO CONFIRM", "button", model, 1)
        assert will_fit("OK, I UNDERSTAND", "button", model, 1)

    assert will_fit("Choose level of details", "text", "TT", 1)
    test_fits_exactly(
        "Do you really want to enforce strict safety checks (recommended)?",
        "text",
        "TT",
        4,
    )


if __name__ == "__main__":
    lang = "de"
    if len(sys.argv) > 1:
        lang = sys.argv[1]

    test()
    check(lang)
