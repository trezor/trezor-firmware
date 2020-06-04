# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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
from collections import namedtuple
from copy import deepcopy

from mnemonic import Mnemonic

from . import mapping, messages, protobuf
from .client import TrezorClient
from .log import DUMP_BYTES
from .tools import expect

EXPECTED_RESPONSES_CONTEXT_LINES = 3

LayoutLines = namedtuple("LayoutLines", "lines text")

LOG = logging.getLogger(__name__)


def layout_lines(lines):
    return LayoutLines(lines, " ".join(lines))


class DebugLink:
    def __init__(self, transport, auto_interact=True):
        self.transport = transport
        self.allow_interactions = auto_interact

    def open(self):
        self.transport.begin_session()

    def close(self):
        self.transport.end_session()

    def _call(self, msg, nowait=False):
        LOG.debug(
            "sending message: {}".format(msg.__class__.__name__),
            extra={"protobuf": msg},
        )
        msg_type, msg_bytes = mapping.encode(msg)
        LOG.log(
            DUMP_BYTES,
            "encoded as type {} ({} bytes): {}".format(
                msg_type, len(msg_bytes), msg_bytes.hex()
            ),
        )
        self.transport.write(msg_type, msg_bytes)
        if nowait:
            return None

        ret_type, ret_bytes = self.transport.read()
        LOG.log(
            DUMP_BYTES,
            "received type {} ({} bytes): {}".format(
                msg_type, len(msg_bytes), msg_bytes.hex()
            ),
        )
        msg = mapping.decode(ret_type, ret_bytes)
        LOG.debug(
            "received message: {}".format(msg.__class__.__name__),
            extra={"protobuf": msg},
        )
        return msg

    def state(self):
        return self._call(messages.DebugLinkGetState())

    def read_layout(self):
        return layout_lines(self.state().layout_lines)

    def wait_layout(self):
        obj = self._call(messages.DebugLinkGetState(wait_layout=True))
        return layout_lines(obj.layout_lines)

    def watch_layout(self, watch: bool) -> None:
        """Enable or disable watching layouts.
        If disabled, wait_layout will not work.

        The message is missing on T1. Use `TrezorClientDebugLink.watch_layout` for
        cross-version compatibility.
        """
        self._call(messages.DebugLinkWatchLayout(watch=watch))

    def encode_pin(self, pin, matrix=None):
        """Transform correct PIN according to the displayed matrix."""
        if matrix is None:
            matrix = self.state().matrix
            if matrix is None:
                # we are on trezor-core
                return pin

        return "".join([str(matrix.index(p) + 1) for p in pin])

    def read_recovery_word(self):
        state = self.state()
        return (state.recovery_fake_word, state.recovery_word_pos)

    def read_reset_word(self):
        state = self._call(messages.DebugLinkGetState(wait_word_list=True))
        return state.reset_word

    def read_reset_word_pos(self):
        state = self._call(messages.DebugLinkGetState(wait_word_pos=True))
        return state.reset_word_pos

    def input(self, word=None, button=None, swipe=None, x=None, y=None, wait=False):
        if not self.allow_interactions:
            return

        args = sum(a is not None for a in (word, button, swipe, x))
        if args != 1:
            raise ValueError("Invalid input - must use one of word, button, swipe")

        decision = messages.DebugLinkDecision(
            yes_no=button, swipe=swipe, input=word, x=x, y=y, wait=wait
        )
        ret = self._call(decision, nowait=not wait)
        if ret is not None:
            return layout_lines(ret.lines)

    def click(self, click, wait=False):
        x, y = click
        return self.input(x=x, y=y, wait=wait)

    def press_yes(self):
        self.input(button=True)

    def press_no(self):
        self.input(button=False)

    def swipe_up(self):
        self.input(swipe=messages.DebugSwipeDirection.UP)

    def swipe_down(self):
        self.input(swipe=messages.DebugSwipeDirection.DOWN)

    def swipe_right(self):
        self.input(swipe=messages.DebugSwipeDirection.RIGHT)

    def swipe_left(self):
        self.input(swipe=messages.DebugSwipeDirection.LEFT)

    def stop(self):
        self._call(messages.DebugLinkStop(), nowait=True)

    def reseed(self, value):
        self._call(messages.DebugLinkReseedRandom(value=value))

    def start_recording(self, directory):
        self._call(messages.DebugLinkRecordScreen(target_directory=directory))

    def stop_recording(self):
        self._call(messages.DebugLinkRecordScreen(target_directory=None))

    @expect(messages.DebugLinkMemory, field="memory")
    def memory_read(self, address, length):
        return self._call(messages.DebugLinkMemoryRead(address=address, length=length))

    def memory_write(self, address, memory, flash=False):
        self._call(
            messages.DebugLinkMemoryWrite(address=address, memory=memory, flash=flash),
            nowait=True,
        )

    def flash_erase(self, sector):
        self._call(messages.DebugLinkFlashErase(sector=sector), nowait=True)

    @expect(messages.Success)
    def erase_sd_card(self, format=True):
        return self._call(messages.DebugLinkEraseSdCard(format=format))


