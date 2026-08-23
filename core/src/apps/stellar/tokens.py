from typing import TYPE_CHECKING

from trezor.crypto.hashlib import sha256
from trezor.wire import DataError

from .helpers import STRKEY_CONTRACT, encode_strkey
from .writers import write_asset, write_bytes_fixed, write_uint32

if TYPE_CHECKING:
    from buffer_types import AnyBytes

    from trezor.messages import StellarAsset, StellarInvokeContractArgs


def sac_address_from_asset(network_id: AnyBytes, asset: StellarAsset) -> str:
    """Derive the address of the Stellar Asset Contract (SAC) of an asset (C...).

    See https://github.com/stellar/stellar-protocol/blob/master/core/cap-0046-02.md#contract-identifier-preimage-type
    """
    w = bytearray()
    write_uint32(w, 8)  # ENVELOPE_TYPE_CONTRACT_ID
    write_bytes_fixed(w, network_id, 32)
    write_uint32(w, 1)  # CONTRACT_ID_PREIMAGE_FROM_ASSET
    write_asset(w, asset)
    return encode_strkey(STRKEY_CONTRACT, sha256(w).digest())


def resolve_sep41_token(
    args: StellarInvokeContractArgs, network_id: AnyBytes
) -> StellarAsset | None:
    """Resolve token metadata for the dedicated SEP-41 UI.

    Currently, the host may identify a Stellar Asset Contract by supplying its
    underlying asset. The hint is used only when its derived SAC address matches
    the invoked contract; an absent, mismatched, or malformed hint leaves the
    invocation to the generic contract UI.
    """
    asset = args.asset_hint
    if asset is None:
        return None
    try:
        sac_address = sac_address_from_asset(network_id, asset)
    except DataError:
        return None
    if sac_address != args.contract_address:
        return None
    return asset
