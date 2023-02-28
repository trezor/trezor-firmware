from copy import copy
from hashlib import sha256
from io import BytesIO

import pytest

from trezorlib import btc, messages, tools
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure

from .signtx import forge_prevtx

# address at seed "all all all..." path m/44h/0h/0h/0/0
INPUT_ADDRESS = "1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL"
PREV_HASH, PREV_TX = forge_prevtx([(INPUT_ADDRESS, 100_000_000)])
PREV_TXES = {PREV_HASH: PREV_TX}


def write_prefixed_bytes(io, data) -> None:
    assert len(data) < 253
    io.write(len(data).to_bytes(1, "little"))
    io.write(data)


def serialize_input(tx_input) -> bytes:
    """serialize for Bitcoin tx format"""
    b = BytesIO()
    if tx_input.prev_hash:
        b.write(tx_input.prev_hash[::-1])
    b.write(tx_input.prev_index.to_bytes(4, "little"))
    write_prefixed_bytes(b, tx_input.script_sig)
    b.write(tx_input.sequence.to_bytes(4, "little"))
    return b.getvalue()


def serialize_bin_output(tx_output) -> bytes:
    b = BytesIO()
    b.write(tx_output.amount.to_bytes(8, "little"))
    write_prefixed_bytes(b, tx_output.script_pubkey)
    return b.getvalue()


def serialize_tx(tx) -> bytes:
    b = BytesIO()
    b.write(tx.version.to_bytes(4, "little"))
    assert len(tx.inputs) < 253
    b.write(len(tx.inputs).to_bytes(1, "little"))
    for inp in tx.inputs:
        b.write(serialize_input(inp))
    assert len(tx.bin_outputs) < 253
    b.write(len(tx.bin_outputs).to_bytes(1, "little"))
    for outp in tx.bin_outputs:
        b.write(serialize_bin_output(outp))
    lock_time = tx.lock_time or 0
    b.write(lock_time.to_bytes(4, "little"))
    if tx.extra_data:
        b.write(tx.extra_data)
    return b.getvalue()


def hash_tx(data: bytes) -> bytes:
    return sha256(sha256(data).digest()).digest()[::-1]


def _check_error_message(value: bytes, model: str, message: str):
    # T1 has several possible errors
    if model == "1" and len(value) > 32:
        assert message.endswith("bytes overflow")
    else:
        assert message.endswith("Provided prev_hash is invalid.")


with_bad_prevhashes = pytest.mark.parametrize(
    "prev_hash", (b"", b"x", b"hello world", b"x" * 33)
)


@with_bad_prevhashes
def test_invalid_prev_hash(client: Client, prev_hash):
    inp1 = messages.TxInputType(
        address_n=tools.parse_path("m/44h/0h/0h/0/0"),
        amount=123_456_789,
        prev_hash=prev_hash,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
    )
    out1 = messages.TxOutputType(
        address="mhRx1CeVfaayqRwq5zgRQmD7W5aWBfD5mC",
        amount=12_300_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with pytest.raises(TrezorFailure) as e:
        btc.sign_tx(client, "Testnet", [inp1], [out1], prev_txes={})
    _check_error_message(prev_hash, client.features.model, e.value.message)


@with_bad_prevhashes
def test_invalid_prev_hash_attack(client: Client, prev_hash):
    # prepare input with a valid prev-hash
    inp1 = messages.TxInputType(
        address_n=tools.parse_path("m/44h/0h/0h/0/0"),
        amount=100_000_000,
        prev_hash=PREV_HASH,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
    )
    out1 = messages.TxOutputType(
        address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
        amount=100_000_000 - 10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    counter = 1

    def attack_filter(msg):
        nonlocal counter

        if not msg.tx.inputs:
            return msg

        # on first attempt, send unmodified input
        if counter > 0:
            counter -= 1
            return msg

        # on second request, send modified input
        msg.tx.inputs[0].prev_hash = prev_hash
        return msg

    with client, pytest.raises(TrezorFailure) as e:
        client.set_filter(messages.TxAck, attack_filter)
        btc.sign_tx(client, "Bitcoin", [inp1], [out1], prev_txes=PREV_TXES)

    # check that injection was performed
    assert counter == 0
    _check_error_message(prev_hash, client.features.model, e.value.message)


@with_bad_prevhashes
def test_invalid_prev_hash_in_prevtx(client: Client, prev_hash):
    prev_tx = copy(PREV_TX)

    # smoke check: replace prev_hash with all zeros, reserialize and hash, try to sign
    prev_tx.inputs[0].prev_hash = b"\x00" * 32
    tx_hash = hash_tx(serialize_tx(prev_tx))

    inp0 = messages.TxInputType(
        address_n=tools.parse_path("m/44h/0h/0h/0/0"),
        amount=100_000_000,
        prev_hash=tx_hash,
        prev_index=0,
    )
    out1 = messages.TxOutputType(
        address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
        amount=99_000_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    btc.sign_tx(client, "Bitcoin", [inp0], [out1], prev_txes={tx_hash: prev_tx})

    # attack: replace prev_hash with an invalid value
    prev_tx.inputs[0].prev_hash = prev_hash
    tx_hash = hash_tx(serialize_tx(prev_tx))
    inp0.prev_hash = tx_hash

    with pytest.raises(TrezorFailure) as e:
        btc.sign_tx(client, "Bitcoin", [inp0], [out1], prev_txes={tx_hash: prev_tx})
    _check_error_message(prev_hash, client.features.model, e.value.message)
