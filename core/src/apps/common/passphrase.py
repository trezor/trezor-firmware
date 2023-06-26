from micropython import const

import storage.device as storage_device
from trezor.wire import DataError

_MAX_PASSPHRASE_LEN = const(50)


def is_enabled() -> bool:
    return storage_device.is_passphrase_enabled()


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
            raise DataError(f"Maximum passphrase length is {_MAX_PASSPHRASE_LEN} bytes")

        return passphrase


async def _request_on_host() -> str:
    from trezor.messages import PassphraseAck, PassphraseRequest
    from trezor.ui.layouts import request_passphrase_on_host
    from trezor.wire.context import call

    request_passphrase_on_host()

    request = PassphraseRequest()
    ack = await call(request, PassphraseAck)
    passphrase = ack.passphrase  # local_cache_attribute

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
        from trezor.ui.layouts import confirm_action, confirm_blob

        # We want to hide the passphrase, or show it, according to settings.
        if storage_device.get_hide_passphrase_from_host():
            explanation = "Passphrase provided by host will be used but will not be displayed due to the device settings."
            await confirm_action(
                "passphrase_host1_hidden",
                "Hidden wallet",
                description=f"Access hidden wallet?\n{explanation}",
            )
        else:
            await confirm_action(
                "passphrase_host1",
                "Hidden wallet",
                description="Next screen will show the passphrase.",
                verb="Continue",
            )

            await confirm_blob(
                "passphrase_host2",
                "Confirm passphrase",
                passphrase,
            )

    return passphrase
