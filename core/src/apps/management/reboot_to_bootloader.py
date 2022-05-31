from typing import TYPE_CHECKING

from trezor import io, loop, utils, wire
from trezor.messages import RebootToBootloader, Success
from trezor.ui.layouts import confirm_action

if TYPE_CHECKING:
    from typing import NoReturn

    pass


async def reboot_to_bootloader(ctx: wire.Context, msg: RebootToBootloader) -> NoReturn:
    await confirm_action(
        ctx,
        "reboot",
        "Go to bootloader",
        "Do you want to restart Trezor in bootloader mode?",
        hold_danger=True,
        verb="Restart",
    )
    await ctx.write(Success(message="Rebooting"))
    # make sure the outgoing USB buffer is flushed
    await loop.wait(ctx.iface.iface_num() | io.POLL_WRITE)
    utils.reboot_to_bootloader()
    raise RuntimeError
