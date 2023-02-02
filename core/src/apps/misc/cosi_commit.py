from typing import TYPE_CHECKING

from trezor.enums import ButtonRequestType
from trezor.messages import CosiCommitment, CosiSign, CosiSignature
from trezor.wire import DataError

from apps.common.paths import PathSchema, unharden

if TYPE_CHECKING:
    from trezor.messages import CosiCommit
    from trezor.wire import Context

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


async def cosi_commit(ctx: Context, msg: CosiCommit) -> CosiSignature:
    import storage.cache as storage_cache
    from trezor.crypto.curve import ed25519
    from trezor.ui.layouts import confirm_blob
    from apps.common import paths
    from apps.common.keychain import get_keychain

    keychain = await get_keychain(ctx, "ed25519", [SCHEMA_SLIP18, SCHEMA_SLIP26])
    await paths.validate_path(ctx, keychain, msg.address_n)

    node = keychain.derive(msg.address_n)
    seckey = node.private_key()
    pubkey = ed25519.publickey(seckey)

    if not storage_cache.is_set(storage_cache.APP_MISC_COSI_COMMITMENT):
        nonce, commitment = ed25519.cosi_commit()
        storage_cache.set(storage_cache.APP_MISC_COSI_NONCE, nonce)
        storage_cache.set(storage_cache.APP_MISC_COSI_COMMITMENT, commitment)
    commitment = storage_cache.get(storage_cache.APP_MISC_COSI_COMMITMENT)
    if commitment is None:
        raise RuntimeError

    sign_msg = await ctx.call(
        CosiCommitment(commitment=commitment, pubkey=pubkey), CosiSign
    )

    if sign_msg.address_n != msg.address_n:
        raise DataError("Mismatched address_n")

    title = "CoSi sign message"
    if SCHEMA_SLIP18.match(sign_msg.address_n):
        index = unharden(msg.address_n[1])
        title = f"CoSi sign index {index}"

    await confirm_blob(
        ctx, "cosi_sign", title, sign_msg.data, br_code=ButtonRequestType.ProtectCall
    )

    # clear nonce from cache
    nonce = storage_cache.get(storage_cache.APP_MISC_COSI_NONCE)
    storage_cache.delete(storage_cache.APP_MISC_COSI_COMMITMENT)
    storage_cache.delete(storage_cache.APP_MISC_COSI_NONCE)
    if nonce is None:
        raise RuntimeError

    signature = ed25519.cosi_sign(
        seckey, sign_msg.data, nonce, sign_msg.global_commitment, sign_msg.global_pubkey
    )
    return CosiSignature(signature=signature)
