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
import os
import warnings
from typing import TYPE_CHECKING, Any, Optional

from mnemonic import Mnemonic

from . import exceptions, mapping, messages, models
from .log import DUMP_BYTES
from .messages import Capability
from .tools import expect, parse_path, session

if TYPE_CHECKING:
    from .protobuf import MessageType
    from .ui import TrezorClientUI
    from .transport import Transport

LOG = logging.getLogger(__name__)

MAX_PASSPHRASE_LENGTH = 50
MAX_PIN_LENGTH = 50

PASSPHRASE_ON_DEVICE = object()
PASSPHRASE_TEST_PATH = parse_path("44h/1h/0h/0/0")

OUTDATED_FIRMWARE_ERROR = """
Your Trezor firmware is out of date. Update it with the following command:
  trezorctl firmware-update
Or visit https://suite.trezor.io/
""".strip()


def get_default_client(
    path: Optional[str] = None, ui: Optional["TrezorClientUI"] = None, **kwargs: Any
) -> "TrezorClient":
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
    """

    def __init__(
        self,
        transport: "Transport",
        ui: "TrezorClientUI",
        session_id: Optional[bytes] = None,
        derive_cardano: Optional[bool] = None,
        model: Optional[models.TrezorModel] = None,
        _init_device: bool = True,
    ) -> None:
        """Create a TrezorClient instance.

        You have to provide a `transport`, i.e., a raw connection to the device. You can
        use `trezorlib.transport.get_transport` to find one.

        You have to provide an UI implementation for the three kinds of interaction:
        - button request (notify the user that their interaction is needed)
        - PIN request (on T1, ask the user to input numbers for a PIN matrix)
        - passphrase request (ask the user to enter a passphrase) See `trezorlib.ui` for
          details.

        You can supply a `session_id` you might have saved in the previous session. If
        you do, the user might not need to enter their passphrase again.

        You can provide Trezor model information. If not provided, it is detected from
        the model name reported at initialization time.

        By default, the instance will open a connection to the Trezor device, send an
        `Initialize` message, set up the `features` field from the response, and connect
        to a session. By specifying `_init_device=False`, this step is skipped. Notably,
        this means that `client.features` is unset. Use `client.init_device()` or
        `client.refresh_features()` to fix that, otherwise A LOT OF THINGS will break.
        Only use this if you are _sure_ that you know what you are doing. This feature
        might be removed at any time.
        """
        LOG.info(f"creating client instance for device: {transport.get_path()}")
        self.model = model
        if self.model:
            self.mapping = self.model.default_mapping
        else:
            self.mapping = mapping.DEFAULT_MAPPING
        self.transport = transport
        self.ui = ui
        self.session_counter = 0
        self.session_id = session_id
        if _init_device:
            self.init_device(session_id=session_id, derive_cardano=derive_cardano)

    def open(self) -> None:
        if self.session_counter == 0:
            self.transport.begin_session()
        self.session_counter += 1

    def close(self) -> None:
        self.session_counter = max(self.session_counter - 1, 0)
        if self.session_counter == 0:
            # TODO call EndSession here?
            self.transport.end_session()

    def cancel(self) -> None:
        self._raw_write(messages.Cancel())

    def call_raw(self, msg: "MessageType") -> "MessageType":
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612
        self._raw_write(msg)
        return self._raw_read()

    def _raw_write(self, msg: "MessageType") -> None:
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612
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

    def _raw_read(self) -> "MessageType":
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612
        msg_type, msg_bytes = self.transport.read()
        LOG.log(
            DUMP_BYTES,
            f"received type {msg_type} ({len(msg_bytes)} bytes): {msg_bytes.hex()}",
        )
        msg = self.mapping.decode(msg_type, msg_bytes)
        LOG.debug(
            f"received message: {msg.__class__.__name__}",
            extra={"protobuf": msg},
        )
        return msg

    def _callback_pin(self, msg: messages.PinMatrixRequest) -> "MessageType":
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

    def _callback_passphrase(self, msg: messages.PassphraseRequest) -> "MessageType":
        available_on_device = Capability.PassphraseEntry in self.features.capabilities

        def send_passphrase(
            passphrase: Optional[str] = None, on_device: Optional[bool] = None
        ) -> "MessageType":
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
        if not isinstance(passphrase, str):
            raise RuntimeError("Passphrase must be a str")
        passphrase = Mnemonic.normalize_string(passphrase)
        if len(passphrase) > MAX_PASSPHRASE_LENGTH:
            self.call_raw(messages.Cancel())
            raise ValueError("Passphrase too long")

        return send_passphrase(passphrase, on_device=False)

    def _callback_button(self, msg: messages.ButtonRequest) -> "MessageType":
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612
        # do this raw - send ButtonAck first, notify UI later
        self._raw_write(messages.ButtonAck())
        self.ui.button_request(msg)
        return self._raw_read()

    @session
    def call(self, msg: "MessageType") -> "MessageType":
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

        if not self.model:
            # Trezor Model One bootloader 1.8.0 or older does not send model name
            self.model = models.by_name(features.model or "1")
            if self.model is None:
                raise RuntimeError("Unsupported Trezor model")

        if features.vendor not in self.model.vendors:
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

    @session
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

    @session
    def init_device(
        self,
        *,
        session_id: Optional[bytes] = None,
        new_session: bool = False,
        derive_cardano: Optional[bool] = None,
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

        resp = self.call_raw(
            messages.Initialize(
                session_id=self.session_id,
                derive_cardano=derive_cardano,
            )
        )
        if isinstance(resp, messages.Failure):
            # can happen if `derive_cardano` does not match the current session
            raise exceptions.TrezorFailure(resp)
        if not isinstance(resp, messages.Features):
            raise exceptions.TrezorException("Unexpected response to Initialize")

        if self.session_id is not None and resp.session_id == self.session_id:
            LOG.info("Successfully resumed session")
        elif session_id is not None:
            LOG.info("Failed to resume session")

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

    def is_outdated(self) -> bool:
        if self.features.bootloader_mode:
            return False

        assert self.model is not None  # should happen in _refresh_features
        return self.version < self.model.minimum_version

    def check_firmware_version(self, warn_only: bool = False) -> None:
        if self.is_outdated():
            if warn_only:
                warnings.warn("Firmware is out of date", stacklevel=2)
            else:
                raise exceptions.OutdatedFirmwareError(OUTDATED_FIRMWARE_ERROR)

    @expect(messages.Success, field="message", ret_type=str)
    def ping(
        self,
        msg: str,
        button_protection: bool = False,
    ) -> "MessageType":
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

        return self.call(
            messages.Ping(message=msg, button_protection=button_protection)
        )

    def get_device_id(self) -> Optional[str]:
        return self.features.device_id

    @session
    def lock(self, *, _refresh_features: bool = True) -> None:
        """Lock the device.

        If the device does not have a PIN configured, this will do nothing.
        Otherwise, a lock screen will be shown and the device will prompt for PIN
        before further actions.

        This call does _not_ invalidate passphrase cache. If passphrase is in use,
        the device will not prompt for it after unlocking.

        To invalidate passphrase cache, use `end_session()`. To lock _and_ invalidate
        passphrase cache, use `clear_session()`.
        """
        # Private argument _refresh_features can be used internally to avoid
        # refreshing in cases where we will refresh soon anyway. This is used
        # in TrezorClient.clear_session()
        self.call(messages.LockDevice())
        if _refresh_features:
            self.refresh_features()

    @session
    def ensure_unlocked(self) -> None:
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

    def end_session(self) -> None:
        """Close the current session and clear cached passphrase.

        The session will become invalid until `init_device()` is called again.
        If passphrase is enabled, further actions will prompt for it again.

        This is a no-op in bootloader mode, as it does not support session management.
        """
        # since: 2.3.4, 1.9.4
        try:
            if not self.features.bootloader_mode:
                self.call(messages.EndSession())
        except exceptions.TrezorFailure:
            # A failure most likely means that the FW version does not support
            # the EndSession call. We ignore the failure and clear the local session_id.
            # The client-side end result is identical.
            pass
        self.session_id = None

    @session
    def clear_session(self) -> None:
        """Lock the device and present a fresh session.

        The current session will be invalidated and a new one will be started. If the
        device has PIN enabled, it will become locked.

        Equivalent to calling `lock()`, `end_session()` and `init_device()`.
        """
        self.lock(_refresh_features=False)
        self.end_session()
        self.init_device(new_session=True)
