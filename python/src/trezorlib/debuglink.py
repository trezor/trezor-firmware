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

from collections import namedtuple
from copy import deepcopy

from mnemonic import Mnemonic

from . import mapping, messages as proto, protobuf
from .client import TrezorClient
from .tools import expect

EXPECTED_RESPONSES_CONTEXT_LINES = 3


LayoutLines = namedtuple("LayoutLines", "lines text")


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
        msg_type, msg_bytes = mapping.encode(msg)
        self.transport.write(msg_type, msg_bytes)
        if nowait:
            return None
        ret_type, ret_bytes = self.transport.read()
        return mapping.decode(ret_type, ret_bytes)

    def state(self):
        return self._call(proto.DebugLinkGetState())

    def read_layout(self):
        return layout_lines(self.state().layout_lines)

    def wait_layout(self):
        obj = self._call(proto.DebugLinkGetState(wait_layout=True))
        return layout_lines(obj.layout_lines)

    def read_pin(self):
        state = self.state()
        return state.pin, state.matrix

    def read_pin_encoded(self):
        return self.encode_pin(*self.read_pin())

    def encode_pin(self, pin, matrix=None):
        """Transform correct PIN according to the displayed matrix."""
        if matrix is None:
            _, matrix = self.read_pin()
        return "".join([str(matrix.index(p) + 1) for p in pin])

    def read_mnemonic_secret(self):
        obj = self._call(proto.DebugLinkGetState())
        return obj.mnemonic_secret

    def read_recovery_word(self):
        obj = self._call(proto.DebugLinkGetState())
        return (obj.recovery_fake_word, obj.recovery_word_pos)

    def read_reset_word(self):
        obj = self._call(proto.DebugLinkGetState(wait_word_list=True))
        return obj.reset_word

    def read_reset_word_pos(self):
        obj = self._call(proto.DebugLinkGetState(wait_word_pos=True))
        return obj.reset_word_pos

    def read_reset_entropy(self):
        obj = self._call(proto.DebugLinkGetState())
        return obj.reset_entropy

    def read_passphrase_protection(self):
        obj = self._call(proto.DebugLinkGetState())
        return obj.passphrase_protection

    def input(self, word=None, button=None, swipe=None, x=None, y=None, wait=False):
        if not self.allow_interactions:
            return

        args = sum(a is not None for a in (word, button, swipe, x))
        if args != 1:
            raise ValueError("Invalid input - must use one of word, button, swipe")

        decision = proto.DebugLinkDecision(
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
        self.input(swipe=proto.DebugSwipeDirection.UP)

    def swipe_down(self):
        self.input(swipe=proto.DebugSwipeDirection.DOWN)

    def swipe_right(self):
        self.input(swipe=proto.DebugSwipeDirection.RIGHT)

    def swipe_left(self):
        self.input(swipe=proto.DebugSwipeDirection.LEFT)

    def stop(self):
        self._call(proto.DebugLinkStop(), nowait=True)

    def reseed(self, value):
        self._call(proto.DebugLinkReseedRandom(value=value))

    def start_recording(self, directory):
        self._call(proto.DebugLinkRecordScreen(target_directory=directory))

    def stop_recording(self):
        self._call(proto.DebugLinkRecordScreen(target_directory=None))

    @expect(proto.DebugLinkMemory, field="memory")
    def memory_read(self, address, length):
        return self._call(proto.DebugLinkMemoryRead(address=address, length=length))

    def memory_write(self, address, memory, flash=False):
        self._call(
            proto.DebugLinkMemoryWrite(address=address, memory=memory, flash=flash),
            nowait=True,
        )

    def flash_erase(self, sector):
        self._call(proto.DebugLinkFlashErase(sector=sector), nowait=True)

    @expect(proto.Success)
    def erase_sd_card(self, format=True):
        return self._call(proto.DebugLinkEraseSdCard(format=format))


class NullDebugLink(DebugLink):
    def __init__(self):
        super().__init__(None)

    def open(self):
        pass

    def close(self):
        pass

    def _call(self, msg, nowait=False):
        if not nowait:
            if isinstance(msg, proto.DebugLinkGetState):
                return proto.DebugLinkState()
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
            # XXX
            # On Trezor T, in some rare cases, two layouts may be queuing for events at
            # the same time.  A new workflow will first send out a ButtonRequest, wait
            # for a ButtonAck, and only then display a layout (closing the old one).
            # That means that if a layout that accepts debuglink decisions is currently
            # on screen, it has a good chance of accepting the following `press_yes`
            # before it can be closed by the newly open layout from the new workflow.
            #
            # This happens in particular when the recovery homescreen is on, because
            # it is a homescreen that accepts debuglink decisions.
            #
            # To prevent the issue, we insert a `wait_layout`, which on TT will only
            # return after the screen is refreshed, so we are certain that the new
            # layout is on. On T1 it is a no-op.
            #
            # This could run into trouble if some workflow asks for a ButtonRequest
            # without refreshing the screen.
            # This will also freeze on old bridges, where Read and Write are not
            # separate operations, because it relies on ButtonAck being sent without
            # waiting for a response.
            self.debuglink.wait_layout()
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
            # respond with correct pin
            return self.debuglink.read_pin_encoded()

        if self.pins == []:
            raise AssertionError("PIN sequence ended prematurely")
        else:
            return self.debuglink.encode_pin(self.pins.pop(0))

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
        next(input_flow)  # can't send before first yield

    def __enter__(self):
        # For usage in with/expected_responses
        self.in_with_statement += 1
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

        return False

    def set_expected_responses(self, expected):
        """Set a sequence of expected responses to client calls.

        Within a given with-block, the list of received responses from device must
        match the list of expected responses, otherwise an AssertionError is raised.

        If an expected response is given a field value other than None, that field value
        must exactly match the received field value. If a given field is None
        (or unspecified) in the expected response, the received field value is not
        checked.
        """
        if not self.in_with_statement:
            raise RuntimeError("Must be called inside 'with' statement")
        self.expected_responses = expected
        self.current_response = 0

    def use_pin_sequence(self, pins):
        """Respond to PIN prompts from device with the provided PINs.
        The sequence must be at least as long as the expected number of PIN prompts.
        """
        # XXX This currently only works on T1 as a response to PinMatrixRequest, but
        # if we modify trezor-core to introduce PIN prompts predictably (i.e. by
        # a new ButtonRequestType), it could also be used on TT via debug.input()
        self.ui.pins = list(pins)

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


@expect(proto.Success, field="message")
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
        proto.LoadDevice(
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


@expect(proto.Success, field="message")
def self_test(client):
    if client.features.bootloader_mode is not True:
        raise RuntimeError("Device must be in bootloader mode")

    return client.call(
        proto.SelfTest(
            payload=b"\x00\xFF\x55\xAA\x66\x99\x33\xCCABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!\x00\xFF\x55\xAA\x66\x99\x33\xCC"
        )
    )


@expect(proto.Success, field="message")
def show_text(client, header_text, body_text, icon=None, icon_color=None):
    body_text = [
        proto.DebugLinkShowTextItem(style=style, content=content)
        for style, content in body_text
    ]
    msg = proto.DebugLinkShowText(
        header_text=header_text,
        body_text=body_text,
        header_icon=icon,
        icon_color=icon_color,
    )
    return client.call(msg)
