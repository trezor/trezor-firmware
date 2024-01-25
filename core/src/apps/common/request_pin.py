import utime
from typing import Any, NoReturn

import storage.cache as storage_cache
from trezor import TR, config, utils, wire
from trezor.ui.layouts import show_error_and_raise


async def _request_sd_salt(
    raise_cancelled_on_unavailable: bool = False,
) -> bytearray | None:
    """Helper to get SD salt in a general manner, working for all models.

    Is model-specific, because some models (like TR/T2B1) do not even
    have SD card support (and we do not want to include SD-card connected code).
    """
    if not utils.USE_SD_CARD:
        return None
    else:
        from .sdcard import SdCardUnavailable, request_sd_salt

        try:
            return await request_sd_salt()
        except SdCardUnavailable:
            if raise_cancelled_on_unavailable:
                raise wire.PinCancelled("SD salt is unavailable")
            else:
                raise


def can_lock_device() -> bool:
    """Return True if the device has a PIN set or SD-protect enabled (when supported)."""
    # TR/T2B1 does not support SD card
    if not utils.USE_SD_CARD:
        return config.has_pin()
    else:
        import storage.sd_salt

        return config.has_pin() or storage.sd_salt.is_enabled()


async def request_pin(
    prompt: str,
    attempts_remaining: int | None = None,
    allow_cancel: bool = True,
) -> str:
    from trezor.ui.layouts import request_pin_on_device

    return await request_pin_on_device(prompt, attempts_remaining, allow_cancel)


async def request_pin_confirm(*args: Any, **kwargs: Any) -> str:
    from trezor.ui.layouts import confirm_reenter_pin, pin_mismatch_popup

    while True:
        pin1 = await request_pin(TR.pin__enter_new, *args, **kwargs)
        await confirm_reenter_pin()
        pin2 = await request_pin(TR.pin__reenter_new, *args, **kwargs)
        if pin1 == pin2:
            return pin1
        await pin_mismatch_popup()


async def request_pin_and_sd_salt(
    prompt: str, allow_cancel: bool = True
) -> tuple[str, bytearray | None]:
    if config.has_pin():
        pin = await request_pin(prompt, config.get_pin_rem(), allow_cancel)
        config.ensure_not_wipe_code(pin)
    else:
        pin = ""

    salt = await _request_sd_salt()

    return pin, salt


def _set_last_unlock_time() -> None:
    now = utime.ticks_ms()
    storage_cache.set_int(storage_cache.APP_COMMON_REQUEST_PIN_LAST_UNLOCK, now)


_DEF_ARG_PIN_ENTER: str = TR.pin__enter


async def verify_user_pin(
    prompt: str = _DEF_ARG_PIN_ENTER,
    allow_cancel: bool = True,
    retry: bool = True,
    cache_time_ms: int = 0,
) -> None:
    # _get_last_unlock_time
    last_unlock = int.from_bytes(
        storage_cache.get(storage_cache.APP_COMMON_REQUEST_PIN_LAST_UNLOCK, b""), "big"
    )

    if (
        cache_time_ms
        and last_unlock
        and utime.ticks_ms() - last_unlock <= cache_time_ms
        and config.is_unlocked()
    ):
        return

    if config.has_pin():
        from trezor.ui.layouts import request_pin_on_device

        pin = await request_pin_on_device(prompt, config.get_pin_rem(), allow_cancel)
        config.ensure_not_wipe_code(pin)
    else:
        pin = ""

    salt = await _request_sd_salt(raise_cancelled_on_unavailable=True)
    if config.unlock(pin, salt):
        _set_last_unlock_time()
        return
    elif not config.has_pin():
        raise RuntimeError

    while retry:
        pin = await request_pin_on_device(  # type: ignore ["request_pin_on_device" is possibly unbound]
            TR.pin__enter, config.get_pin_rem(), allow_cancel, wrong_pin=True
        )
        if config.unlock(pin, salt):
            _set_last_unlock_time()
            return

    raise wire.PinInvalid


async def error_pin_invalid() -> NoReturn:
    await show_error_and_raise(
        "warning_wrong_pin",
        TR.pin__entered_not_valid,
        TR.pin__wrong_pin,  # header
        exc=wire.PinInvalid,
    )
    assert False


async def error_pin_matches_wipe_code() -> NoReturn:
    await show_error_and_raise(
        "warning_invalid_new_pin",
        TR.pin__diff_from_wipe_code,
        TR.pin__invalid_pin,  # header
        exc=wire.PinInvalid,
    )
    assert False
