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

from __future__ import annotations

import json
import logging
import re
import textwrap
import time
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
from enum import Enum, IntEnum, auto
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
    Sequence,
    Tuple,
    Union,
)

from mnemonic import Mnemonic

from . import mapping, messages, models, protobuf
from .client import TrezorClient
from .exceptions import TrezorFailure, UnexpectedMessageError
from .log import DUMP_BYTES
from .messages import DebugWaitType
from .transport import Timeout

if TYPE_CHECKING:
    from typing_extensions import Protocol

    from .messages import PinMatrixRequestType
    from .transport import Transport

    ExpectedMessage = Union[
        protobuf.MessageType, type[protobuf.MessageType], "MessageFilter"
    ]

    AnyDict = Dict[str, Any]
    Coords = Tuple[int, int]

    class InputFunc(Protocol):
        def __call__(
            self,
            hold_ms: int | None = None,
        ) -> "None": ...

    InputFlowType = Generator[None, messages.ButtonRequest, None]


EXPECTED_RESPONSES_CONTEXT_LINES = 3

LOG = logging.getLogger(__name__)


class LayoutType(Enum):
    T1 = auto()
    Bolt = auto()
    Caesar = auto()
    Delizia = auto()
    Eckhart = auto()

    @classmethod
    def from_model(cls, model: models.TrezorModel) -> "LayoutType":
        if model in (models.T2T1,):
            return cls.Bolt
        if model in (models.T2B1, models.T3B1):
            return cls.Caesar
        if model in (models.T3T1,):
            return cls.Delizia
        if model in (models.T3W1,):
            return cls.Eckhart
        if model in (models.T1B1,):
            return cls.T1
        raise ValueError(f"Unknown model: {model}")

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"LayoutType.{self.name}"


class UnstructuredJSONReader:
    """Contains data-parsing helpers for JSON data that have unknown structure."""

    def __init__(self, json_str: str) -> None:
        self.json_str = json_str
        # We may not receive valid JSON, e.g. from an old model in upgrade tests
        try:
            self.dict: AnyDict = json.loads(json_str)
        except json.JSONDecodeError:
            self.dict = {}

    def top_level_value(self, key: str) -> Any:
        return self.dict.get(key)

    def find_objects_with_key_and_value(self, key: str, value: Any) -> list[AnyDict]:
        def recursively_find(data: Any) -> Iterator[Any]:
            if isinstance(data, dict):
                if data.get(key) == value:
                    yield data
                for val in data.values():
                    yield from recursively_find(val)
            elif isinstance(data, list):
                for item in data:
                    yield from recursively_find(item)

        return list(recursively_find(self.dict))

    def find_unique_object_with_key_and_value(
        self, key: str, value: Any
    ) -> AnyDict | None:
        objects = self.find_objects_with_key_and_value(key, value)
        if not objects:
            return None
        assert len(objects) == 1
        return objects[0]

    def find_values_by_key(self, key: str, only_type: type | None = None) -> list[Any]:
        def recursively_find(data: Any) -> Iterator[Any]:
            if isinstance(data, dict):
                if key in data:
                    yield data[key]
                for val in data.values():
                    yield from recursively_find(val)
            elif isinstance(data, list):
                for item in data:
                    yield from recursively_find(item)

        values = list(recursively_find(self.dict))

        if only_type is not None:
            values = [v for v in values if isinstance(v, only_type)]

        return values

    def find_unique_value_by_key(
        self, key: str, default: Any, only_type: type | None = None
    ) -> Any:
        values = self.find_values_by_key(key, only_type=only_type)
        if not values:
            return default
        assert len(values) == 1
        return values[0]


