from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import NoReturn

    from trezor.messages import RebootToBootloader


async def reboot_to_bootloader(msg: RebootToBootloader) -> NoReturn:
    from trezor import io, loop, utils
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_action
    from trezor.wire.context import get_context

    await confirm_action(
        "reboot",
        "Go to bootloader",
        "Do you want to restart Trezor in bootloader mode?",
        verb="Restart",
    )
    ctx = get_context()
    await ctx.write(Success(message="Rebooting"))
    # make sure the outgoing USB buffer is flushed
    await loop.wait(ctx.iface.iface_num() | io.POLL_WRITE)
    utils.reboot_to_bootloader()
    raise RuntimeError
