from typing import TYPE_CHECKING

from trezor.enums import ButtonRequestType
from trezor.messages import CosiCommitment, CosiSign, CosiSignature
from trezor.wire import DataError

from apps.common.paths import PathSchema, unharden

if TYPE_CHECKING:
    from trezor.messages import CosiCommit

# This module implements the cosigner part of the CoSi collective signatures
# as described in https://dedis.cs.yale.edu/dissent/papers/witness.pdf


SCHEMA_SLIP18 = PathSchema.parse("m/10018'/address_index'/*'", slip44_id=())
# SLIP-26: m/10026'/model'/type'/rotation_index'
# - `model`: typically ASCII string T1B1 etc. parsed as little-endian number,
#            but can also be 0 or other values. Maximum allowed value is 0x7F7F7F7F,
#            the maximum 4-byte ASCII string.
# - `type`: 0 = bootloader, 1 = vendorheader, 2 = firmware, 3 = definitions, 4 = reserved
# - `rotation_index`: a fixed 0' for now
SCHEMA_SLIP26 = PathSchema.parse("m/10026'/[0-2139062143]'/[0-4]'/0'", slip44_id=())


def _decode_path(address_n: list[int]) -> str | None:
    signing_types = {
        0: "bootloader",
        1: "vendor header",
        2: "firmware",
    }

    if len(address_n) == 2 and SCHEMA_SLIP18.match(address_n):
        signing_type = signing_types.get(unharden(address_n[1]))
        if signing_type is None:
            return None
        return f"T2T1 {signing_type} (old-style)"

    if SCHEMA_SLIP26.match(address_n):
        model = unharden(address_n[1])
        signing_type = unharden(address_n[2])
        if model == 0 and signing_type == 3:
            return "External definitions"

        model_bytes = model.to_bytes(4, "little")
        signing_type_str = signing_types.get(signing_type)
        if (
            signing_type_str is not None
            and len(model_bytes) == 4
            and all(0x20 <= b <= 0x7E for b in model_bytes)
        ):
            return f"{model_bytes.decode()} {signing_type_str}"

    return None


async def cosi_commit(msg: CosiCommit) -> CosiSignature:
    import storage.cache as storage_cache
    from trezor.crypto import cosi
    from trezor.crypto.curve import ed25519
    from trezor.ui.layouts import confirm_blob, confirm_text
    from trezor.wire.context import call

    from apps.common import paths
    from apps.common.keychain import get_keychain

    keychain = await get_keychain("ed25519", [SCHEMA_SLIP18, SCHEMA_SLIP26])
    await paths.validate_path(keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    seckey = node.private_key()
    pubkey = ed25519.publickey(seckey)

    if not storage_cache.is_set(storage_cache.APP_MISC_COSI_COMMITMENT):
        nonce, commitment = cosi.commit()
        storage_cache.set(storage_cache.APP_MISC_COSI_NONCE, nonce)
        storage_cache.set(storage_cache.APP_MISC_COSI_COMMITMENT, commitment)
    commitment = storage_cache.get(storage_cache.APP_MISC_COSI_COMMITMENT)
    if commitment is None:
        raise RuntimeError

    sign_msg = await call(
        CosiCommitment(commitment=commitment, pubkey=pubkey), CosiSign
    )

    if sign_msg.address_n != msg.address_n:
        raise DataError("Mismatched address_n")

    path_description = _decode_path(sign_msg.address_n)
    await confirm_text(
        "cosi_confirm_key",
        "COSI KEYS",
        paths.address_n_to_str(sign_msg.address_n),
        path_description,
    )
    await confirm_blob(
        "cosi_sign",
        "COSI DATA",
        sign_msg.data,
        br_code=ButtonRequestType.ProtectCall,
    )

    # clear nonce from cache
    nonce = storage_cache.get(storage_cache.APP_MISC_COSI_NONCE)
    storage_cache.delete(storage_cache.APP_MISC_COSI_COMMITMENT)
    storage_cache.delete(storage_cache.APP_MISC_COSI_NONCE)
    if nonce is None:
        raise RuntimeError

    signature = cosi.sign(
        seckey, sign_msg.data, nonce, sign_msg.global_commitment, sign_msg.global_pubkey
    )
    return CosiSignature(signature=signature)