class LayoutContent(UnstructuredJSONReader):
    """Contains helper functions to extract specific parts of the layout."""

    def __init__(self, json_tokens: Sequence[str]) -> None:
        json_str = "".join(json_tokens)
        super().__init__(json_str)

    def main_component(self) -> str:
        """Getting the main component of the layout."""
        return self.top_level_value("component") or "no main component"

    def all_components(self) -> list[str]:
        """Getting all components of the layout."""
        return self.find_values_by_key("component", only_type=str)

    def visible_screen(self) -> str:
        """String representation of a current screen content.
        Example:
            SIGN TRANSACTION
            --------------------
            You are about to
            sign 3 actions.
            ********************
            ICON_CANCEL, -, CONFIRM
        """
        title_separator = f"\n{20 * '-'}\n"
        btn_separator = f"\n{20 * '*'}\n"

        visible = ""
        if self.title():
            visible += self.title()
            visible += title_separator
        visible += self.screen_content()
        visible_buttons = self.button_contents()
        if visible_buttons:
            visible += btn_separator
            visible += ", ".join(visible_buttons)

        return visible

    def _get_str_or_dict_text(self, key: str) -> str:
        value = self.find_unique_value_by_key(key, "")
        if isinstance(value, dict):
            return value["text"]
        return value

    def title(self) -> str:
        """Getting text that is displayed as a title and potentially subtitle."""
        # There could be possibly subtitle as well
        title_parts: list[str] = []

        title = self._get_str_or_dict_text("title")
        if title:
            title_parts.append(title)

        subtitle = self.subtitle()
        if subtitle:
            title_parts.append(subtitle)

        return "\n".join(title_parts)

    def subtitle(self) -> str:
        """Getting text that is displayed as a subtitle."""
        subtitle = self._get_str_or_dict_text("subtitle")
        return subtitle

    def text_content(self) -> str:
        """What is on the screen, in one long string, so content can be
        asserted regardless of newlines. Also getting rid of possible ellipsis.
        """
        content = self.screen_content().replace("\n", " ")
        if content.endswith("..."):
            content = content[:-3]
        if content.startswith("..."):
            content = content[3:]
        return content

    def screen_content(self) -> str:
        """Getting text that is displayed in the main part of the screen.
        Preserving the line breaks.
        """
        # Look for paragraphs first (will match most of the time for TT)
        paragraphs = self.raw_content_paragraphs()
        if paragraphs:
            main_text_blocks: list[str] = []
            for par in paragraphs:
                par_content = ""
                for line_or_newline in par:
                    par_content += line_or_newline
                par_content.replace("\n", " ")
                main_text_blocks.append(par_content)
            return "\n".join(main_text_blocks)

        # Formatted text
        formatted_text = self.find_unique_object_with_key_and_value(
            "component", "FormattedText"
        )
        if formatted_text:
            text_lines = formatted_text["text"]
            return "".join(text_lines)

        # Check the choice_page - mainly for TR
        choice_page = self.find_unique_object_with_key_and_value(
            "component", "ChoicePage"
        )
        if choice_page:
            left = choice_page.get("prev_choice", {}).get("content", "")
            middle = choice_page.get("current_choice", {}).get("content", "")
            right = choice_page.get("next_choice", {}).get("content", "")
            return " ".join(choice for choice in (left, middle, right) if choice)

        # Screen content - in TR share words
        screen_content = self.find_unique_value_by_key(
            "screen_content", default="", only_type=str
        )
        if screen_content:
            return screen_content

        # Flow page - for TR
        flow_page = self.find_unique_value_by_key(
            "flow_page", default={}, only_type=dict
        )
        if flow_page:
            text_lines = flow_page["text"]
            return "".join(text_lines)

        # Looking for any "text": "something" values
        text_values = self.find_values_by_key("text", only_type=str)
        if text_values:
            return "\n".join(text_values)

        # Default when not finding anything
        return self.main_component()

    def raw_content_paragraphs(self) -> list[list[str]] | None:
        """Getting raw paragraphs as sent from Rust."""
        return self.find_unique_value_by_key("paragraphs", default=None, only_type=list)

    def tt_check_seed_button_contents(self) -> list[str]:
        """Getting list of button contents."""
        buttons: list[str] = []
        button_objects = self.find_objects_with_key_and_value("component", "Button")
        for button in button_objects:
            if button.get("icon"):
                buttons.append("ICON")
            elif "text" in button:
                buttons.append(button["text"])
        return buttons

    def button_contents(self) -> list[str]:
        """Getting list of button contents."""
        buttons = self.find_unique_value_by_key("buttons", default={}, only_type=dict)

        def get_button_content(btn_key: str) -> str:
            button_obj = buttons.get(btn_key, {})
            if button_obj.get("component") == "Button":
                if "icon" in button_obj:
                    return button_obj["icon"]
                elif "text" in button_obj:
                    return button_obj["text"]
            elif button_obj.get("component") == "HoldToConfirm":
                text = button_obj.get("loader", {}).get("text", "")
                duration = button_obj.get("loader", {}).get("duration", "")
                return f"{text} ({duration}ms)"

            # default value
            return "-"

        button_keys = ("left_btn", "middle_btn", "right_btn")
        return [get_button_content(btn_key) for btn_key in button_keys]

    def seed_words(self) -> list[str]:
        """Get all the seed words on the screen in order.

        Example content: "1. ladybug\n2. acid\n3. academic\n4. afraid"
          -> ["ladybug", "acid", "academic", "afraid"]
        """
        words: list[str] = []
        for line in self.screen_content().split("\n"):
            # Dot after index is optional (present on TT, not on TR)
            match = re.match(r"^\s*\d+\.? (\w+)$", line)
            if match:
                words.append(match.group(1))
        return words

    def pin(self) -> str:
        """Get PIN from the layout."""
        assert "PinKeyboard" in self.all_components()
        return self.find_unique_value_by_key("pin", default="", only_type=str)

    def passphrase(self) -> str:
        """Get passphrase from the layout."""
        assert "PassphraseKeyboard" in self.all_components()
        return self.find_unique_value_by_key("passphrase", default="", only_type=str)

    def page_count(self) -> int:
        """Get number of pages for the layout."""
        return (
            self.find_unique_value_by_key(
                "scrollbar_page_count", default=0, only_type=int
            )
            or self.find_unique_value_by_key("page_count", default=0, only_type=int)
            or 1
        )

    def active_page(self) -> int:
        """Get current page index of the layout."""
        return self.find_unique_value_by_key("active_page", default=0, only_type=int)

    def tt_pin_digits_order(self) -> str:
        """In what order the PIN buttons are shown on the screen. Only for TT."""
        return self.top_level_value("digits_order") or "no digits order"

    def get_middle_choice(self) -> str:
        """What is the choice being selected right now."""
        return self.choice_items()[1]

    def choice_items(self) -> tuple[str, str, str]:
        """Getting actions for all three possible buttons."""
        choice_obj = self.find_unique_value_by_key(
            "choice_page", default={}, only_type=dict
        )
        if not choice_obj:
            raise RuntimeError("No choice_page object in trace")
        choice_keys = ("prev_choice", "current_choice", "next_choice")
        return tuple(
            choice_obj.get(choice, {}).get("content", "") for choice in choice_keys
        )

    def footer(self) -> str:
        footer = self.find_unique_object_with_key_and_value("component", "Footer")
        if not footer:
            return ""
        return footer.get("description", "") + " " + footer.get("instruction", "")

    def action_bar(self) -> str:
        action_bar = self.find_unique_object_with_key_and_value(
            "component", "ActionBar"
        )
        if not action_bar:
            return ""
        right_button = action_bar.get("right_button", "")
        left_button = action_bar.get("left_button", "")
        if isinstance(left_button, dict):
            left_button = left_button.get("text", "")
        if isinstance(right_button, dict):
            right_button = right_button.get("text", "")
        return left_button + " " + right_button


def multipage_content(layouts: list[LayoutContent]) -> str:
    """Get overall content from multiple-page layout."""
    return "".join(layout.text_content() for layout in layouts)


