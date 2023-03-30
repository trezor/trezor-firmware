from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import RebootToBootloader
    from typing import NoReturn
    from trezor.wire import Context


async def reboot_to_bootloader(ctx: Context, msg: RebootToBootloader) -> NoReturn:
    from trezor import io, loop, utils
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_action

    await confirm_action(
        ctx,
        "reboot",
        "Go to bootloader",
        "Do you want to restart Trezor in bootloader mode?",
        verb="Restart",
    )
    await ctx.write(Success(message="Rebooting"))
    # make sure the outgoing USB buffer is flushed
    await loop.wait(ctx.iface.iface_num() | io.POLL_WRITE)
    utils.reboot_to_bootloader()
    raise RuntimeError
