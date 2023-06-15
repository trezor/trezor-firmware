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
from .exceptions import Cancelled, TrezorException
from .tools import Address, expect, session

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
    """Change device settings.

    Args:
        client: TrezorClient instance
        label: New label for the device
        language: New language for the device
        use_passphrase: Whether to use passphrase
        homescreen: New homescreen for the device
        passphrase_always_on_device: Whether to always ask for passphrase on device
        auto_lock_delay_ms: Delay in milliseconds after which the device with PIN will lock itself
        display_rotation: Display rotation in degrees from North
        safety_checks: Safety check level
        experimental_features: Whether to enable experimental features

    Returns:
        str: Success message
    """
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
    """Change device flags.

    Flags/bits can be only set, not unset.

    Args:
        client: TrezorClient instance
        flags: New flags for the device - bitmask

    Returns:
        str: Success message
    """
    out = client.call(messages.ApplyFlags(flags=flags))
    client.refresh_features()
    return out


@expect(messages.Success, field="message", ret_type=str)
@session
def change_pin(client: "TrezorClient", remove: bool = False) -> "MessageType":
    """Set up, change, or remove PIN on the device.

    Args:
        client: TrezorClient instance
        remove: Set to True to remove the PIN.

    Returns:
        str: Success message
    """
    ret = client.call(messages.ChangePin(remove=remove))
    client.refresh_features()
    return ret


@expect(messages.Success, field="message", ret_type=str)
@session
def change_wipe_code(client: "TrezorClient", remove: bool = False) -> "MessageType":
    """Set up, change, or remove wipe code on the device.

    When entered instead of the unlock PIN, the wipe code, or "duress PIN", will cause the device to be erased.
    Wipe code can only be configured when the unlock PIN is already set up.

    Args:
        client: TrezorClient instance
        remove: Set to True to remove the wipe code.

    Args:
        client: TrezorClient instance
        remove: Whether to remove the wipe-code. False mean setting a new wipe-code.

    Returns:
        str: Success message
    """
    ret = client.call(messages.ChangeWipeCode(remove=remove))
    client.refresh_features()
    return ret


@expect(messages.Success, field="message", ret_type=str)
@session
def sd_protect(
    client: "TrezorClient", operation: messages.SdProtectOperationType
) -> "MessageType":
    """Update SD card protection.

    Args:
        client: TrezorClient instance
        operation: Operation to perform

    Returns:
        str: Success message
    """
    ret = client.call(messages.SdProtect(operation=operation))
    client.refresh_features()
    return ret


@expect(messages.Success, field="message", ret_type=str)
@session
def wipe(client: "TrezorClient") -> "MessageType":
    """Wipe the device.

    In normal mode, this will erase the seed and all user settings.

    When sent in bootloader mode, this will also completely erase the firmware.

    Args:
        client: TrezorClient instance

    Returns:
        str: Success message
    """
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
    """Restore a wallet from a mnemonic seed.

    Must be either run on a wiped device, or with the `dry_run` flag set to True.

    On Trezor 1, `input_callback` is required. When `recovery_type` is `ScrambledWords`,
    each call to callback must return a single word from the mnemonic seed. Trezor
    screen specifies which word to enter.

    When `recovery_type` is `Matrix`, each call to callback must return a single digit
    corresponding to the position of a letter / word in the matrix on the Trezor screen,
    or a backspace character.

    On Trezors with on-screen entry, `input_callback` is ignored.

    Args:
        client: TrezorClient instance
        word_count: Number of words in mnemonic
        passphrase_protection: Whether to enable passphrase protection
        pin_protection: Whether to enable PIN protection
        label: Label for the device
        language: Language for the device
        input_callback: Function to be called for each word. It should return the word.
        type: Recovery type
        dry_run: Whether to perform a dry run - simulate recovery
        u2f_counter: U2F counter value

    Returns:
        Success message
    """
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
    """Create a new wallet on the device.

    Must be run on a wiped device.

    Args:
        client: TrezorClient instance
        display_random: Display entropy generated by the device
        strength: Strength of the generated seed in bits
        passphrase_protection: Whether to enable passphrase protection
        pin_protection: Whether to enable PIN protection
        label: Label for the device
        language: Language for the device
        u2f_counter: U2F counter value
        skip_backup: Postpone seed backup to `BackupDevice` workflow
        no_backup: Indicate that no backup (seedless mode) is going to be made
        backup_type: Type of backup to be made (BIP39, Shamir, SuperShamir)

    Returns:
        str: Success message
    """
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
    """Back up the mnemonic seed.

    Must be run on a device that is already set up but is not backed up yet.
    Backup can be only performed once after device setup -- either as part of the
    `reset` workflow, or separately using this function.

    The backup process is fully interactive on the Trezor device itself and does not
    interact with the host.

    Args:
        client: TrezorClient instance

    Returns:
        str: Success message
    """
    ret = client.call(messages.BackupDevice())
    client.refresh_features()
    return ret


@expect(messages.Success, field="message", ret_type=str)
def cancel_authorization(client: "TrezorClient") -> "MessageType":
    """Cancel any outstanding authorization in the current session.

    Args:
        client: TrezorClient instance

    Returns:
        str: Success message
    """
    return client.call(messages.CancelAuthorization())


@expect(messages.UnlockedPathRequest, field="mac", ret_type=bytes)
def unlock_path(client: "TrezorClient", n: "Address") -> "MessageType":
    """Ask device to unlock a subtree of the keychain.

    Args:
        client: TrezorClient instance
        n: Path to unlock

    Returns:
        MAC of the path: bytes
    """
    resp = client.call(messages.UnlockPath(address_n=n))

    # Cancel the UnlockPath workflow now that we have the authentication code.
    try:
        client.call(messages.Cancel())
    except Cancelled:
        return resp
    else:
        raise TrezorException("Unexpected response in UnlockPath flow")


@session
@expect(messages.Success, field="message", ret_type=str)
def reboot_to_bootloader(client: "TrezorClient") -> "MessageType":
    """Reboot firmware to bootloader mode.

    Args:
        client: TrezorClient instance

    Returns:
        str: Success message
    """
    return client.call(messages.RebootToBootloader())


@expect(messages.Success, field="message", ret_type=str)
@session
def set_busy(client: "TrezorClient", expiry_ms: Optional[int]) -> "MessageType":
    """Sets or clears the busy state of the device.

    Args:
        client: TrezorClient instance
        expiry_ms: Expiry time in milliseconds. If None, clears the busy state.

    Returns:
        str: Success message

    In the busy state the device shows a "Do not disconnect" message instead of the homescreen.
    Setting `expiry_ms=None` clears the busy state.
    """
    ret = client.call(messages.SetBusy(expiry_ms=expiry_ms))
    client.refresh_features()
    return ret
