import os
from decimal import Decimal
from typing import Sequence, Tuple

import bitcoin
import requests
from bitcoin.core import COutPoint, CScript, CTransaction, CTxIn, CTxOut
from bitcoin.wallet import CBitcoinAddress

from trezorlib import messages

T = messages.RequestType


def request_input(n: int, tx_hash: bytes = None) -> messages.TxRequest:
    return messages.TxRequest(
        request_type=T.TXINPUT,
        details=messages.TxRequestDetailsType(request_index=n, tx_hash=tx_hash),
    )


def request_output(n: int, tx_hash: bytes = None) -> messages.TxRequest:
    return messages.TxRequest(
        request_type=T.TXOUTPUT,
        details=messages.TxRequestDetailsType(request_index=n, tx_hash=tx_hash),
    )


def request_orig_input(n: int, tx_hash: bytes) -> messages.TxRequest:
    return messages.TxRequest(
        request_type=T.TXORIGINPUT,
        details=messages.TxRequestDetailsType(request_index=n, tx_hash=tx_hash),
    )


def request_orig_output(n: int, tx_hash: bytes) -> messages.TxRequest:
    return messages.TxRequest(
        request_type=T.TXORIGOUTPUT,
        details=messages.TxRequestDetailsType(request_index=n, tx_hash=tx_hash),
    )


def request_payment_req(n):
    return messages.TxRequest(
        request_type=T.TXPAYMENTREQ,
        details=messages.TxRequestDetailsType(request_index=n),
    )


def request_meta(tx_hash: bytes) -> messages.TxRequest:
    return messages.TxRequest(
        request_type=T.TXMETA,
        details=messages.TxRequestDetailsType(tx_hash=tx_hash),
    )


def request_finished() -> messages.TxRequest:
    return messages.TxRequest(request_type=T.TXFINISHED)


def request_extra_data(ofs: int, len: int, tx_hash: bytes) -> messages.TxRequest:
    return messages.TxRequest(
        request_type=T.TXEXTRADATA,
        details=messages.TxRequestDetailsType(
            tx_hash=tx_hash, extra_data_offset=ofs, extra_data_len=len
        ),
    )


def assert_tx_matches(serialized_tx: bytes, hash_link: str, tx_hex: str = None) -> None:
    """Verifies if a transaction is correctly formed."""
    tx_id = hash_link.split("/")[-1]

    parsed_tx = CTransaction.deserialize(serialized_tx)
    assert tx_id == parsed_tx.GetTxid()[::-1].hex()
    if tx_hex:
        assert serialized_tx.hex() == tx_hex

    # TODO: we could probably do better than os.environ, this was the easiest solution
    # (we could create a pytest option (and use config.getoption("check-on-chain")),
    # but then each test would need to have access to config via function argument)
    if int(os.environ.get("CHECK_ON_CHAIN", 0)):

        def get_tx_hex(hash_link: str) -> str:
            tx_data = requests.get(
                hash_link, headers={"User-Agent": "BTC transactions test"}
            ).json(parse_float=Decimal)

            return tx_data["hex"]

        assert serialized_tx.hex() == get_tx_hex(hash_link)


def forge_prevtx(
    vouts: Sequence[Tuple[str, int]], network: str = "mainnet"
) -> Tuple[bytes, messages.TransactionType]:
    """
    Forge a transaction with the given vouts.
    """
    bitcoin.SelectParams(network)
    input = messages.TxInputType(
        prev_hash=b"\x00" * 32,
        prev_index=0xFFFFFFFF,
        script_sig=b"\x00",
        sequence=0xFFFFFFFF,
    )
    outputs = [
        messages.TxOutputBinType(
            amount=amount,
            script_pubkey=bytes(CBitcoinAddress(address).to_scriptPubKey()),
        )
        for address, amount in vouts
    ]
    tx = messages.TransactionType(
        version=1,
        inputs=[input],
        bin_outputs=outputs,
        lock_time=0,
    )

    cin = CTxIn(
        COutPoint(input.prev_hash, input.prev_index),
        CScript(input.script_sig),
        input.sequence,
    )
    couts = [
        CTxOut(output.amount, CScript(output.script_pubkey))
        for output in tx.bin_outputs
    ]
    txhash = CTransaction([cin], couts, tx.lock_time, tx.version).GetTxid()[::-1]

    bitcoin.SelectParams("mainnet")

    return txhash, tx
