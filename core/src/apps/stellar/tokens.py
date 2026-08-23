from typing import TYPE_CHECKING

from trezor import strings
from trezor.crypto.hashlib import sha256
from trezor.wire import DataError

from .consts import AMOUNT_DECIMALS
from .helpers import STRKEY_CONTRACT, encode_strkey
from .writers import write_asset, write_bytes_fixed, write_uint32

if TYPE_CHECKING:
    from buffer_types import AnyBytes

    from trezor.messages import StellarAsset, StellarInvokeContractArgs


class StellarToken:
    """Identity of the token an amount is denominated in.

    Only a token backed by a classic asset has an issuer; one that exists purely
    as a SEP-41 contract does not. The contract being invoked is not part of the
    identity -- it is a property of the invocation and is passed alongside.
    """

    def __init__(self, symbol: str, decimals: int, issuer: str | None) -> None:
        self.symbol = symbol
        self.decimals = decimals
        self.issuer = issuer

    @classmethod
    def from_asset(cls, asset: StellarAsset) -> "StellarToken":
        """Describe a classic asset."""
        from trezor.enums import StellarAssetType
        from trezor.wire import DataError

        if asset.type == StellarAssetType.NATIVE:
            # A native asset has neither a code nor an issuer, and `write_asset`
            # leaves both out of the SAC address preimage. They must be ignored
            # here as well, or a host could relabel XLM as an asset of its choice.
            return NATIVE_TOKEN
        if asset.code is None or asset.issuer is None:
            raise DataError("Stellar: invalid asset definition")
        return cls(asset.code, AMOUNT_DECIMALS, asset.issuer)

    def format(self, amount: int) -> str:
        """Format an amount with this token's precision and symbol."""
        return strings.format_amount(amount, self.decimals) + " " + self.symbol


# XLM, the native asset.
NATIVE_TOKEN = StellarToken("XLM", AMOUNT_DECIMALS, None)


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
) -> StellarToken | None:
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
    return StellarToken.from_asset(asset)
