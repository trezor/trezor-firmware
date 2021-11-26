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

import os
import time
from typing import TYPE_CHECKING, Callable, Optional

from . import messages
from .exceptions import Cancelled
from .tools import expect, session

if TYPE_CHECKING:
    from .client import TrezorClient
    from .protobuf import MessageType


RECOVERY_BACK = "\x08"  # backspace character, sent literally


@expect(messages.Success, field="message", ret_type=str)
@session
def apply_settings(
    client: "TrezorClient",
    label: Optional[str] = None,
    language: Optional[str] = None,
    use_passphrase: Optional[bool] = None,
    homescreen: Optional[bytes] = None,
    passphrase_always_on_device: Optional[bool] = None,
    auto_lock_delay_ms: Optional[int] = None,
    display_rotation: Optional[int] = None,
    safety_checks: Optional[messages.SafetyCheckLevel] = None,
    experimental_features: Optional[bool] = None,
) -> "MessageType":
    settings = messages.ApplySettings(
        label=label,
        language=language,
        use_passphrase=use_passphrase,
        homescreen=homescreen,
        passphrase_always_on_device=passphrase_always_on_device,
        auto_lock_delay_ms=auto_lock_delay_ms,
        display_rotation=display_rotation,
        safety_checks=safety_checks,
        experimental_features=experimental_features,
    )

    out = client.call(settings)
    client.refresh_features()
    return out


@expect(messages.Success, field="message", ret_type=str)
@session
def apply_flags(client: "TrezorClient", flags: int) -> "MessageType":
    out = client.call(messages.ApplyFlags(flags=flags))
    client.refresh_features()
    return out


@expect(messages.Success, field="message", ret_type=str)
@session
def change_pin(client: "TrezorClient", remove: bool = False) -> "MessageType":
    ret = client.call(messages.ChangePin(remove=remove))
    client.refresh_features()
    return ret


@expect(messages.Success, field="message", ret_type=str)
@session
def change_wipe_code(client: "TrezorClient", remove: bool = False) -> "MessageType":
    ret = client.call(messages.ChangeWipeCode(remove=remove))
    client.refresh_features()
    return ret


@expect(messages.Success, field="message", ret_type=str)
@session
def sd_protect(
    client: "TrezorClient", operation: messages.SdProtectOperationType
) -> "MessageType":
    ret = client.call(messages.SdProtect(operation=operation))
    client.refresh_features()
    return ret


@expect(messages.Success, field="message", ret_type=str)
@session
def wipe(client: "TrezorClient") -> "MessageType":
    ret = client.call(messages.WipeDevice())
    client.init_device()
    return ret


@session
def recover(
    client: "TrezorClient",
    word_count: int = 24,
    passphrase_protection: bool = False,
    pin_protection: bool = True,
    label: Optional[str] = None,
    language: str = "en-US",
    input_callback: Optional[Callable] = None,
    type: messages.RecoveryDeviceType = messages.RecoveryDeviceType.ScrambledWords,
    dry_run: bool = False,
    u2f_counter: Optional[int] = None,
) -> "MessageType":
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
            assert input_callback is not None
            inp = input_callback(res.type)
            res = client.call(messages.WordAck(word=inp))
        except Cancelled:
            res = client.call(messages.Cancel())

    client.init_device()
    return res


@expect(messages.Success, field="message", ret_type=str)
@session
def reset(
    client: "TrezorClient",
    display_random: bool = False,
    strength: Optional[int] = None,
    passphrase_protection: bool = False,
    pin_protection: bool = True,
    label: Optional[str] = None,
    language: str = "en-US",
    u2f_counter: int = 0,
    skip_backup: bool = False,
    no_backup: bool = False,
    backup_type: messages.BackupType = messages.BackupType.Bip39,
) -> "MessageType":
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


@expect(messages.Success, field="message", ret_type=str)
@session
def backup(client: "TrezorClient") -> "MessageType":
    ret = client.call(messages.BackupDevice())
    client.refresh_features()
    return ret


@expect(messages.Success, field="message", ret_type=str)
def cancel_authorization(client: "TrezorClient") -> "MessageType":
    return client.call(messages.CancelAuthorization())


@session
@expect(messages.Success, field="message", ret_type=str)
def reboot_to_bootloader(client: "TrezorClient") -> "MessageType":
    return client.call(messages.RebootToBootloader())
