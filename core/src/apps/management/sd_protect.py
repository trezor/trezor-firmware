from typing import TYPE_CHECKING

import storage.device as storage_device
import storage.sd_salt as storage_sd_salt
from trezor import TR, config
from trezor.enums import SdProtectOperationType
from trezor.messages import Success
from trezor.ui.layouts import show_success
from trezor.wire import ProcessError

from apps.common.request_pin import error_pin_invalid, request_pin_and_sd_salt
from apps.common.sdcard import ensure_sdcard

if TYPE_CHECKING:
    from typing import Awaitable

    from trezor.messages import SdProtect


def _make_salt() -> tuple[bytes, bytes, bytes]:
    from trezor.crypto import random

    salt = random.bytes(storage_sd_salt.SD_SALT_LEN_BYTES)
    auth_key = random.bytes(storage_device.SD_SALT_AUTH_KEY_LEN_BYTES)
    tag = storage_sd_salt.compute_auth_tag(salt, auth_key)
    return salt, auth_key, tag


async def _set_salt(salt: bytes, salt_tag: bytes, stage: bool = False) -> None:
    from apps.common.sdcard import confirm_retry_sd

    while True:
        await ensure_sdcard()
        try:
            return storage_sd_salt.set_sd_salt(salt, salt_tag, stage)
        except OSError:
            await confirm_retry_sd(ProcessError("SD card I/O error."))


async def sd_protect(msg: SdProtect) -> Success:
    from trezor.wire import NotInitialized

    if not storage_device.is_initialized():
        raise NotInitialized("Device is not initialized")

    if msg.operation == SdProtectOperationType.ENABLE:
        return await _sd_protect_enable(msg)
    elif msg.operation == SdProtectOperationType.DISABLE:
        return await _sd_protect_disable(msg)
    elif msg.operation == SdProtectOperationType.REFRESH:
        return await _sd_protect_refresh(msg)
    else:
        raise ProcessError("Unknown operation")


async def _sd_protect_enable(msg: SdProtect) -> Success:
    from apps.common.request_pin import request_pin

    if storage_sd_salt.is_enabled():
        raise ProcessError("SD card protection already enabled")

    # Confirm that user wants to proceed with the operation.
    await require_confirm_sd_protect(msg)

    # Make sure SD card is present.
    await ensure_sdcard()

    # Get the current PIN.
    if config.has_pin():
        pin = await request_pin(TR.pin__enter, config.get_pin_rem())
    else:
        pin = ""

    # Check PIN and prepare salt file.
    salt, salt_auth_key, salt_tag = _make_salt()
    await _set_salt(salt, salt_tag)

    if not config.change_pin(pin, pin, None, salt):
        # Wrong PIN. Clean up the prepared salt file.
        try:
            storage_sd_salt.remove_sd_salt()
        except Exception:
            # The cleanup is not necessary for the correct functioning of
            # SD-protection. If it fails for any reason, we suppress the
            # exception, because primarily we need to raise wire.PinInvalid.
            pass
        await error_pin_invalid()

    storage_device.set_sd_salt_auth_key(salt_auth_key)

    await show_success("success_sd", TR.sd_card__enabled)
    return Success(message="SD card protection enabled")


async def _sd_protect_disable(msg: SdProtect) -> Success:
    if not storage_sd_salt.is_enabled():
        raise ProcessError("SD card protection not enabled")

    # Note that the SD card doesn't need to be present in order to disable SD
    # protection. The cleanup will not happen in such case, but that does not matter.

    # Confirm that user wants to proceed with the operation.
    await require_confirm_sd_protect(msg)

    # Get the current PIN and salt from the SD card.
    pin, salt = await request_pin_and_sd_salt(TR.pin__enter)

    # Check PIN and remove salt.
    if not config.change_pin(pin, pin, salt, None):
        await error_pin_invalid()

    storage_device.set_sd_salt_auth_key(None)

    try:
        # Clean up.
        storage_sd_salt.remove_sd_salt()
    except Exception:
        # The cleanup is not necessary for the correct functioning of
        # SD-protection. If it fails for any reason, we suppress the exception,
        # because overall SD-protection was successfully disabled.
        pass

    await show_success("success_sd", TR.sd_card__disabled)
    return Success(message="SD card protection disabled")


async def _sd_protect_refresh(msg: SdProtect) -> Success:
    if not storage_sd_salt.is_enabled():
        raise ProcessError("SD card protection not enabled")

    # Confirm that user wants to proceed with the operation.
    await require_confirm_sd_protect(msg)

    # Make sure SD card is present.
    await ensure_sdcard()

    # Get the current PIN and salt from the SD card.
    pin, old_salt = await request_pin_and_sd_salt(TR.pin__enter)

    # Check PIN and change salt.
    new_salt, new_auth_key, new_salt_tag = _make_salt()
    await _set_salt(new_salt, new_salt_tag, stage=True)

    if not config.change_pin(pin, pin, old_salt, new_salt):
        await error_pin_invalid()

    storage_device.set_sd_salt_auth_key(new_auth_key)

    try:
        # Clean up.
        storage_sd_salt.commit_sd_salt()
    except Exception:
        # If the cleanup fails, then request_sd_salt() will bring the SD card
        # into a consistent state. We suppress the exception, because overall
        # SD-protection was successfully refreshed.
        pass

    await show_success("success_sd", TR.sd_card__refreshed)
    return Success(message="SD card protection refreshed")


def require_confirm_sd_protect(msg: SdProtect) -> Awaitable[None]:
    from trezor.ui.layouts import confirm_action

    if msg.operation == SdProtectOperationType.ENABLE:
        text = TR.sd_card__enable
    elif msg.operation == SdProtectOperationType.DISABLE:
        text = TR.sd_card__disable
    elif msg.operation == SdProtectOperationType.REFRESH:
        text = TR.sd_card__refresh
    else:
        raise ProcessError("Unknown operation")

    return confirm_action("set_sd", TR.sd_card__title, description=text)
