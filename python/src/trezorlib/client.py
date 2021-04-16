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
import warnings
from typing import Optional

from mnemonic import Mnemonic

from . import MINIMUM_FIRMWARE_VERSION, exceptions, mapping, messages, tools
from .log import DUMP_BYTES
from .messages import Capability

LOG = logging.getLogger(__name__)

VENDORS = ("bitcointrezor.com", "trezor.io")
MAX_PASSPHRASE_LENGTH = 50
MAX_PIN_LENGTH = 50

PASSPHRASE_ON_DEVICE = object()
PASSPHRASE_TEST_PATH = tools.parse_path("44h/1h/0h/0/0")

OUTDATED_FIRMWARE_ERROR = """
Your Trezor firmware is out of date. Update it with the following command:
  trezorctl firmware-update
Or visit https://suite.trezor.io/
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
            # TODO call EndSession here?
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

        if any(d not in "123456789" for d in pin) or not (
            1 <= len(pin) <= MAX_PIN_LENGTH
        ):
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

    def _refresh_features(self, features: messages.Features) -> None:
        """Update internal fields based on passed-in Features message."""
        if features.vendor not in VENDORS:
            raise RuntimeError("Unsupported device")

        self.features = features
        self.version = (
            self.features.major_version,
            self.features.minor_version,
            self.features.patch_version,
        )
        self.check_firmware_version(warn_only=True)
        if self.features.session_id is not None:
            self.session_id = self.features.session_id
            self.features.session_id = None

    @tools.session
    def refresh_features(self) -> messages.Features:
        """Reload features from the device.

        Should be called after changing settings or performing operations that affect
        device state.
        """
        resp = self.call_raw(messages.GetFeatures())
        if not isinstance(resp, messages.Features):
            raise exceptions.TrezorException("Unexpected response to GetFeatures")
        self._refresh_features(resp)
        return resp

    @tools.session
    def init_device(
        self, *, session_id: bytes = None, new_session: bool = False
    ) -> Optional[bytes]:
        """Initialize the device and return a session ID.

        You can optionally specify a session ID. If the session still exists on the
        device, the same session ID will be returned and the session is resumed.
        Otherwise a different session ID is returned.

        Specify `new_session=True` to open a fresh session. Since firmware version
        1.9.0/2.3.0, the previous session will remain cached on the device, and can be
        resumed by calling `init_device` again with the appropriate session ID.

        If neither `new_session` nor `session_id` is specified, the current session ID
        will be reused. If no session ID was cached, a new session ID will be allocated
        and returned.

        # Version notes:

        Trezor One older than 1.9.0 does not have session management. Optional arguments
        have no effect and the function returns None

        Trezor T older than 2.3.0 does not have session cache. Requesting a new session
        will overwrite the old one. In addition, this function will always return None.
        A valid session_id can be obtained from the `session_id` attribute, but only
        after a passphrase-protected call is performed. You can use the following code:

        >>> client.init_device()
        >>> client.ensure_unlocked()
        >>> valid_session_id = client.session_id
        """
        if new_session:
            self.session_id = None
        elif session_id is not None:
            self.session_id = session_id

        resp = self.call_raw(messages.Initialize(session_id=self.session_id))
        if not isinstance(resp, messages.Features):
            raise exceptions.TrezorException("Unexpected response to Initialize")

        # TT < 2.3.0 compatibility:
        # _refresh_features will clear out the session_id field. We want this function
        # to return its value, so that callers can rely on it being either a valid
        # session_id, or None if we can't do that.
        # Older TT FW does not report session_id in Features and self.session_id might
        # be invalid because TT will not allocate a session_id until a passphrase
        # exchange happens.
        reported_session_id = resp.session_id
        self._refresh_features(resp)
        return reported_session_id

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
                resp = self.call_raw(messages.Ping(message=msg))
                if isinstance(resp, messages.ButtonRequest):
                    # device is PIN-locked.
                    # respond and hope for the best
                    resp = self._callback_button(resp)
                return resp
            finally:
                self.close()

        msg = messages.Ping(message=msg, button_protection=button_protection,)
        return self.call(msg)

    def get_device_id(self):
        return self.features.device_id

    @tools.session
    def lock(self):
        """Lock the device.

        If the device does not have a PIN configured, this will do nothing.
        Otherwise, a lock screen will be shown and the device will prompt for PIN
        before further actions.

        This call does _not_ invalidate passphrase cache. If passphrase is in use,
        the device will not prompt for it after unlocking.

        To invalidate passphrase cache, use `end_session()`. To lock _and_ invalidate
        passphrase cache, use `clear_session()`.
        """
        self.call(messages.LockDevice())
        self.refresh_features()

    @tools.session
    def ensure_unlocked(self):
        """Ensure the device is unlocked and a passphrase is cached.

        If the device is locked, this will prompt for PIN. If passphrase is enabled
        and no passphrase is cached for the current session, the device will also
        prompt for passphrase.

        After calling this method, further actions on the device will not prompt for
        PIN or passphrase until the device is locked or the session becomes invalid.
        """
        from .btc import get_address

        get_address(self, "Testnet", PASSPHRASE_TEST_PATH)
        self.refresh_features()

    def end_session(self):
        """Close the current session and clear cached passphrase.

        The session will become invalid until `init_device()` is called again.
        If passphrase is enabled, further actions will prompt for it again.
        """
        # XXX self.call(messages.EndSession())
        self.session_id = None

    @tools.session
    def clear_session(self):
        """Lock the device and present a fresh session.

        The current session will be invalidated and a new one will be started. If the
        device has PIN enabled, it will become locked.

        Equivalent to calling `lock()`, `end_session()` and `init_device()`.
        """
        # call LockDevice manually to save one refresh_features() call
        self.call(messages.LockDevice())
        self.end_session()
        self.init_device()
