from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Object:
    name: str
    comment: str
    breakpoint: str
    attributes: list[str]
    show_only_once: bool = False
    continue_after_cmd: bool = True


# TODO: look into C and micropython as well
# TODO: could define some tests for this - create a test-case and assert sizes
# TODO: could become a stack-size-tool as a counterpart to bin-size-tool
# TODO: look into tools/analyze-memory-dump.py script
# TODO: add possibility to determine the breakpoint dynamically from python,
# , so that we do not need to change the breakpoint line-number manually
# (like setting a function name and a path-to-file, determining linenumber automatically)
# TODO: might analyze it in place() not paint() so it does not spam so much when HoldToConfirm repaints


OBJECTS: list[Object] = [
    Object(
        name="Flow",
        comment="`Flow` when being painted",
        breakpoint="src/ui/model_tr/component/flow.rs:204",
        attributes=[
            "pages",
            "page_counter",
            "pad",
            "common_title",
            "current_page",
            "buttons",
        ],
    ),
    Object(
        name="Page",
        comment="`Page` when being painted",
        breakpoint="src/ui/model_tr/component/flow_pages.rs:92",
        attributes=[
            "ops",
            "layout",
            "btn_layout",
            "btn_actions",
            "current_page",
            "page_count",
            "char_offset",
        ],
    ),
    Object(
        name="PinEntry",
        comment="`PinEntry` when being painted",
        breakpoint="src/ui/model_tr/component/pin.rs:194",
        attributes=[
            "show_real_pin",
            "textbox",
            "choice_page",
        ],
    ),
    Object(
        name="Bip39Entry",
        comment="`Bip39Entry` when being painted",
        breakpoint="src/ui/model_tr/component/bip39.rs:225",
        attributes=[
            "choice_page",
            "letter_choices",
            "textbox",
            "pad",
            "offer_words",
            "bip39_words_list",
            "words",
            "word_count",
        ],
    ),
    Object(
        name="PassphraseEntry",
        comment="`PassphraseEntry` when being painted",
        breakpoint="src/ui/model_tr/component/passphrase.rs:287",
        attributes=[
            "choice_page",
            "show_plain_passphrase",
            "textbox",
            "current_category",
            "menu_position",
        ],
    ),
    Object(
        name="SimpleChoice",
        comment="`SimpleChoice` when being painted",
        breakpoint="src/ui/model_tr/component/simple_choice.rs:100",
        attributes=[
            "choices",
            "choice_page",
        ],
    ),
    Object(
        name="ButtonPage",
        comment="`ButtonPage` when being painted",
        breakpoint="src/ui/model_tr/component/page.rs:213",
        attributes=[
            "content",
            "scrollbar",
            "pad",
            "cancel_btn_details",
            "confirm_btn_details",
            "back_btn_details",
            "next_btn_details",
            "buttons",
        ],
    ),
    Object(
        name="ChoicePage",
        comment="`ChoicePage` when being painted",
        breakpoint="src/ui/model_tr/component/choice.rs:283",
        attributes=[
            "choices",
            "pad",
            "buttons",
            "page_counter",
            "is_carousel",
        ],
    ),
    Object(
        name="Paragraphs",
        comment="`Paragraphs` when being painted",
        breakpoint="src/ui/component/text/paragraphs.rs:142",
        attributes=[
            "area",
            "list",
            "placement",
            "offset",
            "visible",
        ],
    ),
    Object(
        name="FormattedText",
        comment="`FormattedText` when being painted",
        breakpoint="src/ui/component/text/formatted.rs:226",
        attributes=[
            "layout",
            "fonts",
            "format",
            "args",
            "icon_args",
            "char_offset",
        ],
    ),
    Object(
        name="ButtonController",
        comment="`ButtonController` when being painted",
        breakpoint="src/ui/model_tr/component/button_controller.rs:383",
        attributes=[
            "pad",
            "left_btn",
            "middle_btn",
            "right_btn",
            "state",
            "button_area",
        ],
    ),
    Object(
        name="ButtonContainer",
        comment="`ButtonContainer` when being painted",
        breakpoint="src/ui/model_tr/component/button_controller.rs:137",
        attributes=[
            "pos",
            "button_type",
        ],
    ),
    Object(
        name="Button",
        comment="`Button` when being painted",
        breakpoint="src/ui/model_tr/component/button.rs:204",
        attributes=[
            "bounds",
            "pos",
            "content",
            "styles",
            "state",
        ],
    ),
    Object(
        name="HoldToConfirm",
        comment="`HoldToConfirm` when being painted",
        breakpoint="src/ui/model_tr/component/confirm.rs:109",
        attributes=[
            "area",
            "pos",
            "loader",
            "text_width",
        ],
    ),
    Object(
        name="Loader",
        comment="`Loader` when being painted",
        breakpoint="src/ui/model_tr/component/loader.rs:208",
        attributes=[
            "area",
            "state",
            "growing_duration",
            "shrinking_duration",
            "text_overlay",
            "styles",
        ],
    ),
    Object(
        name="ButtonDetails",
        comment="`ButtonDetails` when being styled",
        breakpoint="src/ui/model_tr/component/button.rs:509",
        attributes=[
            "text",
            "icon",
            "duration",
            "is_cancel",
            "with_outline",
            "with_arms",
            "force_width",
            "offset",
        ],
    ),
]
