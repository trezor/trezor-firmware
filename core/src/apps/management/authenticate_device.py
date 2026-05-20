from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from buffer_types import AnyBytes

    from trezor.messages import AuthenticateDevice, AuthenticityProof, Success


async def authenticate_device(msg: AuthenticateDevice) -> AuthenticityProof | Success:
    from trezor import TR, utils, wire
    from trezor.crypto import optiga
    from trezor.crypto.hashlib import sha256
    from trezor.loop import sleep
    from trezor.messages import AuthenticityProof, Success
    from trezor.ui.layouts import confirm_action
    from trezor.ui.layouts.progress import progress
    from trezor.utils import BufferReader, bootloader_locked

    from apps.common.certificates import parse_cert_chain
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

    mcu_certificates = None
    mcu_signature = None
    if utils.USE_MCU_ATTESTATION:
        from trezor.crypto import mcu

        try:
            mcu_signature = mcu.sign(challenge_bytes)
        except RuntimeError:
            raise wire.ProcessError("MCU signing failed.")

        r = BufferReader(mcu.get_certificate())
        mcu_certificates = parse_cert_chain(r)

    if not utils.DISABLE_ANIMATION:
        frame_delay = sleep(60)
        for i in range(1, 20):
            spinner.report(i * 50)
            await frame_delay

        spinner.report(1000)

    if msg.stream:
        from trezor.enums import AuthenticityProofType
        from trezor.messages import (
            AuthenticityProofChunk,
            AuthenticityProofSizes,
            GetAuthenticityProofChunk,
        )
        from trezor.wire import DataError
        from trezor.wire.context import call

        def _cert_sizes(certificates: list[AnyBytes] | None) -> list[int] | None:
            if certificates is None:
                return None
            return [len(cert) for cert in certificates]

        def _sig_size(signature: AnyBytes | None) -> int | None:
            return len(signature) if signature is not None else None

        req = await call(
            AuthenticityProofSizes(
                optiga_certificates=_cert_sizes(optiga_certificates),
                tropic_certificates=_cert_sizes(tropic_certificates),
                mcu_certificates=_cert_sizes(mcu_certificates),
                optiga_signature=len(optiga_signature),
                tropic_signature=_sig_size(tropic_signature),
                mcu_signature=_sig_size(mcu_signature),
            ),
            GetAuthenticityProofChunk,
        )

        all_certificates: dict[AuthenticityProofType, list[AnyBytes] | None] = {
            AuthenticityProofType.OPTIGA: optiga_certificates,
            AuthenticityProofType.TROPIC: tropic_certificates,
            AuthenticityProofType.MCU: mcu_certificates,
        }
        all_signatures: dict[AuthenticityProofType, AnyBytes | None] = {
            AuthenticityProofType.OPTIGA: optiga_signature,
            AuthenticityProofType.TROPIC: tropic_signature,
            AuthenticityProofType.MCU: mcu_signature,
        }

        while req.proof_type is not None:

            if req.index is None:
                blob = all_signatures[req.proof_type]
                if blob is None:
                    raise DataError("No signature")
            else:
                certificates = all_certificates[req.proof_type] or []
                if req.index >= len(certificates):
                    raise DataError("No certificate")
                blob = certificates[req.index]

            blob = memoryview(blob)
            blob_len = len(blob)
            # `req.offset` and `req.size` cannot be negative (defined as `uint32`)
            offset = req.offset
            end = offset + req.size
            if offset > blob_len or end > blob_len:
                raise DataError("Invalid chunk range")
            chunk = blob[offset:end]

            resp = AuthenticityProofChunk(chunk=chunk)
            req = await call(resp, GetAuthenticityProofChunk)

        return Success()

    # support non-chunked response for backwards compatibility
    return AuthenticityProof(
        optiga_certificates=optiga_certificates,
        optiga_signature=optiga_signature,
        tropic_certificates=tropic_certificates,
        tropic_signature=tropic_signature,
        mcu_certificates=mcu_certificates,
        mcu_signature=mcu_signature,
    )