class NullDebugLink(DebugLink):
    def __init__(self):
        super().__init__(None)

    def open(self):
        pass

    def close(self):
        pass

    def _call(self, msg, nowait=False):
        if not nowait:
            if isinstance(msg, messages.DebugLinkGetState):
                return messages.DebugLinkState()
            else:
                raise RuntimeError("unexpected call to a fake debuglink")


class DebugUI:
    INPUT_FLOW_DONE = object()

    def __init__(self, debuglink: DebugLink):
        self.debuglink = debuglink
        self.clear()

    def clear(self):
        self.pins = None
        self.passphrase = ""
        self.input_flow = None

    def button_request(self, code):
        if self.input_flow is None:
            if code == messages.ButtonRequestType.PinEntry:
                self.debuglink.input(self.get_pin())
            else:
                self.debuglink.press_yes()
        elif self.input_flow is self.INPUT_FLOW_DONE:
            raise AssertionError("input flow ended prematurely")
        else:
            try:
                self.input_flow.send(code)
            except StopIteration:
                self.input_flow = self.INPUT_FLOW_DONE

    def get_pin(self, code=None):
        if self.pins is None:
            raise RuntimeError("PIN requested but no sequence was configured")

        try:
            return self.debuglink.encode_pin(next(self.pins))
        except StopIteration:
            raise AssertionError("PIN sequence ended prematurely")

    def get_passphrase(self, available_on_device):
        return self.passphrase


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

    def __init__(self, transport, auto_interact=True):
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

        self.ui = DebugUI(self.debug)

        self.in_with_statement = 0
        self.screenshot_id = 0

        self.filters = {}

        # Do not expect any specific response from device
        self.expected_responses = None
        self.current_response = None

        super().__init__(transport, ui=self.ui)

    def open(self):
        super().open()
        if self.session_counter == 1:
            self.debug.open()

    def close(self):
        if self.session_counter == 1:
            self.debug.close()
        super().close()

    def set_filter(self, message_type, callback):
        """Configure a filter function for a specified message type.

        The `callback` must be a function that accepts a protobuf message, and returns
        a (possibly modified) protobuf message of the same type. Whenever a message
        is sent or received that matches `message_type`, `callback` is invoked on the
        message and its result is substituted for the original.

        Useful for test scenarios with an active malicious actor on the wire.
        """
        self.filters[message_type] = callback

    def _filter_message(self, msg):
        message_type = msg.__class__
        callback = self.filters.get(message_type)
        if callable(callback):
            return callback(deepcopy(msg))
        else:
            return msg

    def set_input_flow(self, input_flow):
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

    def watch_layout(self, watch: bool) -> None:
        """Enable or disable watching layout changes.

        Happens implicitly in a `with client` block.

        Since trezor-core v2.3.2, it is necessary to call `watch_layout()` before
        using `debug.wait_layout()`, otherwise layout changes are not reported.
        """
        if self.version >= (2, 3, 2):
            # version check is necessary because otherwise we cannot reliably detect
            # whether and where to wait for reply:
            # - T1 reports unknown debuglink messages on the wirelink
            # - TT < 2.3.0 does not reply to unknown debuglink messages due to a bug
            self.debug.watch_layout(watch)

    def __enter__(self):
        # For usage in with/expected_responses
        self.in_with_statement += 1
        self.watch_layout(True)
        return self

    def __exit__(self, _type, value, traceback):
        self.in_with_statement -= 1

        # Clear input flow.
        try:
            if _type is not None:
                # Another exception raised
                return False

            if self.expected_responses is None:
                # no need to check anything else
                return False

            # Evaluate missed responses in 'with' statement
            if self.current_response < len(self.expected_responses):
                self._raise_unexpected_response(None)

        finally:
            # Cleanup
            self.expected_responses = None
            self.current_response = None
            self.ui.clear()
            self.watch_layout(False)

        return False

    def set_expected_responses(self, expected):
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
        expected_with_validity = [
            e if isinstance(e, tuple) else (True, e) for e in expected
        ]

        # only apply those items that are (True, message)
        self.expected_responses = [
            expected for valid, expected in expected_with_validity if valid
        ]

        self.current_response = 0

    def use_pin_sequence(self, pins):
        """Respond to PIN prompts from device with the provided PINs.
        The sequence must be at least as long as the expected number of PIN prompts.
        """
        self.ui.pins = iter(pins)

    def use_passphrase(self, passphrase):
        """Respond to passphrase prompts from device with the provided passphrase."""
        self.ui.passphrase = Mnemonic.normalize_string(passphrase)

    def use_mnemonic(self, mnemonic):
        """Use the provided mnemonic to respond to device.
        Only applies to T1, where device prompts the host for mnemonic words."""
        self.mnemonic = Mnemonic.normalize_string(mnemonic).split(" ")

    def _raw_read(self):
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612

        # if SCREENSHOT and self.debug:
        #     from PIL import Image

        #     layout = self.debug.state().layout
        #     im = Image.new("RGB", (128, 64))
        #     pix = im.load()
        #     for x in range(128):
        #         for y in range(64):
        #             rx, ry = 127 - x, 63 - y
        #             if (ord(layout[rx + (ry / 8) * 128]) & (1 << (ry % 8))) > 0:
        #                 pix[x, y] = (255, 255, 255)
        #     im.save("scr%05d.png" % self.screenshot_id)
        #     self.screenshot_id += 1

        resp = super()._raw_read()
        resp = self._filter_message(resp)
        self._check_request(resp)
        return resp

    def _raw_write(self, msg):
        return super()._raw_write(self._filter_message(msg))

    def _raise_unexpected_response(self, msg):
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612

        start_at = max(self.current_response - EXPECTED_RESPONSES_CONTEXT_LINES, 0)
        stop_at = min(
            self.current_response + EXPECTED_RESPONSES_CONTEXT_LINES + 1,
            len(self.expected_responses),
        )
        output = []
        output.append("Expected responses:")
        if start_at > 0:
            output.append("    (...{} previous responses omitted)".format(start_at))
        for i in range(start_at, stop_at):
            exp = self.expected_responses[i]
            prefix = "    " if i != self.current_response else ">>> "
            set_fields = {
                key: value
                for key, value in exp.__dict__.items()
                if value is not None and value != []
            }
            oneline_str = ", ".join("{}={!r}".format(*i) for i in set_fields.items())
            if len(oneline_str) < 60:
                output.append(
                    "{}{}({})".format(prefix, exp.__class__.__name__, oneline_str)
                )
            else:
                item = []
                item.append("{}{}(".format(prefix, exp.__class__.__name__))
                for key, value in set_fields.items():
                    item.append("{}    {}={!r}".format(prefix, key, value))
                item.append("{})".format(prefix))
                output.append("\n".join(item))
        if stop_at < len(self.expected_responses):
            omitted = len(self.expected_responses) - stop_at
            output.append("    (...{} following responses omitted)".format(omitted))

        output.append("")
        if msg is not None:
            output.append("Actually received:")
            output.append(protobuf.format_message(msg))
        else:
            output.append("This message was never received.")
        raise AssertionError("\n".join(output))

    def _check_request(self, msg):
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612
        if self.expected_responses is None:
            return

        if self.current_response >= len(self.expected_responses):
            raise AssertionError(
                "No more messages were expected, but we got:\n"
                + protobuf.format_message(msg)
            )

        expected = self.expected_responses[self.current_response]

        if msg.__class__ != expected.__class__:
            self._raise_unexpected_response(msg)

        for field, value in expected.__dict__.items():
            if value is None or value == []:
                continue
            if getattr(msg, field) != value:
                self._raise_unexpected_response(msg)

        self.current_response += 1

    def mnemonic_callback(self, _):
        word, pos = self.debug.read_recovery_word()
        if word != "":
            return word
        if pos != 0:
            return self.mnemonic[pos - 1]

        raise RuntimeError("Unexpected call")


@expect(messages.Success, field="message")
def load_device(
    client,
    mnemonic,
    pin,
    passphrase_protection,
    label,
    language="en-US",
    skip_checksum=False,
    needs_backup=False,
    no_backup=False,
):
    if not isinstance(mnemonic, (list, tuple)):
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


@expect(messages.Success, field="message")
def self_test(client):
    if client.features.bootloader_mode is not True:
        raise RuntimeError("Device must be in bootloader mode")

    return client.call(
        messages.SelfTest(
            payload=b"\x00\xFF\x55\xAA\x66\x99\x33\xCCABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!\x00\xFF\x55\xAA\x66\x99\x33\xCC"
        )
    )


@expect(messages.Success, field="message")
def show_text(client, header_text, body_text, icon=None, icon_color=None):
    body_text = [
        messages.DebugLinkShowTextItem(style=style, content=content)
        for style, content in body_text
    ]
    msg = messages.DebugLinkShowText(
        header_text=header_text,
        body_text=body_text,
        header_icon=icon,
        icon_color=icon_color,
    )
    return client.call(msg)
