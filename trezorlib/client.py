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

import functools
import logging
import sys
import warnings

from . import (
    btc,
    cosi,
    device,
    ethereum,
    exceptions,
    firmware,
    lisk,
    mapping,
    messages as proto,
    misc,
    nem,
    stellar,
    tools,
)

if sys.version_info.major < 3:
    raise Exception("Trezorlib does not support Python 2 anymore.")


SCREENSHOT = False
LOG = logging.getLogger(__name__)

PinException = exceptions.PinException


def get_buttonrequest_value(code):
    # Converts integer code to its string representation of ButtonRequestType
    return [
        k
        for k in dir(proto.ButtonRequestType)
        if getattr(proto.ButtonRequestType, k) == code
    ][0]


class MovedTo:
    """Deprecation redirector for methods that were formerly part of TrezorClient"""

    def __init__(self, where):
        self.where = where
        self.name = where.__module__ + "." + where.__name__

    def _deprecated_redirect(self, client, *args, **kwargs):
        """Redirector for a deprecated method on TrezorClient"""
        warnings.warn(
            "Function has been moved to %s" % self.name,
            DeprecationWarning,
            stacklevel=2,
        )
        return self.where(client, *args, **kwargs)

    def __get__(self, instance, cls):
        if instance is None:
            return self._deprecated_redirect
        else:
            return functools.partial(self._deprecated_redirect, instance)


class BaseClient(object):
    # Implements very basic layer of sending raw protobuf
    # messages to device and getting its response back.
    def __init__(self, transport, ui, **kwargs):
        LOG.info("creating client instance for device: {}".format(transport.get_path()))
        self.transport = transport
        self.ui = ui

        self.session_counter = 0
        super(BaseClient, self).__init__()  # *args, **kwargs)

    def open(self):
        if self.session_counter == 0:
            self.transport.begin_session()
        self.session_counter += 1

    def close(self):
        if self.session_counter == 1:
            self.transport.end_session()
        self.session_counter -= 1

    def cancel(self):
        self._raw_write(proto.Cancel())

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
        pin = self.ui.get_pin(msg.type)
        if not pin.isdigit():
            raise ValueError("Non-numeric PIN provided")

        resp = self.call_raw(proto.PinMatrixAck(pin=pin))
        if isinstance(resp, proto.Failure) and resp.code in (
            proto.FailureType.PinInvalid,
            proto.FailureType.PinCancelled,
            proto.FailureType.PinExpected,
        ):
            raise exceptions.PinException(resp.code, resp.message)
        else:
            return resp

    def _callback_passphrase(self, msg):
        if msg.on_device:
            passphrase = None
        else:
            passphrase = self.ui.get_passphrase()

        resp = self.call_raw(proto.PassphraseAck(passphrase=passphrase))
        if isinstance(resp, proto.PassphraseStateRequest):
            self.state = resp.state
            return self.call_raw(proto.PassphraseStateAck())
        else:
            return resp

    def _callback_button(self, msg):
        __tracebackhide__ = True  # for pytest # pylint: disable=W0612
        # do this raw - send ButtonAck first, notify UI later
        self._raw_write(proto.ButtonAck())
        self.ui.button_request(msg.code)
        return self._raw_read()

    @tools.session
    def call(self, msg):
        resp = self.call_raw(msg)
        while True:
            if isinstance(resp, proto.PinMatrixRequest):
                resp = self._callback_pin(resp)
            elif isinstance(resp, proto.PassphraseRequest):
                resp = self._callback_passphrase(resp)
            elif isinstance(resp, proto.ButtonRequest):
                resp = self._callback_button(resp)
            elif isinstance(resp, proto.Failure):
                if resp.code == proto.FailureType.ActionCancelled:
                    raise exceptions.Cancelled
                raise exceptions.TrezorFailure(resp)
            else:
                return resp


