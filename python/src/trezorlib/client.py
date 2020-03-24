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
import os
import sys
import warnings

from mnemonic import Mnemonic

from . import MINIMUM_FIRMWARE_VERSION, exceptions, mapping, messages, tools
from .log import DUMP_BYTES
from .messages import Capability

if sys.version_info.major < 3:
    raise Exception("Trezorlib does not support Python 2 anymore.")

LOG = logging.getLogger(__name__)

VENDORS = ("bitcointrezor.com", "trezor.io")
MAX_PASSPHRASE_LENGTH = 50

PASSPHRASE_ON_DEVICE = object()
PASSPHRASE_TEST_PATH = tools.parse_path("44h/1h/19h/0/1337")

OUTDATED_FIRMWARE_ERROR = """
Your Trezor firmware is out of date. Update it with the following command:
  trezorctl firmware-update
Or visit https://wallet.trezor.io/
""".strip()


def get_default_client(path=None, ui=None, **kwargs):
    """Get a client for a connected Trezor device.

    Returns a TrezorClient instance with minimum fuss.

    If path is specified, does a prefix-search for the specified device. Otherwise, uses
    the value of TREZOR_PATH env variable, or finds first connected Trezor.
    If no UI is supplied, instantiates the default CLI UI.
    """
    from .transport import get_transport
    from .ui import ClickUI

    if path is None:
        path = os.getenv("TREZOR_PATH")

    transport = get_transport(path, prefix_search=True)
    if ui is None:
        ui = ClickUI()

    return TrezorClient(transport, ui, **kwargs)


