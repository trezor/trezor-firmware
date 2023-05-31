import utime
from typing import TYPE_CHECKING

import storage.cache as storage_cache
from trezor import config, utils, wire

if TYPE_CHECKING:
    from typing import Any, NoReturn
    from trezor.wire import Context, GenericContext


async def _request_sd_salt(
    ctx: wire.GenericContext, raise_cancelled_on_unavailable: bool = False
) -> bytearray | None:
    """Helper to get SD salt in a general manner, working for all models.

    Is model-specific, because some models (like TR/T2B1) do not even
    have SD card support (and we do not want to include SD-card connected code).
    """
    if not utils.USE_SD_CARD:
        return None
    else:
        from .sdcard import request_sd_salt, SdCardUnavailable

        try:
            return await request_sd_salt(ctx)
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
    ctx: GenericContext,
    prompt: str,
    attempts_remaining: int | None = None,
    allow_cancel: bool = True,
) -> str:
    from trezor.ui.layouts import request_pin_on_device

    return await request_pin_on_device(ctx, prompt, attempts_remaining, allow_cancel)


async def request_pin_confirm(ctx: Context, *args: Any, **kwargs: Any) -> str:
    from trezor.ui.layouts import pin_mismatch_popup, confirm_reenter_pin

    while True:
        pin1 = await request_pin(ctx, "Enter new PIN", *args, **kwargs)
        await confirm_reenter_pin(ctx)
        pin2 = await request_pin(ctx, "Re-enter new PIN", *args, **kwargs)
        if pin1 == pin2:
            return pin1
        await pin_mismatch_popup(ctx)


async def request_pin_and_sd_salt(
    ctx: Context, prompt: str, allow_cancel: bool = True
) -> tuple[str, bytearray | None]:
    if config.has_pin():
        pin = await request_pin(ctx, prompt, config.get_pin_rem(), allow_cancel)
        config.ensure_not_wipe_code(pin)
    else:
        pin = ""

    salt = await _request_sd_salt(ctx)

    return pin, salt


def _set_last_unlock_time() -> None:
    now = utime.ticks_ms()
    storage_cache.set_int(storage_cache.APP_COMMON_REQUEST_PIN_LAST_UNLOCK, now)


async def verify_user_pin(
    ctx: GenericContext = wire.DUMMY_CONTEXT,
    prompt: str = "Enter PIN",
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

        pin = await request_pin_on_device(
            ctx, prompt, config.get_pin_rem(), allow_cancel
        )
        config.ensure_not_wipe_code(pin)
    else:
        pin = ""

    salt = await _request_sd_salt(ctx, raise_cancelled_on_unavailable=True)
    if config.unlock(pin, salt):
        _set_last_unlock_time()
        return
    elif not config.has_pin():
        raise RuntimeError

    while retry:
        pin = await request_pin_on_device(  # type: ignore ["request_pin_on_device" is possibly unbound]
            ctx, "Enter PIN", config.get_pin_rem(), allow_cancel, wrong_pin=True
        )
        if config.unlock(pin, salt):
            _set_last_unlock_time()
            return

    raise wire.PinInvalid


async def error_pin_invalid(ctx: Context) -> NoReturn:
    from trezor.ui.layouts import show_error_and_raise

    await show_error_and_raise(
        ctx,
        "warning_wrong_pin",
        "The PIN you have entered is not valid.",
        "Wrong PIN",  # header
        exc=wire.PinInvalid,
    )
    assert False


async def error_pin_matches_wipe_code(ctx: Context) -> NoReturn:
    from trezor.ui.layouts import show_error_and_raise

    await show_error_and_raise(
        ctx,
        "warning_invalid_new_pin",
        "The new PIN must be different from your wipe code.",
        "Invalid PIN",  # header
        exc=wire.PinInvalid,
    )
    assert False
