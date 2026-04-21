import utime
from micropython import const
from typing import TYPE_CHECKING
from trezor import utils

if TYPE_CHECKING:
    from typing import NoReturn

    from trezor.messages import UnlockBootloader


_REBOOT_SUCCESS_TIMEOUT_MS = const(500)


def _unlock_bootloader():
    if utils.USE_OPTIGA:
        from trezor.crypto import optiga

        # delete?? optiga.DEVICE_ECC_KEY_INDEX
    if utils.USE_TROPIC:
        from trezor.crypto import tropic

        # delete tropic.DEVICE_KEY_SLOT
        # delete tropic.FIDO_KEY_SLOT
        pass


async def unlock_bootloader(msg: UnlockBootloader) -> NoReturn:
    from trezor import TR, io, loop, utils
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_action
    from trezor.wire.context import get_context

    # Bootloader will allow the bootloader-unlock flow only from official images.
    # This is to prevent a custom signed firmware from jumping to bootloader
    # this way, as custom firmwares can be used only with an already unlocked
    # bootloader.
    is_official = utils.firmware_vendor() != "UNSAFE, DO NOT USE!"
    if not is_official:
        raise Exception  # TODO change

    await confirm_action(
        "unlock_bootloader",
        TR.reboot_to_bootloader__title,  # TODO change
        TR.reboot_to_bootloader__restart,  # TODO change
        verb=TR.buttons__restart,  # TODO change
        prompt_screen=True,
    )

    _unlock_bootloader()

    ctx = get_context()
    # After ACK-ing the `Success` message (over THP), the host may already be waiting for the bootloader to start.
    # In case this THP ACK packet is lost, the device should stop retransmissions, and reboot anyway.
    res = await loop.race(
        ctx.write(Success(message="Rebooting")), loop.sleep(_REBOOT_SUCCESS_TIMEOUT_MS)
    )
    if res is None:
        # make sure the outgoing buffer is flushed
        await loop.wait(ctx.iface.iface_num() | io.POLL_WRITE)

    utime.sleep_ms(10)

    # reboot to the bootloader and start its bootloader-unlock flow
    utils.reboot_and_unlock_bootloader()
    raise RuntimeError