class TrezorClient:
    """Trezor client, a connection to a Trezor device.

    This class allows you to manage connection state, send and receive protobuf
    messages, handle user interactions, and perform some generic tasks
    (send a cancel message, initialize or clear a session, ping the device).

    You have to provide a transport, i.e., a raw connection to the device. You can use
    `trezorlib.transport.get_transport` to find one.

    You have to provide an UI implementation for the three kinds of interaction:
    - button request (notify the user that their interaction is needed)
    - PIN request (on T1, ask the user to input numbers for a PIN matrix)
    - passphrase request (ask the user to enter a passphrase)
    See `trezorlib.ui` for details.

    You can supply a `session_id` you might have saved in the previous session.
    If you do, the user might not need to enter their passphrase again.
    """

    def __init__(
        self, transport, ui, session_id=None,
    ):
        LOG.info("creating client instance for device: {}".format(transport.get_path()))
        self.transport = transport
        self.ui = ui
        self.session_id = session_id
        self.session_counter = 0
        self.init_device()

    def open(self):
        if self.session_counter == 0:
            self.transport.begin_session()
        self.session_counter += 1

    def close(self):
        self.session_counter = max(self.session_counter - 1, 0)
        if self.session_counter == 0:
            self.transport.end_session()

    def cancel(self):
        self._raw_write(messages.Cancel())

    def call_raw(self, msg):
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612
        self._raw_write(msg)
        return self._raw_read()

    def _raw_write(self, msg):
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612
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

    def _raw_read(self):
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612
        msg_type, msg_bytes = self.transport.read()
        LOG.log(
            DUMP_BYTES,
            "received type {} ({} bytes): {}".format(
                msg_type, len(msg_bytes), msg_bytes.hex()
            ),
        )
        msg = mapping.decode(msg_type, msg_bytes)
        LOG.debug(
            "received message: {}".format(msg.__class__.__name__),
            extra={"protobuf": msg},
        )
        return msg

    def _callback_pin(self, msg):
        try:
            pin = self.ui.get_pin(msg.type)
        except exceptions.Cancelled:
            self.call_raw(messages.Cancel())
            raise

        if any(d not in "123456789" for d in pin) or not (1 <= len(pin) <= 9):
            self.call_raw(messages.Cancel())
            raise ValueError("Invalid PIN provided")

        resp = self.call_raw(messages.PinMatrixAck(pin=pin))
        if isinstance(resp, messages.Failure) and resp.code in (
            messages.FailureType.PinInvalid,
            messages.FailureType.PinCancelled,
            messages.FailureType.PinExpected,
        ):
            raise exceptions.PinException(resp.code, resp.message)
        else:
            return resp

    def _callback_passphrase(self, msg: messages.PassphraseRequest):
        available_on_device = Capability.PassphraseEntry in self.features.capabilities

        def send_passphrase(passphrase=None, on_device=None):
            msg = messages.PassphraseAck(passphrase=passphrase, on_device=on_device)
            resp = self.call_raw(msg)
            if isinstance(resp, messages.Deprecated_PassphraseStateRequest):
                self.session_id = resp.state
                resp = self.call_raw(messages.Deprecated_PassphraseStateAck())
            return resp

        # short-circuit old style entry
        if msg._on_device is True:
            return send_passphrase(None, None)

        try:
            passphrase = self.ui.get_passphrase(available_on_device=available_on_device)
        except exceptions.Cancelled:
            self.call_raw(messages.Cancel())
            raise

        if passphrase is PASSPHRASE_ON_DEVICE:
            if not available_on_device:
                self.call_raw(messages.Cancel())
                raise RuntimeError("Device is not capable of entering passphrase")
            else:
                return send_passphrase(on_device=True)

        # else process host-entered passphrase
        passphrase = Mnemonic.normalize_string(passphrase)
        if len(passphrase) > MAX_PASSPHRASE_LENGTH:
            self.call_raw(messages.Cancel())
            raise ValueError("Passphrase too long")

        return send_passphrase(passphrase, on_device=False)

    def _callback_button(self, msg):
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612
        # do this raw - send ButtonAck first, notify UI later
        self._raw_write(messages.ButtonAck())
        self.ui.button_request(msg.code)
        return self._raw_read()

    @tools.session
    def call(self, msg):
        self.check_firmware_version()
        resp = self.call_raw(msg)
        while True:
            if isinstance(resp, messages.PinMatrixRequest):
                resp = self._callback_pin(resp)
            elif isinstance(resp, messages.PassphraseRequest):
                resp = self._callback_passphrase(resp)
            elif isinstance(resp, messages.ButtonRequest):
                resp = self._callback_button(resp)
            elif isinstance(resp, messages.Failure):
                if resp.code == messages.FailureType.ActionCancelled:
                    raise exceptions.Cancelled
                raise exceptions.TrezorFailure(resp)
            else:
                return resp

    @tools.session
    def init_device(self):
        resp = self.call_raw(messages.Initialize(session_id=self.session_id))
        if not isinstance(resp, messages.Features):
            raise exceptions.TrezorException("Unexpected initial response")
        else:
            self.features = resp
        if self.features.vendor not in VENDORS:
            raise RuntimeError("Unsupported device")
            # A side-effect of this is a sanity check for broken protobuf definitions.
            # If the `vendor` field doesn't exist, you probably have a mismatched
            # checkout of trezor-common.
        self.version = (
            self.features.major_version,
            self.features.minor_version,
            self.features.patch_version,
        )
        self.check_firmware_version(warn_only=True)
        if self.features.session_id is not None:
            self.session_id = self.features.session_id

    def is_outdated(self):
        if self.features.bootloader_mode:
            return False
        model = self.features.model or "1"
        required_version = MINIMUM_FIRMWARE_VERSION[model]
        return self.version < required_version

    def check_firmware_version(self, warn_only=False):
        if self.is_outdated():
            if warn_only:
                warnings.warn("Firmware is out of date", stacklevel=2)
            else:
                raise exceptions.OutdatedFirmwareError(OUTDATED_FIRMWARE_ERROR)

    @tools.expect(messages.Success, field="message")
    def ping(
        self, msg, button_protection=False,
    ):
        # We would like ping to work on any valid TrezorClient instance, but
        # due to the protection modes, we need to go through self.call, and that will
        # raise an exception if the firmware is too old.
        # So we short-circuit the simplest variant of ping with call_raw.
        if not button_protection:
            # XXX this should be: `with self:`
            try:
                self.open()
                return self.call_raw(messages.Ping(message=msg))
            finally:
                self.close()

        msg = messages.Ping(message=msg, button_protection=button_protection,)
        return self.call(msg)

    def get_device_id(self):
        return self.features.device_id

    @tools.session
    def clear_session(self):
        resp = self.call_raw(messages.ClearSession())
        if isinstance(resp, messages.Success):
            self.session_id = None
            self.init_device()
            return resp.message
        else:
            return resp
