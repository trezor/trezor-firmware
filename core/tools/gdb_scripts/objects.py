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


OBJECTS: list[Object] = [
    Object(
        name="Flow",
        comment="Sizes of `Flow` when being painted",
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
        comment="Sizes of `Page` when being painted",
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
        comment="Sizes of `PinEntry` when being painted",
        breakpoint="src/ui/model_tr/component/pin.rs:194",
        attributes=[
            "show_real_pin",
            "textbox",
            "choice_page",
        ],
    ),
    Object(
        name="Bip39Entry",
        comment="Sizes of `Bip39Entry` when being painted",
        breakpoint="src/ui/model_tr/component/bip39.rs:284",
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
        comment="Sizes of `PassphraseEntry` when being painted",
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
        comment="Sizes of `SimpleChoice` when being painted",
        breakpoint="src/ui/model_tr/component/simple_choice.rs:100",
        attributes=[
            "choices",
            "choice_page",
        ],
    ),
    Object(
        name="ButtonPage",
        comment="Sizes of `ButtonPage` when being painted",
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
        comment="Sizes of `ChoicePage` when being painted",
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
        comment="Sizes of `Paragraphs` when being painted",
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
        comment="Sizes of `FormattedText` when being painted",
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
]
