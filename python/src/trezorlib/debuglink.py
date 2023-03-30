# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

import logging
import re
import textwrap
import time
from copy import deepcopy
from datetime import datetime
from enum import IntEnum
from itertools import zip_longest
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generator,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    overload,
)

from mnemonic import Mnemonic
from typing_extensions import Literal

from . import mapping, messages, protobuf
from .client import TrezorClient
from .exceptions import TrezorFailure
from .log import DUMP_BYTES
from .tools import expect

if TYPE_CHECKING:
    from .transport import Transport
    from .messages import PinMatrixRequestType

    ExpectedMessage = Union[
        protobuf.MessageType, Type[protobuf.MessageType], "MessageFilter"
    ]

EXPECTED_RESPONSES_CONTEXT_LINES = 3

LOG = logging.getLogger(__name__)


def _get_strings_inside_tag(string: str, tag: str) -> List[str]:
    """Getting all strings that are inside two same tags.
    Example:
        _get_strings_inside_tag("abc **TAG** def **TAG** ghi")
        -> ["def"]
    """
    parts = string.split(tag)
    if len(parts) == 1:
        return []
    else:
        # returning all odd indexes in the list
        return parts[1::2]


class LayoutBase:
    """Common base for layouts, containing common methods."""

    def __init__(self, lines: Sequence[str]) -> None:
        self.lines = list(lines)
        self.str_content = "\n".join(self.lines)
        self.tokens = self.str_content.split()

    def kw_pair_int(self, key: str) -> Optional[int]:
        """Getting the value of a key-value pair as an integer. None if missing."""
        val = self.kw_pair(key)
        if val is None:
            return None
        return int(val)

    def kw_pair_compulsory(self, key: str) -> str:
        """Getting value of a key that cannot be missing."""
        val = self.kw_pair(key)
        assert val is not None
        return val

    def kw_pair(self, key: str) -> Optional[str]:
        """Getting the value of a key-value pair. None if missing."""
        # Pairs are sent in this format in the list:
        # [..., "key", "::", "value", ...]
        for key_index, item in enumerate(self.tokens):
            if item == key:
                if self.tokens[key_index + 1] == "::":
                    return self.tokens[key_index + 2]

        return None


class LayoutButtons(LayoutBase):
    """Extension for the LayoutContent class to handle buttons."""

    BTN_TAG = " **BTN** "
    EMPTY_BTN = "---"
    NEXT_BTN = "Next"
    PREV_BTN = "Prev"
    BTN_NAMES = ("left", "middle", "right")

    def __init__(self, lines: Sequence[str]) -> None:
        super().__init__(lines)

    def is_applicable(self) -> bool:
        """Check if the layout has buttons."""
        return self.BTN_TAG in self.str_content

    def visible(self) -> str:
        """Getting content and actions for all three buttons."""
        return ", ".join(self.all_buttons())

    def all_buttons(self) -> Tuple[str, str, str]:
        """Getting content and actions for all three buttons."""
        contents = self.content()
        actions = self.actions()
        return tuple(f"{contents[i]} [{actions[i]}]" for i in range(3))

    def content(self) -> Tuple[str, str, str]:
        """Getting visual details for all three buttons. They should always be there."""
        if self.BTN_TAG not in self.str_content:
            return ("None", "None", "None")
        btns = _get_strings_inside_tag(self.str_content, self.BTN_TAG)
        assert len(btns) == 3
        return btns[0].strip(), btns[1].strip(), btns[2].strip()

    def actions(self) -> Tuple[str, str, str]:
        """Getting actions for all three buttons. They should always be there."""
        if "_action" not in self.str_content:
            return ("None", "None", "None")
        action_ids = ("left_action", "middle_action", "right_action")
        assert len(action_ids) == 3
        return tuple(self.kw_pair_compulsory(action) for action in action_ids)

    def get_middle_select(self) -> str:
        """What is the choice being selected right now."""
        middle_action = self.actions()[1]
        if middle_action.startswith("Select("):
            # Parsing the value out of "Select(value)"
            return middle_action[7:-1]
        else:
            return middle_action

    def get_middle_action(self) -> str:
        """What action is currently connected with a middle button."""
        return self.actions()[1]

    def can_go_next(self) -> bool:
        """Checking if there is a next page."""
        return self.get_next_button() is not None

    def can_go_back(self) -> bool:
        """Checking if there is a previous page."""
        return self.get_prev_button() is not None

    def get_next_button(self) -> Optional[str]:
        """Position of the next button, if any."""
        return self._get_btn_by_action(self.NEXT_BTN)

    def get_prev_button(self) -> Optional[str]:
        """Position of the previous button, if any."""
        return self._get_btn_by_action(self.PREV_BTN)

    def _get_btn_by_action(self, btn_action: str) -> Optional[str]:
        """Position of button described by some action. None if not found."""
        for index, action in enumerate(self.actions()):
            if action == btn_action:
                return self.BTN_NAMES[index]

        return None

    def tt_select_word_button_texts(self) -> List[str]:
        """Get text of all buttons in the layout.

        Example button: "< Button text :  LADYBUG >"
        -> ["LADYBUG"]

        Only for TT.
        """
        return re.findall(r"< Button +text : +(.*?) +>", self.str_content)

    def tt_pin_digits_order(self) -> str:
        """In what order the PIN buttons are shown on the screen.

        Example: "digits_order :: 0571384692"

        Only for TT."""
        return self.kw_pair_compulsory("digits_order")