class ProtocolMixin(object):
    VENDORS = ("bitcointrezor.com", "trezor.io")

    def __init__(self, state=None, *args, **kwargs):
        super(ProtocolMixin, self).__init__(*args, **kwargs)
        self.state = state
        self.init_device()

    def set_tx_api(self, tx_api):
        warnings.warn("set_tx_api is deprecated, use new arguments to sign_tx")

    @tools.session
    def init_device(self):
        resp = self.call(proto.Initialize(state=self.state))
        if not isinstance(resp, proto.Features):
            raise exceptions.TrezorException("Unexpected initial response")
        else:
            self.features = resp
        if self.features.vendor not in self.VENDORS:
            raise RuntimeError("Unsupported device")
            # A side-effect of this is a sanity check for broken protobuf definitions.
            # If the `vendor` field doesn't exist, you probably have a mismatched
            # checkout of trezor-common.

    @staticmethod
    def expand_path(n):
        warnings.warn(
            "expand_path is deprecated, use tools.parse_path",
            DeprecationWarning,
            stacklevel=2,
        )
        return tools.parse_path(n)

    @tools.expect(proto.Success, field="message")
    def ping(
        self,
        msg,
        button_protection=False,
        pin_protection=False,
        passphrase_protection=False,
    ):
        msg = proto.Ping(
            message=msg,
            button_protection=button_protection,
            pin_protection=pin_protection,
            passphrase_protection=passphrase_protection,
        )
        return self.call(msg)

    def get_device_id(self):
        return self.features.device_id

    @tools.expect(proto.Success, field="message")
    def clear_session(self):
        return self.call(proto.ClearSession())

    # Device functionality
    wipe_device = MovedTo(device.wipe)
    recovery_device = MovedTo(device.recover)
    reset_device = MovedTo(device.reset)
    backup_device = MovedTo(device.backup)

    set_u2f_counter = MovedTo(device.set_u2f_counter)

    apply_settings = MovedTo(device.apply_settings)
    apply_flags = MovedTo(device.apply_flags)
    change_pin = MovedTo(device.change_pin)

    # Firmware functionality
    firmware_update = MovedTo(firmware.update)

    # BTC-like functionality
    get_public_node = MovedTo(btc.get_public_node)
    get_address = MovedTo(btc.get_address)
    sign_tx = MovedTo(btc.sign_tx)
    sign_message = MovedTo(btc.sign_message)
    verify_message = MovedTo(btc.verify_message)

    # CoSi functionality
    cosi_commit = MovedTo(cosi.commit)
    cosi_sign = MovedTo(cosi.sign)

    # Ethereum functionality
    ethereum_get_address = MovedTo(ethereum.get_address)
    ethereum_sign_tx = MovedTo(ethereum.sign_tx)
    ethereum_sign_message = MovedTo(ethereum.sign_message)
    ethereum_verify_message = MovedTo(ethereum.verify_message)

    # Lisk functionality
    lisk_get_address = MovedTo(lisk.get_address)
    lisk_get_public_key = MovedTo(lisk.get_public_key)
    lisk_sign_message = MovedTo(lisk.sign_message)
    lisk_verify_message = MovedTo(lisk.verify_message)
    lisk_sign_tx = MovedTo(lisk.sign_tx)

    # NEM functionality
    nem_get_address = MovedTo(nem.get_address)
    nem_sign_tx = MovedTo(nem.sign_tx)

    # Stellar functionality
    stellar_get_address = MovedTo(stellar.get_address)
    stellar_sign_transaction = MovedTo(stellar.sign_tx)

    # Miscellaneous cryptographic functionality
    get_entropy = MovedTo(misc.get_entropy)
    sign_identity = MovedTo(misc.sign_identity)
    get_ecdh_session_key = MovedTo(misc.get_ecdh_session_key)
    encrypt_keyvalue = MovedTo(misc.encrypt_keyvalue)
    decrypt_keyvalue = MovedTo(misc.decrypt_keyvalue)


class TrezorClient(ProtocolMixin, BaseClient):
    def __init__(self, transport, *args, **kwargs):
        super().__init__(transport=transport, *args, **kwargs)
