# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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
import sys
import warnings

from mnemonic import Mnemonic

from . import MINIMUM_FIRMWARE_VERSION, exceptions, messages, tools

if sys.version_info.major < 3:
    raise Exception("Trezorlib does not support Python 2 anymore.")

LOG = logging.getLogger(__name__)

VENDORS = ("bitcointrezor.com", "trezor.io")
MAX_PASSPHRASE_LENGTH = 50

DEPRECATION_ERROR = """
Incompatible Trezor library detected.

(Original error: {})
""".strip()

OUTDATED_FIRMWARE_ERROR = """
Your Trezor firmware is out of date. Update it with the following command:
  trezorctl firmware-update
Or visit https://wallet.trezor.io/
""".strip()


def get_buttonrequest_value(code):
    # Converts integer code to its string representation of ButtonRequestType
    return [
        k
        for k in dir(messages.ButtonRequestType)
        if getattr(messages.ButtonRequestType, k) == code
    ][0]


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

    You can supply a `state` you saved in the previous session. If you do,
    the user might not need to enter their passphrase again.
    """

    def __init__(self, transport, ui=None, state=None):
        LOG.info("creating client instance for device: {}".format(transport.get_path()))
        self.transport = transport
        self.ui = ui
        self.state = state

        if ui is None:
            warnings.warn("UI class not supplied. This will probably crash soon.")

        self.session_counter = 0
        self.init_device()

    def open(self):
        if self.session_counter == 0:
            self.transport.begin_session()
        self.session_counter += 1

    def close(self):
        if self.session_counter == 1:
            self.transport.end_session()
        self.session_counter -= 1

    def cancel(self):
        self._raw_write(messages.Cancel())

    def call_raw(self, msg):
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612
        self._raw_write(msg)
        return self._raw_read()

    def _raw_write(self, msg):
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612
        self.transport.write(msg)

    def _raw_read(self):
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612
        return self.transport.read()

    def _callback_pin(self, msg):
        try:
            pin = self.ui.get_pin(msg.type)
        except exceptions.Cancelled:
            self.call_raw(messages.Cancel())
            raise

        if not pin.isdigit():
            self.call_raw(messages.Cancel())
            raise ValueError("Non-numeric PIN provided")

        resp = self.call_raw(messages.PinMatrixAck(pin=pin))
        if isinstance(resp, messages.Failure) and resp.code in (
            messages.FailureType.PinInvalid,
            messages.FailureType.PinCancelled,
            messages.FailureType.PinExpected,
        ):
            raise exceptions.PinException(resp.code, resp.message)
        else:
            return resp

    def _callback_passphrase(self, msg):
        if msg.on_device:
            passphrase = None
        else:
            try:
                passphrase = self.ui.get_passphrase()
            except exceptions.Cancelled:
                self.call_raw(messages.Cancel())
                raise

        passphrase = Mnemonic.normalize_string(passphrase)
        if len(passphrase) > MAX_PASSPHRASE_LENGTH:
            self.call_raw(messages.Cancel())
            raise ValueError("Passphrase too long")

        resp = self.call_raw(messages.PassphraseAck(passphrase=passphrase))
        if isinstance(resp, messages.PassphraseStateRequest):
            self.state = resp.state
            return self.call_raw(messages.PassphraseStateAck())
        else:
            return resp

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
        resp = self.call_raw(messages.Initialize(state=self.state))
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

    def is_outdated(self):
        if self.features.bootloader_mode:
            return False
        model = self.features.model or "1"
        required_version = MINIMUM_FIRMWARE_VERSION[model]
        return self.version < required_version

    def check_firmware_version(self, warn_only=False):
        if self.is_outdated():
            if warn_only:
                warnings.warn(OUTDATED_FIRMWARE_ERROR, stacklevel=2)
            else:
                raise exceptions.OutdatedFirmwareError(OUTDATED_FIRMWARE_ERROR)

    @tools.expect(messages.Success, field="message")
    def ping(
        self,
        msg,
        button_protection=False,
        pin_protection=False,
        passphrase_protection=False,
    ):
        # We would like ping to work on any valid TrezorClient instance, but
        # due to the protection modes, we need to go through self.call, and that will
        # raise an exception if the firmware is too old.
        # So we short-circuit the simplest variant of ping with call_raw.
        if not button_protection and not pin_protection and not passphrase_protection:
            # XXX this should be: `with self:`
            try:
                self.open()
                return self.call_raw(messages.Ping(message=msg))
            finally:
                self.close()

        msg = messages.Ping(
            message=msg,
            button_protection=button_protection,
            pin_protection=pin_protection,
            passphrase_protection=passphrase_protection,
        )
        return self.call(msg)

    def get_device_id(self):
        return self.features.device_id

    @tools.expect(messages.Success, field="message")
    @tools.session
    def clear_session(self):
        return self.call_raw(messages.ClearSession())


def MovedTo(where):
    def moved_to(*args, **kwargs):
        msg = "Function has been moved to " + where
        raise RuntimeError(DEPRECATION_ERROR.format(msg))

    return moved_to


class ProtocolMixin(object):
    """Fake mixin for old-style software that constructed TrezorClient class
    from separate mixins.

    Now it only simulates existence of original attributes to prevent some early
    crashes, and raises errors when any of the attributes are actually called.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn("TrezorClient mixins are not supported anymore")
        self.tx_api = None  # Electrum checks that this attribute exists
        super().__init__(*args, **kwargs)

    def set_tx_api(self, tx_api):
        warnings.warn("set_tx_api is deprecated, use new arguments to sign_tx")

    @staticmethod
    def expand_path(n):
        warnings.warn(
            "expand_path is deprecated, use tools.parse_path",
            DeprecationWarning,
            stacklevel=2,
        )
        return tools.parse_path(n)

    # Device functionality
    wipe_device = MovedTo("device.wipe")
    recovery_device = MovedTo("device.recover")
    reset_device = MovedTo("device.reset")
    backup_device = MovedTo("device.backup")

    set_u2f_counter = MovedTo("device.set_u2f_counter")

    apply_settings = MovedTo("device.apply_settings")
    apply_flags = MovedTo("device.apply_flags")
    change_pin = MovedTo("device.change_pin")

    # Firmware functionality
    firmware_update = MovedTo("firmware.update")

    # BTC-like functionality
    get_public_node = MovedTo("btc.get_public_node")
    get_address = MovedTo("btc.get_address")
    sign_tx = MovedTo("btc.sign_tx")
    sign_message = MovedTo("btc.sign_message")
    verify_message = MovedTo("btc.verify_message")

    # CoSi functionality
    cosi_commit = MovedTo("cosi.commit")
    cosi_sign = MovedTo("cosi.sign")

    # Ethereum functionality
    ethereum_get_address = MovedTo("ethereum.get_address")
    ethereum_sign_tx = MovedTo("ethereum.sign_tx")
    ethereum_sign_message = MovedTo("ethereum.sign_message")
    ethereum_verify_message = MovedTo("ethereum.verify_message")

    # Lisk functionality
    lisk_get_address = MovedTo("lisk.get_address")
    lisk_get_public_key = MovedTo("lisk.get_public_key")
    lisk_sign_message = MovedTo("lisk.sign_message")
    lisk_verify_message = MovedTo("lisk.verify_message")
    lisk_sign_tx = MovedTo("lisk.sign_tx")

    # NEM functionality
    nem_get_address = MovedTo("nem.get_address")
    nem_sign_tx = MovedTo("nem.sign_tx")

    # Stellar functionality
    stellar_get_address = MovedTo("stellar.get_address")
    stellar_sign_transaction = MovedTo("stellar.sign_tx")

    # Miscellaneous cryptographic functionality
    get_entropy = MovedTo("misc.get_entropy")
    sign_identity = MovedTo("misc.sign_identity")
    get_ecdh_session_key = MovedTo("misc.get_ecdh_session_key")
    encrypt_keyvalue = MovedTo("misc.encrypt_keyvalue")
    decrypt_keyvalue = MovedTo("misc.decrypt_keyvalue")

    # Debug device functionality
    load_device_by_mnemonic = MovedTo("debuglink.load_device_by_mnemonic")
    load_device_by_xprv = MovedTo("debuglink.load_device_by_xprv")


class BaseClient:
    """Compatibility proxy for original BaseClient class.
    Prevents early crash in Electrum forks and possibly other software.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn("TrezorClient mixins are not supported anymore")
        self.trezor_client = TrezorClient(*args, **kwargs)

    def __getattr__(self, key):
        return getattr(self.trezor_client, key)


# further Electrum compatibility
proto = None