def _make_input_func(
    button: messages.DebugButton | None = None,
    physical_button: messages.DebugPhysicalButton | None = None,
    swipe: messages.DebugSwipeDirection | None = None,
) -> "InputFunc":
    decision = messages.DebugLinkDecision(
        button=button,
        physical_button=physical_button,
        swipe=swipe,
    )

    def input_func(
        self: "DebugLink",
        hold_ms: int | None = None,
    ) -> None:
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612
        decision.hold_ms = hold_ms
        self._decision(decision)

    return input_func  # type: ignore [Parameter name mismatch]


class DebugLink:
    def __init__(self, transport: "Transport", auto_interact: bool = True) -> None:
        self.transport = transport
        self.allow_interactions = auto_interact
        self.mapping = mapping.DEFAULT_MAPPING

        # To be set by TrezorClientDebugLink (is not known during creation time)
        self.model: models.TrezorModel | None = None
        self.version: tuple[int, int, int] = (0, 0, 0)

        # Where screenshots are being saved
        self.screenshot_recording_dir: str | None = None

        # For T1 screenshotting functionality in DebugUI
        self.t1_screenshot_directory: Path | None = None
        self.t1_screenshot_counter = 0

        self.waiting_for_layout_change = False

        self.input_wait_type = DebugWaitType.IMMEDIATE

    @property
    def legacy_ui(self) -> bool:
        """Differences between UI1 and UI2."""
        return self.version < (2, 6, 0)

    @property
    def legacy_debug(self) -> bool:
        """Differences in handling debug events and LayoutContent."""
        return self.version < (2, 6, 1)

    @property
    def has_global_layout(self) -> bool:
        """Differences in waiting for Global Layout objects."""
        return self.version >= (2, 8, 6)

    @property
    def responds_to_debuglink_in_usb_tiny(self) -> bool:
        """Whether a Trezor One can respond to DebugLinkGetState while waiting
        for a Button/Pin/Passphrase Ack."""
        return self.version >= (1, 11, 0)

    @property
    def layout_type(self) -> LayoutType:
        assert self.model is not None
        return LayoutType.from_model(self.model)

    @property
    def screen_buttons(self) -> ScreenButtons:
        return ScreenButtons(self.layout_type)

    @property
    def button_actions(self) -> ButtonActions:
        return ButtonActions(self.layout_type)

    def open(self) -> None:
        self.transport.begin_session()

    def close(self) -> None:
        self.transport.end_session()

    def _write(self, msg: protobuf.MessageType) -> None:
        if self.waiting_for_layout_change:
            raise RuntimeError(
                "Debuglink is unavailable while waiting for layout change."
            )

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

    def _read(self, timeout: float | None = None) -> protobuf.MessageType:
        ret_type, ret_bytes = self.transport.read(timeout=timeout)
        LOG.log(
            DUMP_BYTES,
            f"received type {ret_type} ({len(ret_bytes)} bytes): {ret_bytes.hex()}",
        )
        msg = self.mapping.decode(ret_type, ret_bytes)

        # Collapse tokens to make log use less lines.
        msg_for_log = msg
        if isinstance(msg, (messages.DebugLinkState, messages.DebugLinkLayout)):
            msg_for_log = deepcopy(msg)
            msg_for_log.tokens = ["".join(msg_for_log.tokens)]

        LOG.debug(
            f"received message: {msg_for_log.__class__.__name__}",
            extra={"protobuf": msg_for_log},
        )
        return msg

    def _call(self, msg: protobuf.MessageType, timeout: float | None = None) -> Any:
        self._write(msg)
        return self._read(timeout=timeout)

    def state(self, wait_type: DebugWaitType | None = None) -> messages.DebugLinkState:
        if wait_type is None:
            wait_type = (
                DebugWaitType.CURRENT_LAYOUT
                if self.has_global_layout
                else DebugWaitType.IMMEDIATE
            )
        result = self._call(messages.DebugLinkGetState(wait_layout=wait_type))
        while not isinstance(result, (messages.Failure, messages.DebugLinkState)):
            result = self._read()
        if isinstance(result, messages.Failure):
            raise TrezorFailure(result)
        return result

    def read_layout(self, wait: bool | None = None) -> LayoutContent:
        """
        Force waiting for the layout by setting `wait=True`. Force not waiting by
        setting `wait=False` -- useful when, e.g., you are causing the next layout to be
        deliberately delayed.
        """
        if wait is True:
            wait_type = DebugWaitType.CURRENT_LAYOUT
        elif wait is False:
            wait_type = DebugWaitType.IMMEDIATE
        else:
            wait_type = None
        return LayoutContent(self.state(wait_type=wait_type).tokens)

    def wait_layout(self, wait_for_external_change: bool = False) -> LayoutContent:
        # Next layout change will be caused by external event
        # (e.g. device being auto-locked or as a result of device_handler.run(xxx))
        # and not by our debug actions/decisions.
        # Resetting the debug state so we wait for the next layout change
        # (and do not return the current state).
        if wait_for_external_change:
            self.reset_debug_events()

        obj = self._call(
            messages.DebugLinkGetState(wait_layout=DebugWaitType.NEXT_LAYOUT)
        )
        if isinstance(obj, messages.Failure):
            raise TrezorFailure(obj)
        return LayoutContent(obj.tokens)

    @contextmanager
    def wait_for_layout_change(self) -> Iterator[None]:
        # make sure some current layout is up by issuing a dummy GetState
        self.state()

        # send GetState without waiting for reply
        self._write(messages.DebugLinkGetState(wait_layout=DebugWaitType.NEXT_LAYOUT))

        # allow the block to proceed
        self.waiting_for_layout_change = True
        try:
            yield
        finally:
            self.waiting_for_layout_change = False

        # wait for the reply
        resp = self._read()
        assert isinstance(resp, messages.DebugLinkState)

    def reset_debug_events(self) -> None:
        # Only supported on TT and above certain version
        if (self.model is not models.T1B1) and not self.legacy_debug:
            return self._call(messages.DebugLinkResetDebugEvents())
        return None

    def synchronize_at(self, layout_text: str, timeout: float = 5) -> LayoutContent:
        now = time.monotonic()
        while True:
            layout = self.read_layout()
            if layout_text in layout.json_str:
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

    def encode_pin(self, pin: str, matrix: str | None = None) -> str:
        """Transform correct PIN according to the displayed matrix."""
        if matrix is None:
            matrix = self.state().matrix
            if matrix is None:
                # we are on trezor-core
                return pin

        return "".join([str(matrix.index(p) + 1) for p in pin])

    def read_recovery_word(self) -> Tuple[str | None, int | None]:
        state = self.state()
        return (state.recovery_fake_word, state.recovery_word_pos)

    def read_reset_word(self) -> str:
        state = self._call(messages.DebugLinkGetState(wait_word_list=True))
        return state.reset_word

    def _decision(
        self, decision: messages.DebugLinkDecision, wait: bool | None = None
    ) -> None:
        """Send a debuglink decision.

        If hold_ms is set, an additional 200ms is added to account for processing
        delays. (This is needed for hold-to-confirm to trigger reliably.)

        If `wait` is unset, the following wait mode is used:

        - `IMMEDIATE`, when in normal tests, which never deadlocks the device, but may
          return an empty layout in case the next one didn't come up immediately. (E.g.,
          in SignTx flow, the device is waiting for more TxRequest/TxAck exchanges
          before showing the next UI layout.)
        - `CURRENT_LAYOUT`, when in tests running through a `DeviceHandler`. This mode
          returns the current layout or waits for some layout to come up if there is
          none at the moment. The assumption is that wirelink is communicating on
          another thread and won't be blocked by waiting on debuglink.

        Force waiting for the layout by setting `wait=True`. Force not waiting by
        setting `wait=False` -- useful when, e.g., you are causing the next layout to be
        deliberately delayed.
        """
        if not self.allow_interactions:
            self.wait_layout()
            return

        if decision.hold_ms is not None:
            decision.hold_ms += 200

        self._write(decision)
        if self.model is models.T1B1:
            return

        if wait is True:
            wait_type = DebugWaitType.CURRENT_LAYOUT
        elif wait is False:
            wait_type = DebugWaitType.IMMEDIATE
        else:
            wait_type = self.input_wait_type

        # When the call below returns, we know that `decision` has been processed in Core.
        # XXX Due to a bug, the reply may get lost at the end of a workflow.
        # We assume that no single input event takes more than 5 seconds to process,
        # and give up waiting after that.
        try:
            msg = messages.DebugLinkGetState(
                wait_layout=wait_type,
                return_empty_state=True,
            )
            self._call(msg, timeout=5)
        except Timeout as e:
            LOG.warning("timeout waiting for DebugLinkState: %s", e)

    press_yes = _make_input_func(button=messages.DebugButton.YES)
    """Confirm current layout. See `_decision` for more details."""
    press_no = _make_input_func(button=messages.DebugButton.NO)
    """Reject current layout. See `_decision` for more details."""
    press_info = _make_input_func(button=messages.DebugButton.INFO)
    """Trigger the Info action. See `_decision` for more details."""
    swipe_up = _make_input_func(swipe=messages.DebugSwipeDirection.UP)
    """Swipe up. See `_decision` for more details."""
    swipe_down = _make_input_func(swipe=messages.DebugSwipeDirection.DOWN)
    """Swipe down. See `_decision` for more details."""
    swipe_right = _make_input_func(swipe=messages.DebugSwipeDirection.RIGHT)
    """Swipe right. See `_decision` for more details."""
    swipe_left = _make_input_func(swipe=messages.DebugSwipeDirection.LEFT)
    """Swipe left. See `_decision` for more details."""
    press_left = _make_input_func(physical_button=messages.DebugPhysicalButton.LEFT_BTN)
    """Press left button. See `_decision` for more details."""
    press_middle = _make_input_func(
        physical_button=messages.DebugPhysicalButton.MIDDLE_BTN
    )
    """Press middle button. See `_decision` for more details."""
    press_right = _make_input_func(
        physical_button=messages.DebugPhysicalButton.RIGHT_BTN
    )
    """Press right button. See `_decision` for more details."""

    def input(self, word: str) -> None:
        """Send text input to the device. See `_decision` for more details."""
        self._decision(messages.DebugLinkDecision(input=word))

    def click(
        self,
        click: Tuple[int, int],
        hold_ms: int | None = None,
        wait: bool | None = None,
    ) -> None:
        """Send a click to the device. See `_decision` for more details."""
        x, y = click
        self._decision(messages.DebugLinkDecision(x=x, y=y, hold_ms=hold_ms), wait=wait)

    def stop(self) -> None:
        self._write(messages.DebugLinkStop())

    def reseed(self, value: int) -> protobuf.MessageType:
        return self._call(messages.DebugLinkReseedRandom(value=value))

    def start_recording(self, directory: str, refresh_index: int | None = None) -> None:
        self.screenshot_recording_dir = directory
        # Different recording logic between core and legacy
        if self.model is not models.T1B1:
            self._call(
                messages.DebugLinkRecordScreen(
                    target_directory=directory, refresh_index=refresh_index
                )
            )
        else:
            self.t1_screenshot_directory = Path(directory)
            self.t1_screenshot_counter = 0
            self.t1_take_screenshots = True

    def stop_recording(self) -> None:
        self.screenshot_recording_dir = None
        # Different recording logic between TT and T1
        if self.model is not models.T1B1:
            self._call(messages.DebugLinkRecordScreen(target_directory=None))
        else:
            self.t1_take_screenshots = False

    def memory_read(self, address: int, length: int) -> bytes:
        return self._call(
            messages.DebugLinkMemoryRead(address=address, length=length)
        ).memory

    def memory_write(self, address: int, memory: bytes, flash: bool = False) -> None:
        self._write(
            messages.DebugLinkMemoryWrite(address=address, memory=memory, flash=flash)
        )

    def flash_erase(self, sector: int) -> None:
        self._write(messages.DebugLinkFlashErase(sector=sector))

    def erase_sd_card(self, format: bool = True) -> messages.Success:
        res = self._call(messages.DebugLinkEraseSdCard(format=format))
        if not isinstance(res, messages.Success):
            raise UnexpectedMessageError(messages.Success, res)
        return res

    def snapshot_legacy(self) -> None:
        """Snapshot the current state of the device."""
        if self.model is not models.T1B1:
            return

        if not self.responds_to_debuglink_in_usb_tiny:
            return

        state = self.state()
        if state.layout is not None:
            self._save_screenshot_t1(state.layout)

    def _save_screenshot_t1(self, data: bytes) -> None:
        if self.t1_screenshot_directory is None:
            return

        from PIL import Image

        assert len(data) == 128 * 64 // 8

        pixels: list[int] = []
        for byteline in range(64 // 8):
            offset = byteline * 128
            row = data[offset : offset + 128]
            for bit in range(8):
                pixels.extend(bool(px & (1 << bit)) for px in row)

        im = Image.new("1", (128, 64))
        im.putdata(pixels[::-1])

        img_location = (
            self.t1_screenshot_directory / f"{self.t1_screenshot_counter:04d}.png"
        )
        im.save(img_location)
        self.t1_screenshot_counter += 1


del _make_input_func


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
    ) -> messages.DebugLinkState | None:
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
        self.pins: Iterator[str] | None = None
        self.passphrase = ""
        self.input_flow: Union[
            Generator[None, messages.ButtonRequest, None], object, None
        ] = None

    def _default_input_flow(self, br: messages.ButtonRequest) -> None:
        if br.code == messages.ButtonRequestType.PinEntry:
            self.debuglink.input(self.get_pin())
        else:
            # Paginating (going as further as possible) and pressing Yes
            if br.pages is not None:
                for _ in range(br.pages - 1):
                    if self.debuglink.model is models.T3W1:
                        self.debuglink.click(self.debuglink.screen_buttons.ok())
                    else:
                        self.debuglink.swipe_up()

            if self.debuglink.model is models.T3T1:
                layout = self.debuglink.read_layout()
                if "PromptScreen" in layout.all_components():
                    self.debuglink.press_yes()
                elif "SwipeContent" in layout.all_components():
                    self.debuglink.swipe_up()
                else:
                    self.debuglink.press_yes()
            elif self.debuglink.model is models.T3W1:
                layout = self.debuglink.read_layout()
                if "TextScreen" in layout.all_components():
                    self.debuglink.click(self.debuglink.screen_buttons.ok())
                else:
                    self.debuglink.press_yes()
            else:
                self.debuglink.press_yes()

    def button_request(self, br: messages.ButtonRequest) -> None:
        self.debuglink.snapshot_legacy()

        if self.input_flow is None:
            self._default_input_flow(br)
        elif self.input_flow is self.INPUT_FLOW_DONE:
            raise AssertionError("input flow ended prematurely")
        else:
            try:
                assert isinstance(self.input_flow, Generator)
                self.input_flow.send(br)
            except StopIteration:
                self.input_flow = self.INPUT_FLOW_DONE

    def get_pin(self, code: PinMatrixRequestType | None = None) -> str:
        self.debuglink.snapshot_legacy()

        if self.pins is None:
            raise RuntimeError("PIN requested but no sequence was configured")

        try:
            return self.debuglink.encode_pin(next(self.pins))
        except StopIteration:
            raise AssertionError("PIN sequence ended prematurely")

    def get_passphrase(self, available_on_device: bool) -> str:
        self.debuglink.snapshot_legacy()
        return self.passphrase


