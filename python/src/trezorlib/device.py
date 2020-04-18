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

import os
import time
import warnings

from . import messages
from .exceptions import Cancelled
from .tools import expect, session
from .transport import enumerate_devices, get_transport

RECOVERY_BACK = "\x08"  # backspace character, sent literally


class TrezorDevice:
    """
    This class is deprecated. (There is no reason for it to exist in the first
    place, it is nothing but a collection of two functions.)
    Instead, please use functions from the ``trezorlib.transport`` module.
    """

    @classmethod
    def enumerate(cls):
        warnings.warn("TrezorDevice is deprecated.", DeprecationWarning)
        return enumerate_devices()

    @classmethod
    def find_by_path(cls, path):
        warnings.warn("TrezorDevice is deprecated.", DeprecationWarning)
        return get_transport(path, prefix_search=False)


@expect(messages.Success, field="message")
def apply_settings(
    client,
    label=None,
    language=None,
    use_passphrase=None,
    homescreen=None,
    passphrase_always_on_device=None,
    auto_lock_delay_ms=None,
    display_rotation=None,
):
    settings = messages.ApplySettings()
    if label is not None:
        settings.label = label
    if language:
        settings.language = language
    if use_passphrase is not None:
        settings.use_passphrase = use_passphrase
    if homescreen is not None:
        settings.homescreen = homescreen
    if passphrase_always_on_device is not None:
        settings.passphrase_always_on_device = passphrase_always_on_device
    if auto_lock_delay_ms is not None:
        settings.auto_lock_delay_ms = auto_lock_delay_ms
    if display_rotation is not None:
        settings.display_rotation = display_rotation

    out = client.call(settings)
    client.init_device()  # Reload Features
    return out


@expect(messages.Success, field="message")
def apply_flags(client, flags):
    out = client.call(messages.ApplyFlags(flags=flags))
    client.init_device()  # Reload Features
    return out


@expect(messages.Success, field="message")
def change_pin(client, remove=False):
    ret = client.call(messages.ChangePin(remove=remove))
    client.init_device()  # Re-read features
    return ret


@expect(messages.Success, field="message")
def change_wipe_code(client, remove=False):
    ret = client.call(messages.ChangeWipeCode(remove=remove))
    client.init_device()  # Re-read features
    return ret


@expect(messages.Success, field="message")
def sd_protect(client, operation):
    ret = client.call(messages.SdProtect(operation=operation))
    client.init_device()
    return ret


@expect(messages.Success, field="message")
def wipe(client):
    ret = client.call(messages.WipeDevice())
    client.init_device()
    return ret


def recover(
    client,
    word_count=24,
    passphrase_protection=False,
    pin_protection=True,
    label=None,
    language="en-US",
    input_callback=None,
    type=messages.RecoveryDeviceType.ScrambledWords,
    dry_run=False,
    u2f_counter=None,
):
    if client.features.model == "1" and input_callback is None:
        raise RuntimeError("Input callback required for Trezor One")

    if word_count not in (12, 18, 24):
        raise ValueError("Invalid word count. Use 12/18/24")

    if client.features.initialized and not dry_run:
        raise RuntimeError(
            "Device already initialized. Call device.wipe() and try again."
        )

    if u2f_counter is None:
        u2f_counter = int(time.time())

    msg = messages.RecoveryDevice(
        word_count=word_count, enforce_wordlist=True, type=type, dry_run=dry_run
    )

    if not dry_run:
        # set additional parameters
        msg.passphrase_protection = passphrase_protection
        msg.pin_protection = pin_protection
        msg.label = label
        msg.language = language
        msg.u2f_counter = u2f_counter

    res = client.call(msg)

    while isinstance(res, messages.WordRequest):
        try:
            inp = input_callback(res.type)
            res = client.call(messages.WordAck(word=inp))
        except Cancelled:
            res = client.call(messages.Cancel())

    client.init_device()
    return res


@expect(messages.Success, field="message")
@session
def reset(
    client,
    display_random=False,
    strength=None,
    passphrase_protection=False,
    pin_protection=True,
    label=None,
    language="en-US",
    u2f_counter=0,
    skip_backup=False,
    no_backup=False,
    backup_type=messages.BackupType.Bip39,
):
    if client.features.initialized:
        raise RuntimeError(
            "Device is initialized already. Call wipe_device() and try again."
        )

    if strength is None:
        if client.features.model == "1":
            strength = 256
        else:
            strength = 128

    # Begin with device reset workflow
    msg = messages.ResetDevice(
        display_random=bool(display_random),
        strength=strength,
        passphrase_protection=bool(passphrase_protection),
        pin_protection=bool(pin_protection),
        language=language,
        label=label,
        u2f_counter=u2f_counter,
        skip_backup=bool(skip_backup),
        no_backup=bool(no_backup),
        backup_type=backup_type,
    )

    resp = client.call(msg)
    if not isinstance(resp, messages.EntropyRequest):
        raise RuntimeError("Invalid response, expected EntropyRequest")

    external_entropy = os.urandom(32)
    # LOG.debug("Computer generated entropy: " + external_entropy.hex())
    ret = client.call(messages.EntropyAck(entropy=external_entropy))
    client.init_device()
    return ret


@expect(messages.Success, field="message")
def backup(client):
    ret = client.call(messages.BackupDevice())
    return ret