class LayoutContent(LayoutBase):
    """Stores content of a layout as returned from Trezor.

    Contains helper functions to extract specific parts of the layout.
    """

    # How will some information be identified in the content
    TITLE_TAG = " **TITLE** "
    CONTENT_TAG = " **CONTENT** "

    def __init__(self, lines: Sequence[str]) -> None:
        super().__init__(lines)
        self.buttons = LayoutButtons(lines)

    def visible_screen(self) -> str:
        """String representation of a current screen content.
        Example:
            SIGN TRANSACTION
            --------------------
            You are about to
            sign 3 actions.
            ********************
            Icon:cancel [Cancel], --- [None], CONFIRM [Confirm]
        """
        title_separator = f"\n{20*'-'}\n"
        btn_separator = f"\n{20*'*'}\n"

        visible = ""
        if self.title():
            visible += self.title()
            visible += title_separator
        visible += self.raw_content()
        if self.buttons.is_applicable():
            visible += btn_separator
            visible += self.buttons.visible()

        return visible

    def title(self) -> str:
        """Getting text that is displayed as a title."""
        # there could be multiple of those - title and subtitle for example
        title_strings = _get_strings_inside_tag(self.str_content, self.TITLE_TAG)
        return "\n".join(title_strings).strip()

    def text_content(self) -> str:
        """Getting text that is displayed in the main part of the screen."""
        raw = self.raw_content()
        lines = raw.split("\n")
        cleaned_lines = [_clean_line(line) for line in lines if _clean_line(line)]
        return " ".join(cleaned_lines)

    def raw_content(self) -> str:
        """Getting raw text that is displayed in the main part of the screen,
        with corresponding line breaks."""
        # there could be multiple content parts
        content_parts = _get_strings_inside_tag(self.str_content, self.CONTENT_TAG)
        # there are some unwanted spaces
        return "\n".join(
            [
                content.replace(" \n ", "\n").replace("\n ", "\n").lstrip()
                for content in content_parts
            ]
        )

    def seed_words(self) -> List[str]:
        """Get all the seed words on the screen in order.

        Example content: "1. ladybug 2. acid 3. academic 4. afraid"
          -> ["ladybug", "acid", "academic", "afraid"]
        """
        # Dot after index is optional (present on TT, not on TR)
        return re.findall(r"\d+\.? (\w+)\b", self.raw_content())

    def passphrase(self) -> str:
        """Get the current value of passphrase from passphrase dialogue.

        Example content: "textbox :: abc123AB ,#$% , current_category ::"
          -> "abc123AB ,#$%"
        """
        # The passphrase itself can have spaces and commas,
        # therefore need to match the kw-pair after it)
        if "current_category" in self.str_content:
            pattern = r"textbox :: (.*?) , current_category ::"
        else:
            pattern = r"textbox :: (.*?) , >"

        match = re.search(pattern, self.str_content)
        if match:
            return match.group(1)
        else:
            return ""

    def pin(self) -> str:
        """Get the current value of PIN from PIN dialogue.

        Example content: "textbox :: 1234 "
          -> "1234"
        """
        match = re.search(r"textbox :: (.*?) ", self.str_content)
        if match:
            return match.group(1)
        else:
            return ""

    def page_count(self) -> int:
        """Get number of pages for the layout."""
        return (
            self.kw_pair_int("scrollbar_page_count")
            or self.kw_pair_int("page_count")
            or 1
        )

    def active_page(self) -> int:
        """Get current page index of the layout."""
        return self._get_number("active_page")

    def _get_number(self, key: str) -> int:
        """Get number connected with a specific key."""
        match = re.search(rf"{key} : +(\d+)", self.str_content)
        if not match:
            return 0
        return int(match.group(1))

    def _get_content_lines(
        self, tag_name: str = "Paragraphs", raw: bool = False
    ) -> List[str]:
        """Get lines of the main screen content of the layout."""

        # First line should have content after the tag, last line does not store content
        tag = f"< {tag_name}"
        for i in range(len(self.lines)):
            if tag in self.lines[i]:
                first_line = self.lines[i].split(tag)[1]
                all_lines = [first_line] + self.lines[i + 1 : -1]
                break
        else:
            all_lines = self.lines[1:-1]

        if raw:
            return all_lines
        else:
            return [_clean_line(line) for line in all_lines]