class MessageFilter:
    def __init__(self, message_type: type[protobuf.MessageType], **fields: Any) -> None:
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
        if type(message) is not self.message_type:
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
        fields: list[Tuple[str, str]] = []
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
            item: list[str] = []
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

        # set transport explicitly so that sync_responses can work
        self.transport = transport

        self.reset_debug_features()
        self.sync_responses()
        super().__init__(transport, ui=self.ui)

        # So that we can choose right screenshotting logic (T1 vs TT)
        # and know the supported debug capabilities
        self.debug.model = self.model
        self.debug.version = self.version

    @property
    def layout_type(self) -> LayoutType:
        return self.debug.layout_type

    def reset_debug_features(self) -> None:
        """Prepare the debugging client for a new testcase.

        Clears all debugging state that might have been modified by a testcase.
        """
        self.ui: DebugUI = DebugUI(self.debug)
        self.in_with_statement = False
        self.expected_responses: list[MessageFilter] | None = None
        self.actual_responses: list[protobuf.MessageType] | None = None
        self.filters: dict[
            type[protobuf.MessageType],
            Callable[[protobuf.MessageType], protobuf.MessageType] | None,
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
        message_type: type[protobuf.MessageType],
        callback: Callable[[protobuf.MessageType], protobuf.MessageType] | None,
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
        self, input_flow: InputFlowType | Callable[[], InputFlowType]
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
        next(input_flow)  # start the generator

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

        # grab a copy of the inputflow generator to raise an exception through it
        if isinstance(self.ui, DebugUI):
            input_flow = self.ui.input_flow
        else:
            input_flow = None

        self.reset_debug_features()

        if exc_type is None:
            # If no other exception was raised, evaluate missed responses
            # (raises AssertionError on mismatch)
            self._verify_responses(expected_responses, actual_responses)

        elif isinstance(input_flow, Generator):
            # Propagate the exception through the input flow, so that we see in
            # traceback where it is stuck.
            input_flow.throw(exc_type, value, traceback)

    def set_expected_responses(
        self,
        expected: Sequence[Union["ExpectedMessage", Tuple[bool, "ExpectedMessage"]]],
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
    def _expectation_lines(expected: list[MessageFilter], current: int) -> list[str]:
        start_at = max(current - EXPECTED_RESPONSES_CONTEXT_LINES, 0)
        stop_at = min(current + EXPECTED_RESPONSES_CONTEXT_LINES + 1, len(expected))
        output: list[str] = []
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
        expected: list[MessageFilter] | None,
        actual: list[protobuf.MessageType] | None,
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

    def sync_responses(self) -> None:
        """Synchronize Trezor device receiving with caller.

        When a failed test does not read out the response, the next caller will write
        a request, but read the previous response -- while the device had already sent
        and placed into queue the new response.

        This function will call `Ping` and read responses until it locates a `Success`
        with the expected text. This means that we are reading up-to-date responses.
        """
        import secrets

        # Start by canceling whatever is on screen. This will work to cancel T1 PIN
        # prompt, which is in TINY mode and does not respond to `Ping`.
        cancel_msg = mapping.DEFAULT_MAPPING.encode(messages.Cancel())
        self.transport.begin_session()
        try:
            self.transport.write(*cancel_msg)

            message = "SYNC" + secrets.token_hex(8)
            ping_msg = mapping.DEFAULT_MAPPING.encode(messages.Ping(message=message))
            self.transport.write(*ping_msg)
            resp = None
            while resp != messages.Success(message=message):
                msg_id, msg_bytes = self.transport.read()
                try:
                    resp = mapping.DEFAULT_MAPPING.decode(msg_id, msg_bytes)
                except Exception:
                    pass
        finally:
            self.transport.end_session()

    def mnemonic_callback(self, _) -> str:
        word, pos = self.debug.read_recovery_word()
        if word:
            return word
        if pos:
            return self.mnemonic[pos - 1]

        raise RuntimeError("Unexpected call")


def load_device(
    client: "TrezorClient",
    mnemonic: Union[str, Iterable[str]],
    pin: str | None,
    passphrase_protection: bool,
    label: str | None,
    skip_checksum: bool = False,
    needs_backup: bool = False,
    no_backup: bool = False,
    _skip_init_device: bool = False,
) -> None:
    if isinstance(mnemonic, str):
        mnemonic = [mnemonic]

    mnemonics = [Mnemonic.normalize_string(m) for m in mnemonic]

    if client.features.initialized:
        raise RuntimeError(
            "Device is initialized already. Call device.wipe() and try again."
        )

    client.call(
        messages.LoadDevice(
            mnemonics=mnemonics,
            pin=pin,
            passphrase_protection=passphrase_protection,
            label=label,
            skip_checksum=skip_checksum,
            needs_backup=needs_backup,
            no_backup=no_backup,
        ),
        expect=messages.Success,
    )
    if not _skip_init_device:
        client.init_device()


# keep the old name for compatibility
load_device_by_mnemonic = load_device


def prodtest_t1(client: "TrezorClient") -> None:
    if client.features.bootloader_mode is not True:
        raise RuntimeError("Device must be in bootloader mode")

    client.call(
        messages.ProdTestT1(
            payload=b"\x00\xFF\x55\xAA\x66\x99\x33\xCCABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!\x00\xFF\x55\xAA\x66\x99\x33\xCC"
        ),
        expect=messages.Success,
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


def optiga_set_sec_max(client: "TrezorClient") -> None:
    client.call(messages.DebugLinkOptigaSetSecMax(), expect=messages.Success)


class ScreenButtons:
    def __init__(self, layout_type: LayoutType):
        assert layout_type in (LayoutType.Bolt, LayoutType.Delizia, LayoutType.Eckhart)
        self.layout_type = layout_type

    def _width(self) -> int:
        if self.layout_type in (LayoutType.Bolt, LayoutType.Delizia):
            return 240
        elif self.layout_type is LayoutType.Eckhart:
            return 380
        else:
            raise ValueError("Wrong layout type")

    def _height(self) -> int:
        if self.layout_type in (LayoutType.Bolt, LayoutType.Delizia):
            return 240
        elif self.layout_type is LayoutType.Eckhart:
            return 520
        else:
            raise ValueError("Wrong layout type")

    def _grid(self, dim: int, grid_cells: int, cell: int) -> int:
        assert cell < grid_cells
        step = dim // grid_cells
        ofs = step // 2
        return cell * step + ofs

    # 3 columns, 4 rows, 1st row is input area
    def _grid35(self, x: int, y: int) -> Coords:
        assert x < 3, y < 5
        return self._grid(self._width(), 3, x), self._grid(self._height(), 5, y)

    def _grid55(self, x: int, y: int) -> Coords:
        assert x < 5, y < 5
        return self._grid(self._width(), 5, x), self._grid(self._height(), 5, y)

    # TODO: do not expose this
    # 3 columns, 3 rows, 1st row is input area
    def grid34(self, x: int, y: int) -> Coords:
        assert x < 3, y < 4
        return self._grid(self._width(), 3, x), self._grid(self._height(), 4, y)

    # 2 columns, 3 rows, first two are header and description
    def _grid25(self, x: int, y: int) -> Coords:
        assert x < 2, y < 5
        return self._grid(self._width(), 2, x), self._grid(self._height(), 5, y)

    # Horizontal coordinates
    def _left(self) -> int:
        return self._grid(self._width(), 3, 0)

    def _mid(self) -> int:
        return self._grid(self._width(), 3, 1)

    def _right(self) -> int:
        return self._grid(self._width(), 3, 2)

    # Vertical coordinates
    def _top(self) -> int:
        return self._grid(self._height(), 6, 0)

    def _bottom(self) -> int:
        return self._grid(self._height(), 6, 5)

    # Buttons

    # Right bottom
    def ok(self) -> Coords:
        return (self._right(), self._bottom())

    # Left bottom
    def cancel(self) -> Coords:
        return (self._left(), self._bottom())

    # Mid bottom
    def info(self) -> Coords:
        return (self._mid(), self._bottom())

    # Menu/close menu button
    def menu(self) -> Coords:
        return self._grid55(4, 0)

    # Center of the screen
    def tap_to_confirm(self) -> Coords:
        assert self.layout_type is LayoutType.Delizia
        return (self._grid(self._width(), 1, 0), self._grid(self._width(), 1, 0))

    # Yes/No decision component
    def ui_yes(self) -> Coords:
        if self.layout_type is LayoutType.Delizia:
            return self.grid34(2, 2)
        elif self.layout_type is LayoutType.Eckhart:
            return self.ok()
        else:
            raise ValueError("Wrong layout type")

    def ui_no(self) -> Coords:
        if self.layout_type is LayoutType.Delizia:
            return self.grid34(0, 2)
        elif self.layout_type is LayoutType.Eckhart:
            return self.cancel()
        else:
            raise ValueError("Wrong layout type")

    # +/- buttons in number input component
    def number_input_minus(self) -> Coords:
        if self.layout_type is LayoutType.Bolt:
            return (self._left(), self._grid(self._height(), 5, 1))
        elif self.layout_type is LayoutType.Delizia:
            return (self._left(), self._grid(self._height(), 5, 3))
        elif self.layout_type is LayoutType.Eckhart:
            return self.grid34(0, 2)
        else:
            raise ValueError("Wrong layout type")

    def number_input_plus(self) -> Coords:
        if self.layout_type is LayoutType.Bolt:
            return (self._right(), self._grid(self._height(), 5, 1))
        elif self.layout_type is LayoutType.Delizia:
            return (self._right(), self._grid(self._height(), 5, 3))
        elif self.layout_type is LayoutType.Eckhart:
            return self.grid34(2, 2)
        else:
            raise ValueError("Wrong layout type")

    def word_count_all_word(self, word_count: int) -> Coords:
        assert word_count in (12, 18, 20, 24, 33)
        if self.layout_type is LayoutType.Bolt:
            coords_map = {
                12: self.grid34(0, 2),
                18: self.grid34(1, 2),
                20: self.grid34(2, 2),
                24: self.grid34(1, 3),
                33: self.grid34(2, 3),
            }
        elif self.layout_type is LayoutType.Delizia:
            coords_map = {
                12: self.grid34(0, 1),
                18: self.grid34(2, 1),
                20: self.grid34(0, 2),
                24: self.grid34(2, 2),
                33: self.grid34(2, 3),
            }
        elif self.layout_type is LayoutType.Eckhart:
            coords_map = {
                12: self._grid35(0, 2),
                18: self._grid35(2, 2),
                20: self._grid35(0, 3),
                24: self._grid35(2, 3),
                33: self._grid35(2, 4),
            }
        else:
            raise ValueError("Wrong layout type")

        return coords_map[word_count]

    def word_count_all_cancel(self) -> Coords:
        if self.layout_type is LayoutType.Bolt:
            return self.grid34(0, 3)
        elif self.layout_type is LayoutType.Delizia:
            return self.grid34(0, 3)
        elif self.layout_type is LayoutType.Eckhart:
            return self._grid35(0, 4)
        else:
            raise ValueError("Wrong layout type")

    def word_count_repeated_word(self, word_count: int) -> Coords:
        assert word_count in (20, 33)
        if self.layout_type is LayoutType.Bolt:
            coords_map = {
                20: self.grid34(1, 2),
                33: self.grid34(2, 2),
            }
        elif self.layout_type is LayoutType.Delizia:
            coords_map = {
                20: self.grid34(0, 1),
                33: self.grid34(2, 1),
            }
        elif self.layout_type is LayoutType.Eckhart:
            coords_map = {
                20: self._grid35(1, 2),
                33: self._grid35(1, 3),
            }
        else:
            raise ValueError("Wrong layout type")

        return coords_map[word_count]

    def word_count_repeated_cancel(self) -> Coords:
        if self.layout_type is LayoutType.Bolt:
            return self.grid34(0, 2)
        elif self.layout_type is LayoutType.Delizia:
            return self.grid34(0, 3)
        elif self.layout_type is LayoutType.Eckhart:
            return self._grid35(1, 4)
        else:
            raise ValueError("Wrong layout type")

    # select word component buttons
    def word_check_words(self) -> "list[Coords]":
        if self.layout_type in (LayoutType.Bolt, LayoutType.Delizia):
            return [
                (self._mid(), self._grid(self._height(), 4, 1)),
                (self._mid(), self._grid(self._height(), 4, 2)),
                (self._mid(), self._grid(self._height(), 4, 3)),
            ]
        elif self.layout_type is LayoutType.Eckhart:
            return [
                (self._mid(), self._grid(self._height(), 5, 2)),
                (self._mid(), self._grid(self._height(), 5, 3)),
                (self._mid(), self._grid(self._height(), 5, 4)),
            ]
        else:
            raise ValueError("Wrong layout type")

    # vertical menu buttons
    def vertical_menu_items(self) -> "list[Coords]":
        if self.layout_type is LayoutType.Delizia:
            return [
                (self._mid(), self._grid(self._height(), 4, 1)),
                (self._mid(), self._grid(self._height(), 4, 2)),
                (self._mid(), self._grid(self._height(), 4, 3)),
            ]
        elif self.layout_type is LayoutType.Eckhart:
            return [
                (self._mid(), self._grid(self._height(), 5, 1)),
                (self._mid(), self._grid(self._height(), 5, 2)),
                (self._mid(), self._grid(self._height(), 5, 3)),
            ]
        else:
            raise ValueError("Wrong layout type")

    # Pin/passphrase keyboards
    def pin_passphrase_index(self, idx: int) -> Coords:
        assert idx < 10
        if idx == 9:
            idx = 10  # last digit is in the middle
        return self.pin_passphrase_grid(idx % 3, idx // 3)

    def pin_passphrase_grid(self, x: int, y: int) -> Coords:
        y += 1  # first line is empty
        return self._grid35(x, y)

    # PIN/passphrase input
    def pin_passphrase_input(self) -> Coords:
        return (self._mid(), self._top())

    def pin_passphrase_erase(self) -> Coords:
        return self.pin_passphrase_grid(0, 3)

    def passphrase_confirm(self) -> Coords:
        if self.layout_type in (LayoutType.Bolt, LayoutType.Eckhart):
            return self.pin_passphrase_grid(2, 3)
        elif self.layout_type is LayoutType.Delizia:
            return self._grid55(4, 0)
        else:
            raise ValueError("Wrong layout type")

    def pin_confirm(self) -> Coords:
        return self.pin_passphrase_grid(2, 3)

    # Mnemonic keyboard
    def mnemonic_from_index(self, idx: int) -> Coords:
        assert idx < 9
        return self.mnemonic_grid(idx)

    def mnemonic_grid(self, idx: int) -> Coords:
        grid_x = idx % 3
        grid_y = idx // 3 + 1  # first line is empty
        if self.layout_type in (LayoutType.Bolt, LayoutType.Delizia):
            return self.grid34(grid_x, grid_y)
        elif self.layout_type is LayoutType.Eckhart:
            return self._grid35(grid_x, grid_y)
        else:
            raise ValueError("Wrong layout type")

    def mnemonic_erase(self) -> Coords:
        if self.layout_type in (LayoutType.Bolt, LayoutType.Delizia):
            return (self._left(), self._top())
        elif self.layout_type is LayoutType.Eckhart:
            return self._grid35(0, 4)
        else:
            raise ValueError("Wrong layout type")

    def mnemonic_confirm(self) -> Coords:
        if self.layout_type in (LayoutType.Bolt, LayoutType.Delizia):
            return (self._mid(), self._top())
        elif self.layout_type is LayoutType.Eckhart:
            return self._grid35(2, 4)
        else:
            raise ValueError("Wrong layout type")


BUTTON_LETTERS_BIP39 = ("abc", "def", "ghi", "jkl", "mno", "pqr", "stu", "vwx", "yz")
BUTTON_LETTERS_SLIP39 = ("ab", "cd", "ef", "ghij", "klm", "nopq", "rs", "tuv", "wxyz")

# fmt: off
PASSPHRASE_LOWERCASE_BOLT = (" ", "abc", "def", "ghi", "jkl", "mno", "pqrs", "tuv", "wxyz", "*#")
PASSPHRASE_LOWERCASE_DE = ("abc", "def", "ghi", "jkl", "mno", "pq", "rst", "uvw", "xyz", " *#")
PASSPHRASE_UPPERCASE_BOLT = (" ", "ABC", "DEF", "GHI", "JKL", "MNO", "PQRS", "TUV", "WXYZ", "*#")
PASSPHRASE_UPPERCASE_DE = ("ABC", "DEF", "GHI", "JKL", "MNO", "PQ", "RST", "UVW", "XYZ", " *#")
PASSPHRASE_DIGITS = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "0")
PASSPHRASE_SPECIAL = ("_<>", ".:@", "/|\\", "!()", "+%&", "-[]", "?{}", ",'`", ";\"~", "$^=")
# fmt: on


class ButtonActions:
    def __init__(self, layout_type: LayoutType):
        self.buttons = ScreenButtons(layout_type)

    def _passphrase_choices(self, char: str) -> "tuple[str, ...]":
        if char in " *#" or char.islower():
            if self.buttons.layout_type is LayoutType.Bolt:
                return PASSPHRASE_LOWERCASE_BOLT
            elif self.buttons.layout_type in (LayoutType.Delizia, LayoutType.Eckhart):
                return PASSPHRASE_LOWERCASE_DE
            else:
                raise ValueError("Wrong layout type")
        elif char.isupper():
            if self.buttons.layout_type is LayoutType.Bolt:
                return PASSPHRASE_UPPERCASE_BOLT
            elif self.buttons.layout_type in (LayoutType.Delizia, LayoutType.Eckhart):
                return PASSPHRASE_UPPERCASE_DE
            else:
                raise ValueError("Wrong layout type")
        elif char.isdigit():
            return PASSPHRASE_DIGITS
        else:
            return PASSPHRASE_SPECIAL

    def passphrase(self, char: str) -> Tuple[Coords, int]:
        choices = self._passphrase_choices(char)
        idx = next(i for i, letters in enumerate(choices) if char in letters)
        click_amount = choices[idx].index(char) + 1
        return self.buttons.pin_passphrase_index(idx), click_amount

    def type_word(self, word: str, is_slip39: bool = False) -> Iterator[Coords]:
        if is_slip39:
            yield from self._type_word_slip39(word)
        else:
            yield from self._type_word_bip39(word)

    def _type_word_slip39(self, word: str) -> Iterator[Coords]:
        for l in word:
            idx = next(
                i for i, letters in enumerate(BUTTON_LETTERS_SLIP39) if l in letters
            )
            yield self.buttons.mnemonic_from_index(idx)

    def _type_word_bip39(self, word: str) -> Iterator[Coords]:
        coords_prev: Coords | None = None
        for letter in word:
            time.sleep(0.1)  # not being so quick to miss something
            coords, amount = self._letter_coords_and_amount(letter)
            # If the button is the same as for the previous letter,
            # waiting a second before pressing it again.
            if coords == coords_prev:
                time.sleep(1.1)
            coords_prev = coords
            for _ in range(amount):
                yield coords

    def _letter_coords_and_amount(self, letter: str) -> Tuple[Coords, int]:
        idx = next(
            i for i, letters in enumerate(BUTTON_LETTERS_BIP39) if letter in letters
        )
        click_amount = BUTTON_LETTERS_BIP39[idx].index(letter) + 1
        return self.buttons.mnemonic_from_index(idx), click_amount
