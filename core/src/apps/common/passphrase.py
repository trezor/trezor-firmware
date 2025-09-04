from micropython import const
from typing import TYPE_CHECKING

import storage.device as storage_device
from trezor import utils
from trezor.wire import DataError

_MAX_PASSPHRASE_LEN = const(50)

if TYPE_CHECKING:
    from trezor.messages import ThpCreateNewSession

if __debug__:
    from trezor import log


def is_enabled() -> bool:
    return storage_device.is_passphrase_enabled()


async def get_passphrase(msg: ThpCreateNewSession) -> str:
    passphrase_always_on_device = storage_device.get_passphrase_always_on_device()

    # Device setting "disabled passphrase protection" is ignored
    if __debug__:
        if not is_enabled() and msg.passphrase:
            log.warning(
                __name__,
                "Creating new session with passphrase, ignoring device settings.",
            )

    # When always_on_device is True, messages with passphrase raise a DataError
    if passphrase_always_on_device and msg.passphrase is not None:
        raise DataError(
            "Providing passphrase in message is not allowed when PASSPHRASE_ALWAYS_ON_DEVICE is True."
        )

    if msg.on_device or passphrase_always_on_device:
        passphrase = await _get_on_device()
    else:
        passphrase = msg.passphrase or ""
        if passphrase:
            await _handle_displaying_passphrase_from_host(passphrase)

    if len(passphrase.encode()) > _MAX_PASSPHRASE_LEN:
        raise DataError(f"Maximum passphrase length is {_MAX_PASSPHRASE_LEN} bytes")

    return passphrase


async def _get_on_device() -> str:
    from trezor import workflow
    from trezor.ui.layouts import request_passphrase_on_device

    workflow.close_others()  # request exclusive UI access
    passphrase = await request_passphrase_on_device(_MAX_PASSPHRASE_LEN)

    return passphrase


async def _handle_displaying_passphrase_from_host(passphrase: str) -> None:
    from trezor.ui.layouts import (
        confirm_hidden_passphrase_from_host,
        show_passphrase_from_host,
    )

    # We want to hide the passphrase, or show it, according to settings.
    if storage_device.get_hide_passphrase_from_host():
        await confirm_hidden_passphrase_from_host()
    else:
        await show_passphrase_from_host(passphrase)


if not utils.USE_THP:

    async def get() -> str:
        from trezor import workflow

        if not is_enabled():
            return ""
        else:
            workflow.close_others()  # request exclusive UI access
            if storage_device.get_passphrase_always_on_device():
                from trezor.ui.layouts import request_passphrase_on_device

                passphrase = await request_passphrase_on_device(_MAX_PASSPHRASE_LEN)
            else:
                passphrase = await _request_on_host()
            if len(passphrase.encode()) > _MAX_PASSPHRASE_LEN:
                raise DataError(
                    f"Maximum passphrase length is {_MAX_PASSPHRASE_LEN} bytes"
                )

            return passphrase

    async def _request_on_host() -> str:
        from trezor import loop, workflow
        from trezor.messages import PassphraseAck, PassphraseRequest
        from trezor.ui.layouts import request_passphrase_on_host
        from trezor.wire.context import call

        async def _delay_request_passphrase_on_host() -> None:
            await loop.sleep(100)
            return request_passphrase_on_host()

        on_host = workflow.spawn(_delay_request_passphrase_on_host())
        try:
            request = PassphraseRequest()
            ack = await call(request, PassphraseAck)
            passphrase = ack.passphrase  # local_cache_attribute
        finally:
            # make sure on-host passphrase prompt closed after receiving an ack
            on_host.close()

        if ack.on_device:
            from trezor.ui.layouts import request_passphrase_on_device

            if passphrase is not None:
                raise DataError("Passphrase provided when it should not be")
            return await request_passphrase_on_device(_MAX_PASSPHRASE_LEN)

        if passphrase is None:
            raise DataError(
                "Passphrase not provided and on_device is False. Use empty string to set an empty passphrase."
            )

        # non-empty passphrase
        if passphrase:
            await _handle_displaying_passphrase_from_host(passphrase)

        return passphrase
