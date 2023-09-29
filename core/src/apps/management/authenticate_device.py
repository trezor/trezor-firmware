from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import AuthenticateDevice, AuthenticityProof


async def authenticate_device(msg: AuthenticateDevice) -> AuthenticityProof:
    from trezor import utils, wire
    from trezor.crypto import optiga
    from trezor.crypto.der import read_length
    from trezor.crypto.hashlib import sha256
    from trezor.loop import sleep
    from trezor.messages import AuthenticityProof
    from trezor.ui.layouts import confirm_action
    from trezor.ui.layouts.progress import progress
    from trezor.utils import BufferReader, bootloader_locked

    from apps.common.writers import write_compact_size

    if not bootloader_locked():
        raise wire.ProcessError("Cannot authenticate since bootloader is unlocked.")

    await confirm_action(
        "authenticate_device",
        "Authenticate device",
        description=f"Allow connected computer to confirm your {utils.MODEL_FULL_NAME} is genuine?",
        verb="Allow",
    )

    header = b"AuthenticateDevice:"
    h = utils.HashWriter(sha256())
    write_compact_size(h, len(header))
    h.extend(header)
    write_compact_size(h, len(msg.challenge))
    h.extend(msg.challenge)

    spinner = progress("", description="Checking authenticity...")
    spinner.report(0)

    try:
        signature = optiga.sign(optiga.DEVICE_ECC_KEY_INDEX, h.get_digest())
    except optiga.SigningInaccessible:
        raise wire.ProcessError("Signing inaccessible.")

    certificates = []
    r = BufferReader(optiga.get_certificate(optiga.DEVICE_CERT_INDEX))
    while r.remaining_count() > 0:
        cert_begin = r.offset
        if r.get() != 0x30:
            wire.FirmwareError("Device certificate is corrupted.")
        n = read_length(r)
        cert_len = r.offset - cert_begin + n
        r.seek(cert_begin)
        certificates.append(r.read_memoryview(cert_len))

    if not utils.DISABLE_ANIMATION:
        frame_delay = sleep(60)
        for i in range(1, 20):
            spinner.report(i * 50)
            await frame_delay

        spinner.report(1000)

    return AuthenticityProof(
        certificates=certificates,
        signature=signature,
    )
