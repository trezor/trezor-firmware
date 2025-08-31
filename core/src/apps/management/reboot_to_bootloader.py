import utime
from micropython import const
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import NoReturn

    from trezor.enums import BootCommand
    from trezor.messages import RebootToBootloader


_REBOOT_SUCCESS_TIMEOUT_MS = const(500)


async def install_upgrade(
    firmware_header: bytes, language_data_length: int
) -> tuple[BootCommand, bytes]:
    from ubinascii import hexlify

    from trezor import TR, utils, wire
    from trezor.enums import BootCommand
    from trezor.ui.layouts import confirm_firmware_update, show_wait_text

    from apps.management.change_language import do_change_language

    # check and parse received firmware header
    try:
        hdr = utils.check_firmware_header(firmware_header)
    except Exception:
        raise wire.DataError("Invalid firmware header.")

    # vendor must be the same
    if hdr.vendor != utils.firmware_vendor():
        raise wire.DataError("Different firmware vendor.")

    # firmware must be newer
    if hdr.version <= utils.VERSION:
        raise wire.DataError("Not a firmware upgrade.")

    version_str = ".".join(map(str, hdr.version[:3]))

    await confirm_firmware_update(
        description=TR.reboot_to_bootloader__version_by_template.format(
            version_str, hdr.vendor
        ),
        fingerprint=hexlify(hdr.fingerprint).decode(),
    )

    # send language data
    if language_data_length > 0:
        show_wait_text(TR.reboot_to_bootloader__just_a_moment)
        try:
            await do_change_language(
                language_data_length,
                show_display=False,
                expected_version=hdr.version,
                report=lambda i: None,
            )
        except MemoryError:
            # Continue firmware upgrade even if language change failed
            pass

    return BootCommand.INSTALL_UPGRADE, hdr.hash


async def reboot_to_bootloader(msg: RebootToBootloader) -> NoReturn:
    from trezor import TR, io, loop, utils
    from trezor.enums import BootCommand
    from trezor.messages import Success
    from trezor.ui.layouts import confirm_action
    from trezor.wire.context import get_context

    # Bootloader will only allow the INSTALL_UPGRADE flow for official images.
    # This is to prevent a problematic custom signed firmware from self-updating
    # through this code path.
    # For convenience, we block unofficial firmwares from jumping to bootloader
    # this way, so that the user doesn't get mysterious "install failed" errors.
    # (It would be somewhat nicer if this was a compile-time flag, but oh well.)
    is_official = utils.firmware_vendor() != "UNSAFE, DO NOT USE!"
    if (
        msg.boot_command == BootCommand.INSTALL_UPGRADE
        and msg.firmware_header is not None
        and is_official
    ):
        boot_command, boot_args = await install_upgrade(
            msg.firmware_header, msg.language_data_length
        )

    else:
        await confirm_action(
            "reboot",
            TR.reboot_to_bootloader__title,
            TR.reboot_to_bootloader__restart,
            verb=TR.buttons__restart,
            prompt_screen=True,
        )
        boot_command = BootCommand.STOP_AND_WAIT
        boot_args = None

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
    # reboot to the bootloader, pass the firmware header hash if any
    utils.reboot_to_bootloader(boot_command, boot_args)
    raise RuntimeError
