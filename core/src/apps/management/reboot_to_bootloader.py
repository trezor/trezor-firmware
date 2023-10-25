from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import NoReturn

    from trezor.messages import RebootToBootloader


async def reboot_to_bootloader(msg: RebootToBootloader) -> NoReturn:
    from ubinascii import hexlify

    from trezor import io, loop, utils, wire
    from trezor.enums import BootCommand
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_action, confirm_firmware_update
    from trezor.wire.context import get_context


    if (
        msg.boot_command == BootCommand.INSTALL_UPGRADE
        and msg.firmware_header is not None
    ):
        # check and parse received firmware header
        hdr = utils.check_firmware_header(msg.firmware_header)
        if hdr is None:
            raise wire.DataError("Invalid firmware header.")
        else:
            # vendor must be the same
            if hdr["vendor"] != utils.firmware_vendor():
                raise wire.DataError("Different firmware vendor.")

            current_version = (
                int(utils.VERSION_MAJOR),
                int(utils.VERSION_MINOR),
                int(utils.VERSION_PATCH),
            )

            # firmware must be newer
            if hdr["version"] <= current_version:
                raise wire.DataError("Not a firmware upgrade.")

            version_str = ".".join(map(str, hdr["version"]))

            await confirm_firmware_update(
                description=f"Firmware version {version_str}\nby {hdr['vendor']}",
                fingerprint=hexlify(hdr["fingerprint"]).decode(),
            )
            boot_command = BootCommand.INSTALL_UPGRADE
            boot_args = hdr["hash"]

    else:
        await confirm_action(
            "reboot",
            "Go to bootloader",
            "Do you want to restart Trezor in bootloader mode?",
            verb="Restart",
        )
        boot_command = BootCommand.STOP_AND_WAIT
        boot_args = None

    ctx = get_context()
    await ctx.write(Success(message="Rebooting"))
    # make sure the outgoing USB buffer is flushed
    await loop.wait(ctx.iface.iface_num() | io.POLL_WRITE)
    # reboot to the bootloader, pass the firmware header hash if any
    utils.reboot_to_bootloader(boot_command, boot_args)
    raise RuntimeError
