from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from buffer_types import AnyBytes

    from trezor.messages import AuthenticateDevice, AuthenticityProof
    from trezor.utils import BufferReader


def parse_cert_chain(r: BufferReader) -> list[AnyBytes]:
    from trezor import wire
    from trezor.crypto.der import read_length

    certificates = []
    while r.remaining_count() > 0:
        cert_begin = r.offset
        if r.get() != 0x30:
            raise wire.FirmwareError("Device certificate is corrupted.")
        n = read_length(r)
        cert_len = r.offset - cert_begin + n
        r.seek(cert_begin)
        certificates.append(r.read_memoryview(cert_len))

    return certificates


async def authenticate_device(msg: AuthenticateDevice) -> AuthenticityProof:
    from trezor import TR, utils, wire
    from trezor.crypto import optiga
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
        TR.authenticate__header,
        description=TR.authenticate__confirm_template.format(utils.MODEL_FULL_NAME),
        verb=TR.buttons__allow,
        prompt_screen=True,
    )

    header = b"AuthenticateDevice:"
    challenge_bytes = utils.empty_bytearray(1 + len(header) + 1 + len(msg.challenge))
    write_compact_size(challenge_bytes, len(header))
    challenge_bytes.extend(header)
    write_compact_size(challenge_bytes, len(msg.challenge))
    challenge_bytes.extend(msg.challenge)

    spinner = progress(TR.progress__authenticity_check)
    spinner.report(0)

    try:
        optiga_signature = optiga.sign(
            optiga.DEVICE_ECC_KEY_INDEX, sha256(challenge_bytes).digest()
        )
    except optiga.SigningInaccessible:
        raise wire.ProcessError("Optiga signing inaccessible.")

    r = BufferReader(optiga.get_certificate(optiga.DEVICE_CERT_INDEX))
    optiga_certificates = parse_cert_chain(r)

    tropic_certificates = None
    tropic_signature = None
    if utils.USE_TROPIC:
        from trezor.crypto import tropic

        try:
            tropic_signature = tropic.sign(tropic.DEVICE_KEY_SLOT, challenge_bytes)
        except tropic.TropicError:
            raise wire.ProcessError("Tropic signing failed.")

        r = BufferReader(tropic.get_user_data(tropic.DEVICE_CERT_INDEX))
        tropic_certificates = parse_cert_chain(r)

    if not utils.DISABLE_ANIMATION:
        frame_delay = sleep(60)
        for i in range(1, 20):
            spinner.report(i * 50)
            await frame_delay

        spinner.report(1000)

    return AuthenticityProof(
        optiga_certificates=optiga_certificates,
        optiga_signature=optiga_signature,
        tropic_certificates=tropic_certificates,
        tropic_signature=tropic_signature,
    )