def _clean_line(line: str) -> str:
    """Cleaning the layout line for extra spaces, hyphens and ellipsis.

    Line usually comes in the form of " <content> ", with trailing spaces
    at both ends. It may end with a hyphen (" - ") or ellipsis (" ... ").

    Hyphen means the word was split to the next line, ellipsis signals
    the text continuing on the next page.
    """
    # Deleting whitespace
    line = line.strip()

    # Deleting ellipsis at the beginning
    if line.startswith("..."):
        line = line[3:]

    # Deleting a hyphen at the end, together with the space
    # before it, so it will be tightly connected with the next line
    if line.endswith(" -"):
        line = line[:-2]

    # Deleting the ellipsis at the end
    if line.endswith(" ..."):
        line = line[:-4]

    return line.strip()


def multipage_content(layouts: List[LayoutContent]) -> str:
    """Get overall content from multiple-page layout."""
    final_text = ""
    for layout in layouts:
        final_text += layout.text_content()
        # When the raw content of the page ends with ellipsis,
        # we need to add a space to separate it with the next page
        if layout.raw_content().endswith("... "):
            final_text += " "

    # Stripping possible space at the end of last page
    if final_text.endswith(" "):
        final_text = final_text[:-1]

    return final_text


class DebugLink:
    def __init__(self, transport: "Transport", auto_interact: bool = True) -> None:
        self.transport = transport
        self.allow_interactions = auto_interact
        self.mapping = mapping.DEFAULT_MAPPING

        # To be set by TrezorClientDebugLink (is not known during creation time)
        self.model: Optional[str] = None

        # For T1 screenshotting functionality in DebugUI
        self.t1_take_screenshots = False
        self.t1_screenshot_directory: Optional[Path] = None
        self.t1_screenshot_counter = 0

        # Optional file for saving text representation of the screen
        self.screen_text_file: Optional[Path] = None
        self.last_screen_content = ""

    def set_screen_text_file(self, file_path: Optional[Path]) -> None:
        if file_path is not None:
            file_path.write_bytes(b"")
        self.screen_text_file = file_path

    def open(self) -> None:
        self.transport.begin_session()

    def close(self) -> None:
        self.transport.end_session()

    def _call(self, msg: protobuf.MessageType, nowait: bool = False) -> Any:
        LOG.debug(
            f"sending message: {msg.__class__.__name__}",
            extra={"protobuf": msg},
        )
        msg_type, msg_bytes = self.mapping.encode(msg)
        LOG.log(
            DUMP_BYTES,
            f"encoded as type {msg_type} ({len(msg_bytes)} bytes): {msg_bytes.hex()}",
        )
        self.transport.write(msg_type, msg_bytes)
        if nowait:
            return None

        ret_type, ret_bytes = self.transport.read()
        LOG.log(
            DUMP_BYTES,
            f"received type {msg_type} ({len(msg_bytes)} bytes): {msg_bytes.hex()}",
        )
        msg = self.mapping.decode(ret_type, ret_bytes)
        LOG.debug(
            f"received message: {msg.__class__.__name__}",
            extra={"protobuf": msg},
        )
        return msg

    def state(self) -> messages.DebugLinkState:
        return self._call(messages.DebugLinkGetState())

    def read_layout(self) -> LayoutContent:
        return LayoutContent(self.state().layout_lines)

    def wait_layout(self) -> LayoutContent:
        obj = self._call(messages.DebugLinkGetState(wait_layout=True))
        if isinstance(obj, messages.Failure):
            raise TrezorFailure(obj)
        return LayoutContent(obj.layout_lines)

    def synchronize_at(self, layout_text: str, timeout: float = 5) -> LayoutContent:
        now = time.monotonic()
        while True:
            layout = self.read_layout()
            if layout_text in layout.str_content:
                return layout
            if time.monotonic() - now > timeout:
                raise RuntimeError("Timeout waiting for layout")
            time.sleep(0.1)

    def watch_layout(self, watch: bool) -> None:
        """Enable or disable watching layouts.
        If disabled, wait_layout will not work.

        The message is missing on T1. Use `TrezorClientDebugLink.watch_layout` for
        cross-version compatibility.
        """
        self._call(messages.DebugLinkWatchLayout(watch=watch))

    def encode_pin(self, pin: str, matrix: Optional[str] = None) -> str:
        """Transform correct PIN according to the displayed matrix."""
        if matrix is None:
            matrix = self.state().matrix
            if matrix is None:
                # we are on trezor-core
                return pin

        return "".join([str(matrix.index(p) + 1) for p in pin])

    def read_recovery_word(self) -> Tuple[Optional[str], Optional[int]]:
        state = self.state()
        return (state.recovery_fake_word, state.recovery_word_pos)

    def read_reset_word(self) -> str:
        state = self._call(messages.DebugLinkGetState(wait_word_list=True))
        return state.reset_word

    def read_reset_word_pos(self) -> int:
        state = self._call(messages.DebugLinkGetState(wait_word_pos=True))
        return state.reset_word_pos

    def input(
        self,
        word: Optional[str] = None,
        button: Optional[messages.DebugButton] = None,
        swipe: Optional[messages.DebugSwipeDirection] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
        wait: Optional[bool] = None,
        hold_ms: Optional[int] = None,
    ) -> Optional[LayoutContent]:
        if not self.allow_interactions:
            return None

        args = sum(a is not None for a in (word, button, swipe, x))
        if args != 1:
            raise ValueError(
                "Invalid input - must use one of word, button, swipe, click(x,y)"
            )

        decision = messages.DebugLinkDecision(
            button=button, swipe=swipe, input=word, x=x, y=y, wait=wait, hold_ms=hold_ms
        )

        ret = self._call(decision, nowait=not wait)
        if ret is not None:
            return LayoutContent(ret.lines)

        # Getting the current screen after the (nowait) decision
        self.save_current_screen_if_relevant(wait=False)

        return None

    def save_current_screen_if_relevant(self, wait: bool = True) -> None:
        """Optionally saving the textual screen output."""
        if self.screen_text_file is None:
            return

        if wait:
            layout = self.wait_layout()
        else:
            layout = self.read_layout()
        self.save_debug_screen(layout.visible_screen())

    def save_debug_screen(self, screen_content: str) -> None:
        if self.screen_text_file is None:
            return

        if not self.screen_text_file.exists():
            self.screen_text_file.write_bytes(b"")

        # Not writing the same screen twice
        if screen_content == self.last_screen_content:
            return

        self.last_screen_content = screen_content

        with open(self.screen_text_file, "a") as f:
            f.write(screen_content)
            f.write("\n" + 80 * "/" + "\n")

    # Type overloads make sure that when we supply `wait=True` into `click()`,
    # it will always return `LayoutContent` and we do not need to assert `is not None`.

    @overload
    def click(self, click: Tuple[int, int]) -> None:
        ...

    @overload
    def click(self, click: Tuple[int, int], wait: Literal[True]) -> LayoutContent:
        ...

    def click(
        self, click: Tuple[int, int], wait: bool = False
    ) -> Optional[LayoutContent]:
        x, y = click
        return self.input(x=x, y=y, wait=wait)

    def press_yes(self, wait: bool = False) -> None:
        self.input(button=messages.DebugButton.YES, wait=wait)

    def press_no(self, wait: bool = False) -> None:
        self.input(button=messages.DebugButton.NO, wait=wait)

    def press_info(self, wait: bool = False) -> None:
        self.input(button=messages.DebugButton.INFO, wait=wait)

    def swipe_up(self, wait: bool = False) -> None:
        self.input(swipe=messages.DebugSwipeDirection.UP, wait=wait)

    def swipe_down(self, wait: bool = False) -> None:
        self.input(swipe=messages.DebugSwipeDirection.DOWN, wait=wait)

    @overload
    def swipe_right(self) -> None:
        ...

    @overload
    def swipe_right(self, wait: Literal[True]) -> LayoutContent:
        ...

    def swipe_right(self, wait: bool = False) -> Union[LayoutContent, None]:
        return self.input(swipe=messages.DebugSwipeDirection.RIGHT, wait=wait)

    @overload
    def swipe_left(self) -> None:
        ...

    @overload
    def swipe_left(self, wait: Literal[True]) -> LayoutContent:
        ...

    def swipe_left(self, wait: bool = False) -> Union[LayoutContent, None]:
        return self.input(swipe=messages.DebugSwipeDirection.LEFT, wait=wait)

    def stop(self) -> None:
        self._call(messages.DebugLinkStop(), nowait=True)

    def reseed(self, value: int) -> protobuf.MessageType:
        return self._call(messages.DebugLinkReseedRandom(value=value))

    def start_recording(self, directory: str) -> None:
        # Different recording logic between TT and T1
        if self.model == "T":
            self._call(messages.DebugLinkRecordScreen(target_directory=directory))
        else:
            self.t1_screenshot_directory = Path(directory)
            self.t1_screenshot_counter = 0
            self.t1_take_screenshots = True

    def stop_recording(self) -> None:
        # Different recording logic between TT and T1
        if self.model == "T":
            self._call(messages.DebugLinkRecordScreen(target_directory=None))
        else:
            self.t1_take_screenshots = False

    @expect(messages.DebugLinkMemory, field="memory", ret_type=bytes)
    def memory_read(self, address: int, length: int) -> protobuf.MessageType:
        return self._call(messages.DebugLinkMemoryRead(address=address, length=length))

    def memory_write(self, address: int, memory: bytes, flash: bool = False) -> None:
        self._call(
            messages.DebugLinkMemoryWrite(address=address, memory=memory, flash=flash),
            nowait=True,
        )

    def flash_erase(self, sector: int) -> None:
        self._call(messages.DebugLinkFlashErase(sector=sector), nowait=True)

    @expect(messages.Success)
    def erase_sd_card(self, format: bool = True) -> messages.Success:
        return self._call(messages.DebugLinkEraseSdCard(format=format))

    def take_t1_screenshot_if_relevant(self) -> None:
        """Conditionally take screenshots on T1.

        TT handles them differently, see debuglink.start_recording.
        """
        if self.model == "1" and self.t1_take_screenshots:
            self.save_screenshot_for_t1()

    def save_screenshot_for_t1(self) -> None:
        from PIL import Image

        layout = self.state().layout
        assert layout is not None
        assert len(layout) == 128 * 64 // 8

        pixels: List[int] = []
        for byteline in range(64 // 8):
            offset = byteline * 128
            row = layout[offset : offset + 128]
            for bit in range(8):
                pixels.extend(bool(px & (1 << bit)) for px in row)

        im = Image.new("1", (128, 64))
        im.putdata(pixels[::-1])

        assert self.t1_screenshot_directory is not None
        img_location = (
            self.t1_screenshot_directory / f"{self.t1_screenshot_counter:04d}.png"
        )
        im.save(img_location)
        self.t1_screenshot_counter += 1


class NullDebugLink(DebugLink):
    def __init__(self) -> None:
        # Ignoring type error as self.transport will not be touched while using NullDebugLink
        super().__init__(None)  # type: ignore [Argument of type "None" cannot be assigned to parameter "transport"]

    def open(self) -> None:
        pass

    def close(self) -> None:
        pass

    def _call(
        self, msg: protobuf.MessageType, nowait: bool = False
    ) -> Optional[messages.DebugLinkState]:
        if not nowait:
            if isinstance(msg, messages.DebugLinkGetState):
                return messages.DebugLinkState()
            else:
                raise RuntimeError("unexpected call to a fake debuglink")

        return None


class DebugUI:
    INPUT_FLOW_DONE = object()

    def __init__(self, debuglink: DebugLink) -> None:
        self.debuglink = debuglink
        self.clear()

    def clear(self) -> None:
        self.pins: Optional[Iterator[str]] = None
        self.passphrase = ""
        self.input_flow: Union[
            Generator[None, messages.ButtonRequest, None], object, None
        ] = None

    def button_request(self, br: messages.ButtonRequest) -> None:
        self.debuglink.take_t1_screenshot_if_relevant()

        if self.input_flow is None:
            # Only calling screen-saver when not in input-flow
            # as it collides with wait-layout of input flows.
            # All input flows call debuglink.input(), so
            # recording their screens that way (as well as
            # possible swipes below).
            self.debuglink.save_current_screen_if_relevant(wait=True)
            if br.code == messages.ButtonRequestType.PinEntry:
                self.debuglink.input(self.get_pin())
            else:
                # Paginating (going as further as possible) and pressing Yes
                if br.pages is not None:
                    for _ in range(br.pages - 1):
                        self.debuglink.swipe_up(wait=True)
                self.debuglink.press_yes()
        elif self.input_flow is self.INPUT_FLOW_DONE:
            raise AssertionError("input flow ended prematurely")
        else:
            try:
                assert isinstance(self.input_flow, Generator)
                self.input_flow.send(br)
            except StopIteration:
                self.input_flow = self.INPUT_FLOW_DONE

    def get_pin(self, code: Optional["PinMatrixRequestType"] = None) -> str:
        self.debuglink.take_t1_screenshot_if_relevant()

        if self.pins is None:
            raise RuntimeError("PIN requested but no sequence was configured")

        try:
            return self.debuglink.encode_pin(next(self.pins))
        except StopIteration:
            raise AssertionError("PIN sequence ended prematurely")

    def get_passphrase(self, available_on_device: bool) -> str:
        self.debuglink.take_t1_screenshot_if_relevant()
        return self.passphrase


class MessageFilter:
    def __init__(self, message_type: Type[protobuf.MessageType], **fields: Any) -> None:
        self.message_type = message_type
        self.fields: Dict[str, Any] = {}
        self.update_fields(**fields)

    def update_fields(self, **fields: Any) -> "MessageFilter":
        for name, value in fields.items():
            try:
                self.fields[name] = self.from_message_or_type(value)
            except TypeError:
                self.fields[name] = value

        return self

    @classmethod
    def from_message_or_type(
        cls, message_or_type: "ExpectedMessage"
    ) -> "MessageFilter":
        if isinstance(message_or_type, cls):
            return message_or_type
        if isinstance(message_or_type, protobuf.MessageType):
            return cls.from_message(message_or_type)
        if isinstance(message_or_type, type) and issubclass(
            message_or_type, protobuf.MessageType
        ):
            return cls(message_or_type)
        raise TypeError("Invalid kind of expected response")

    @classmethod
    def from_message(cls, message: protobuf.MessageType) -> "MessageFilter":
        fields = {}
        for field in message.FIELDS.values():
            value = getattr(message, field.name)
            if value in (None, [], protobuf.REQUIRED_FIELD_PLACEHOLDER):
                continue
            fields[field.name] = value
        return cls(type(message), **fields)

    def match(self, message: protobuf.MessageType) -> bool:
        if type(message) != self.message_type:
            return False

        for field, expected_value in self.fields.items():
            actual_value = getattr(message, field, None)
            if isinstance(expected_value, MessageFilter):
                if actual_value is None or not expected_value.match(actual_value):
                    return False
            elif expected_value != actual_value:
                return False

        return True

    def to_string(self, maxwidth: int = 80) -> str:
        fields: List[Tuple[str, str]] = []
        for field in self.message_type.FIELDS.values():
            if field.name not in self.fields:
                continue
            value = self.fields[field.name]
            if isinstance(value, IntEnum):
                field_str = value.name
            elif isinstance(value, MessageFilter):
                field_str = value.to_string(maxwidth - 4)
            elif isinstance(value, protobuf.MessageType):
                field_str = protobuf.format_message(value)
            else:
                field_str = repr(value)
            field_str = textwrap.indent(field_str, "    ").lstrip()
            fields.append((field.name, field_str))

        pairs = [f"{k}={v}" for k, v in fields]
        oneline_str = ", ".join(pairs)
        if len(oneline_str) < maxwidth:
            return f"{self.message_type.__name__}({oneline_str})"
        else:
            item: List[str] = []
            item.append(f"{self.message_type.__name__}(")
            for pair in pairs:
                item.append(f"    {pair}")
            item.append(")")
            return "\n".join(item)


class MessageFilterGenerator:
    def __getattr__(self, key: str) -> Callable[..., "MessageFilter"]:
        message_type = getattr(messages, key)
        return MessageFilter(message_type).update_fields


message_filters = MessageFilterGenerator()


class TrezorClientDebugLink(TrezorClient):
    # This class implements automatic responses
    # and other functionality for unit tests
    # for various callbacks, created in order
    # to automatically pass unit tests.
    #
    # This mixing should be used only for purposes
    # of unit testing, because it will fail to work
    # without special DebugLink interface provided
    # by the device.

    def __init__(self, transport: "Transport", auto_interact: bool = True) -> None:
        try:
            debug_transport = transport.find_debug()
            self.debug = DebugLink(debug_transport, auto_interact)
            # try to open debuglink, see if it works
            self.debug.open()
            self.debug.close()
        except Exception:
            if not auto_interact:
                self.debug = NullDebugLink()
            else:
                raise

        self.reset_debug_features()

        super().__init__(transport, ui=self.ui)

        # So that we can choose right screenshotting logic (T1 vs TT)
        self.debug.model = self.features.model

    def reset_debug_features(self) -> None:
        """Prepare the debugging client for a new testcase.

        Clears all debugging state that might have been modified by a testcase.
        """
        self.ui: DebugUI = DebugUI(self.debug)
        self.in_with_statement = False
        self.expected_responses: Optional[List[MessageFilter]] = None
        self.actual_responses: Optional[List[protobuf.MessageType]] = None
        self.filters: Dict[
            Type[protobuf.MessageType],
            Optional[Callable[[protobuf.MessageType], protobuf.MessageType]],
        ] = {}

    def ensure_open(self) -> None:
        """Only open session if there isn't already an open one."""
        if self.session_counter == 0:
            self.open()

    def open(self) -> None:
        super().open()
        if self.session_counter == 1:
            self.debug.open()

    def close(self) -> None:
        if self.session_counter == 1:
            self.debug.close()
        super().close()

    def set_filter(
        self,
        message_type: Type[protobuf.MessageType],
        callback: Optional[Callable[[protobuf.MessageType], protobuf.MessageType]],
    ) -> None:
        """Configure a filter function for a specified message type.

        The `callback` must be a function that accepts a protobuf message, and returns
        a (possibly modified) protobuf message of the same type. Whenever a message
        is sent or received that matches `message_type`, `callback` is invoked on the
        message and its result is substituted for the original.

        Useful for test scenarios with an active malicious actor on the wire.
        """
        if not self.in_with_statement:
            raise RuntimeError("Must be called inside 'with' statement")

        self.filters[message_type] = callback

    def _filter_message(self, msg: protobuf.MessageType) -> protobuf.MessageType:
        message_type = msg.__class__
        callback = self.filters.get(message_type)
        if callable(callback):
            return callback(deepcopy(msg))
        else:
            return msg

    def set_input_flow(
        self, input_flow: Generator[None, Optional[messages.ButtonRequest], None]
    ) -> None:
        """Configure a sequence of input events for the current with-block.

        The `input_flow` must be a generator function. A `yield` statement in the
        input flow function waits for a ButtonRequest from the device, and returns
        its code.

        Example usage:

        >>> def input_flow():
        >>>     # wait for first button prompt
        >>>     code = yield
        >>>     assert code == ButtonRequestType.Other
        >>>     # press No
        >>>     client.debug.press_no()
        >>>
        >>>     # wait for second button prompt
        >>>     yield
        >>>     # press Yes
        >>>     client.debug.press_yes()
        >>>
        >>> with client:
        >>>     client.set_input_flow(input_flow)
        >>>     some_call(client)
        """
        if not self.in_with_statement:
            raise RuntimeError("Must be called inside 'with' statement")

        if callable(input_flow):
            input_flow = input_flow()
        if not hasattr(input_flow, "send"):
            raise RuntimeError("input_flow should be a generator function")
        self.ui.input_flow = input_flow
        input_flow.send(None)  # start the generator

    def watch_layout(self, watch: bool = True) -> None:
        """Enable or disable watching layout changes.

        Since trezor-core v2.3.2, it is necessary to call `watch_layout()` before
        using `debug.wait_layout()`, otherwise layout changes are not reported.
        """
        if self.version >= (2, 3, 2):
            # version check is necessary because otherwise we cannot reliably detect
            # whether and where to wait for reply:
            # - T1 reports unknown debuglink messages on the wirelink
            # - TT < 2.3.0 does not reply to unknown debuglink messages due to a bug
            self.debug.watch_layout(watch)

    def __enter__(self) -> "TrezorClientDebugLink":
        # For usage in with/expected_responses
        if self.in_with_statement:
            raise RuntimeError("Do not nest!")
        self.in_with_statement = True
        return self

    def __exit__(self, exc_type: Any, value: Any, traceback: Any) -> None:
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612

        # copy expected/actual responses before clearing them
        expected_responses = self.expected_responses
        actual_responses = self.actual_responses
        self.reset_debug_features()

        if exc_type is None:
            # If no other exception was raised, evaluate missed responses
            # (raises AssertionError on mismatch)
            self._verify_responses(expected_responses, actual_responses)

    def set_expected_responses(
        self, expected: List[Union["ExpectedMessage", Tuple[bool, "ExpectedMessage"]]]
    ) -> None:
        """Set a sequence of expected responses to client calls.

        Within a given with-block, the list of received responses from device must
        match the list of expected responses, otherwise an AssertionError is raised.

        If an expected response is given a field value other than None, that field value
        must exactly match the received field value. If a given field is None
        (or unspecified) in the expected response, the received field value is not
        checked.

        Each expected response can also be a tuple (bool, message). In that case, the
        expected response is only evaluated if the first field is True.
        This is useful for differentiating sequences between Trezor models:

        >>> trezor_one = client.features.model == "1"
        >>> client.set_expected_responses([
        >>>     messages.ButtonRequest(code=ConfirmOutput),
        >>>     (trezor_one, messages.ButtonRequest(code=ConfirmOutput)),
        >>>     messages.Success(),
        >>> ])
        """
        if not self.in_with_statement:
            raise RuntimeError("Must be called inside 'with' statement")

        # make sure all items are (bool, message) tuples
        expected_with_validity = (
            e if isinstance(e, tuple) else (True, e) for e in expected
        )

        # only apply those items that are (True, message)
        self.expected_responses = [
            MessageFilter.from_message_or_type(expected)
            for valid, expected in expected_with_validity
            if valid
        ]
        self.actual_responses = []

    def use_pin_sequence(self, pins: Iterable[str]) -> None:
        """Respond to PIN prompts from device with the provided PINs.
        The sequence must be at least as long as the expected number of PIN prompts.
        """
        self.ui.pins = iter(pins)

    def use_passphrase(self, passphrase: str) -> None:
        """Respond to passphrase prompts from device with the provided passphrase."""
        self.ui.passphrase = Mnemonic.normalize_string(passphrase)

    def use_mnemonic(self, mnemonic: str) -> None:
        """Use the provided mnemonic to respond to device.
        Only applies to T1, where device prompts the host for mnemonic words."""
        self.mnemonic = Mnemonic.normalize_string(mnemonic).split(" ")

    def _raw_read(self) -> protobuf.MessageType:
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612

        resp = super()._raw_read()
        resp = self._filter_message(resp)
        if self.actual_responses is not None:
            self.actual_responses.append(resp)
        return resp

    def _raw_write(self, msg: protobuf.MessageType) -> None:
        return super()._raw_write(self._filter_message(msg))

    @staticmethod
    def _expectation_lines(expected: List[MessageFilter], current: int) -> List[str]:
        start_at = max(current - EXPECTED_RESPONSES_CONTEXT_LINES, 0)
        stop_at = min(current + EXPECTED_RESPONSES_CONTEXT_LINES + 1, len(expected))
        output: List[str] = []
        output.append("Expected responses:")
        if start_at > 0:
            output.append(f"    (...{start_at} previous responses omitted)")
        for i in range(start_at, stop_at):
            exp = expected[i]
            prefix = "    " if i != current else ">>> "
            output.append(textwrap.indent(exp.to_string(), prefix))
        if stop_at < len(expected):
            omitted = len(expected) - stop_at
            output.append(f"    (...{omitted} following responses omitted)")

        output.append("")
        return output

    @classmethod
    def _verify_responses(
        cls,
        expected: Optional[List[MessageFilter]],
        actual: Optional[List[protobuf.MessageType]],
    ) -> None:
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612

        if expected is None and actual is None:
            return

        assert expected is not None
        assert actual is not None

        for i, (exp, act) in enumerate(zip_longest(expected, actual)):
            if exp is None:
                output = cls._expectation_lines(expected, i)
                output.append("No more messages were expected, but we got:")
                for resp in actual[i:]:
                    output.append(
                        textwrap.indent(protobuf.format_message(resp), "    ")
                    )
                raise AssertionError("\n".join(output))

            if act is None:
                output = cls._expectation_lines(expected, i)
                output.append("This and the following message was not received.")
                raise AssertionError("\n".join(output))

            if not exp.match(act):
                output = cls._expectation_lines(expected, i)
                output.append("Actually received:")
                output.append(textwrap.indent(protobuf.format_message(act), "    "))
                raise AssertionError("\n".join(output))

    def mnemonic_callback(self, _) -> str:
        word, pos = self.debug.read_recovery_word()
        if word:
            return word
        if pos:
            return self.mnemonic[pos - 1]

        raise RuntimeError("Unexpected call")


@expect(messages.Success, field="message", ret_type=str)
def load_device(
    client: "TrezorClient",
    mnemonic: Union[str, Iterable[str]],
    pin: Optional[str],
    passphrase_protection: bool,
    label: Optional[str],
    language: str = "en-US",
    skip_checksum: bool = False,
    needs_backup: bool = False,
    no_backup: bool = False,
) -> protobuf.MessageType:
    if isinstance(mnemonic, str):
        mnemonic = [mnemonic]

    mnemonics = [Mnemonic.normalize_string(m) for m in mnemonic]

    if client.features.initialized:
        raise RuntimeError(
            "Device is initialized already. Call device.wipe() and try again."
        )

    resp = client.call(
        messages.LoadDevice(
            mnemonics=mnemonics,
            pin=pin,
            passphrase_protection=passphrase_protection,
            language=language,
            label=label,
            skip_checksum=skip_checksum,
            needs_backup=needs_backup,
            no_backup=no_backup,
        )
    )
    client.init_device()
    return resp


# keep the old name for compatibility
load_device_by_mnemonic = load_device


@expect(messages.Success, field="message", ret_type=str)
def self_test(client: "TrezorClient") -> protobuf.MessageType:
    if client.features.bootloader_mode is not True:
        raise RuntimeError("Device must be in bootloader mode")

    return client.call(
        messages.SelfTest(
            payload=b"\x00\xFF\x55\xAA\x66\x99\x33\xCCABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!\x00\xFF\x55\xAA\x66\x99\x33\xCC"
        )
    )


def record_screen(
    debug_client: "TrezorClientDebugLink",
    directory: Union[str, None],
    report_func: Union[Callable[[str], None], None] = None,
) -> None:
    """Record screen changes into a specified directory.

    Passing `None` as `directory` stops the recording.

    Creates subdirectories inside a specified directory, one for each session
    (for each new call of this function).
    (So that older screenshots are not overwritten by new ones.)

    Is available only for emulators, hardware devices are not capable of that.
    """

    def get_session_screenshot_dir(directory: Path) -> Path:
        """Create and return screenshot dir for the current session, according to datetime."""
        session_dir = directory / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    if not _is_emulator(debug_client):
        raise RuntimeError("Recording is only supported on emulator.")

    if directory is None:
        debug_client.debug.stop_recording()
        if report_func is not None:
            report_func("Recording stopped.")
    else:
        # Transforming the directory into an absolute path,
        # because emulator demands it
        abs_directory = Path(directory).resolve()
        # Creating the dir when it does not exist yet
        if not abs_directory.exists():
            abs_directory.mkdir(parents=True, exist_ok=True)
        # Getting a new screenshot dir for the current session
        current_session_dir = get_session_screenshot_dir(abs_directory)
        debug_client.debug.start_recording(str(current_session_dir))
        if report_func is not None:
            report_func(f"Recording started into {current_session_dir}.")


def _is_emulator(debug_client: "TrezorClientDebugLink") -> bool:
    """Check if we are connected to emulator, in contrast to hardware device."""
    return debug_client.features.fw_vendor == "EMULATOR"
