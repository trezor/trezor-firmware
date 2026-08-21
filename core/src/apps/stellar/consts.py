from micropython import const
from typing import TYPE_CHECKING

from trezor.enums import MessageType

if TYPE_CHECKING:
    from trezor import protobuf
    from trezor.messages import (
        StellarAccountMergeOp,
        StellarAllowTrustOp,
        StellarBumpSequenceOp,
        StellarChangeTrustOp,
        StellarClaimClaimableBalanceOp,
        StellarCreateAccountOp,
        StellarCreatePassiveSellOfferOp,
        StellarInvokeHostFunctionOp,
        StellarManageBuyOfferOp,
        StellarManageDataOp,
        StellarManageSellOfferOp,
        StellarPathPaymentStrictReceiveOp,
        StellarPathPaymentStrictSendOp,
        StellarPaymentOp,
        StellarSetOptionsOp,
    )

    StellarMessageType = (
        StellarAccountMergeOp
        | StellarAllowTrustOp
        | StellarBumpSequenceOp
        | StellarChangeTrustOp
        | StellarCreateAccountOp
        | StellarCreatePassiveSellOfferOp
        | StellarManageDataOp
        | StellarManageBuyOfferOp
        | StellarManageSellOfferOp
        | StellarPathPaymentStrictReceiveOp
        | StellarPathPaymentStrictSendOp
        | StellarPaymentOp
        | StellarSetOptionsOp
        | StellarClaimClaimableBalanceOp
        | StellarInvokeHostFunctionOp
    )


TX_TYPE = b"\x00\x00\x00\x02"

# source: https://github.com/stellar/go/blob/a1db2a6b1f/xdr/Stellar-transaction.x#L35
# Inflation not supported see https://github.com/trezor/trezor-core/issues/202#issuecomment-393342089
op_codes: dict[int, int] = {
    MessageType.StellarAccountMergeOp: 8,
    MessageType.StellarAllowTrustOp: 7,
    MessageType.StellarBumpSequenceOp: 11,
    MessageType.StellarChangeTrustOp: 6,
    MessageType.StellarCreateAccountOp: 0,
    MessageType.StellarCreatePassiveSellOfferOp: 4,
    MessageType.StellarManageDataOp: 10,
    MessageType.StellarManageBuyOfferOp: 12,
    MessageType.StellarManageSellOfferOp: 3,
    MessageType.StellarPathPaymentStrictReceiveOp: 2,
    MessageType.StellarPathPaymentStrictSendOp: 13,
    MessageType.StellarPaymentOp: 1,
    MessageType.StellarSetOptionsOp: 5,
    MessageType.StellarClaimClaimableBalanceOp: 15,
    MessageType.StellarInvokeHostFunctionOp: 24,
}


# https://www.stellar.org/developers/guides/concepts/accounts.html#balance
# https://github.com/stellar/go/blob/3d2c1defe73dbfed00146ebe0e8d7e07ce4bb1b6/amount/main.go#L23
AMOUNT_DECIMALS = const(7)

# https://github.com/stellar/go/blob/master/network/main.go
NETWORK_PASSPHRASE_PUBLIC = "Public Global Stellar Network ; September 2015"
NETWORK_PASSPHRASE_TESTNET = "Test SDF Network ; September 2015"

# Trusted SEP-41 token contracts of the public network that are not Stellar
# Asset Contracts, and so can never be recognized from a host-supplied asset
# hint. Keyed by contract address, mapping to `(symbol, decimals)` as the
# contract itself reports them.
PUBLIC_TOKENS: dict[str, tuple[str, int]] = {
    # SolvBTC
    # https://stellar.expert/explorer/public/contract/CBIJBDNZNF4X35BJ4FFZWCDBSCKOP5NB4PLG4SNENRMLAPYG4P5FM6VN
    "CBIJBDNZNF4X35BJ4FFZWCDBSCKOP5NB4PLG4SNENRMLAPYG4P5FM6VN": ("SolvBTC", 8),
    # xSolvBTC
    # https://stellar.expert/explorer/public/contract/CAUP7NFABXE5TJRL3FKTPMWRLC7IAXYDCTHQRFSCLR5TMGKHOOQO772J
    "CAUP7NFABXE5TJRL3FKTPMWRLC7IAXYDCTHQRFSCLR5TMGKHOOQO772J": ("xSolvBTC", 8),
}

# https://www.stellar.org/developers/guides/concepts/accounts.html#flags
FLAG_AUTH_REQUIRED = const(1)
FLAG_AUTH_REVOCABLE = const(2)
FLAG_AUTH_IMMUTABLE = const(4)
FLAGS_MAX_SIZE = const(7)

# SCSymbol is a string with a maximum length of 32
# https://github.com/stellar/stellar-xdr/blob/v26.0/Stellar-contract.x#L211
SCSYMBOL_MAX_SIZE = const(32)


def get_op_code(msg: protobuf.MessageType) -> int:
    wire = msg.MESSAGE_WIRE_TYPE
    if wire not in op_codes:
        raise ValueError("Stellar: op code unknown")
    assert isinstance(wire, int)
    return op_codes[wire]
