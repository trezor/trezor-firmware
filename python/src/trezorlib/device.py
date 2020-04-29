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

from . import messages
from .exceptions import Cancelled
from .tools import expect, session

RECOVERY_BACK = "\x08"  # backspace character, sent literally


@expect(messages.Success, field="message")
@session
def apply_settings(
    client,
    label=None,
    language=None,
    use_passphrase=None,
    homescreen=None,
    passphrase_always_on_device=None,
    auto_lock_delay_ms=None,
    display_rotation=None,
    safety_checks=None,
):
    settings = messages.ApplySettings(
        label=label,
        language=language,
        use_passphrase=use_passphrase,
        homescreen=homescreen,
        passphrase_always_on_device=passphrase_always_on_device,
        auto_lock_delay_ms=auto_lock_delay_ms,
        display_rotation=display_rotation,
        safety_checks=safety_checks,
    )

    out = client.call(settings)
    client.refresh_features()
    return out


@expect(messages.Success, field="message")
@session
def apply_flags(client, flags):
    out = client.call(messages.ApplyFlags(flags=flags))
    client.refresh_features()
    return out


@expect(messages.Success, field="message")
@session
def change_pin(client, remove=False):
    ret = client.call(messages.ChangePin(remove=remove))
    client.refresh_features()
    return ret


@expect(messages.Success, field="message")
@session
def change_wipe_code(client, remove=False):
    ret = client.call(messages.ChangeWipeCode(remove=remove))
    client.refresh_features()
    return ret


@expect(messages.Success, field="message")
@session
def sd_protect(client, operation):
    ret = client.call(messages.SdProtect(operation=operation))
    client.refresh_features()
    return ret


@expect(messages.Success, field="message")
@session
def wipe(client):
    ret = client.call(messages.WipeDevice())
    client.init_device()
    return ret


@session
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
@session
def backup(client):
    ret = client.call(messages.BackupDevice())
    client.refresh_features()
    return ret


@expect(messages.Success, field="message")
def cancel_authorization(client):
    return client.call(messages.CancelAuthorization())
