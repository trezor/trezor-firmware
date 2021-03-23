from hashlib import sha256
from io import BytesIO

import pytest

from trezorlib import btc, messages, tools
from trezorlib.exceptions import TrezorFailure

from ..tx_cache import TxCache

TXHASH_157041 = bytes.fromhex(
    "1570416eb4302cf52979afd5e6909e37d8fdd874301f7cc87e547e509cb1caa6"
)


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
    if model != "1":
        if value is None:
            assert message == "Failed to decode message: Missing"
        else:
            assert message == "Provided prev_hash is invalid."
        return

    # T1 has several possible errors
    if value is None:
        assert message.endswith("missing required field")
    elif len(value) > 32:
        assert message.endswith("bytes overflow")
    else:
        assert message.endswith("Encountered invalid prevhash")


@pytest.mark.parametrize("prev_hash", (None, b"", b"x", b"hello world", b"x" * 33))
def test_invalid_prev_hash(client, prev_hash):
    inp1 = messages.TxInputType(
        address_n=tools.parse_path("m/44h/0h/0h/0/0"),
        amount=123456789,
        prev_hash=prev_hash,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
    )
    out1 = messages.TxOutputType(
        address="mhRx1CeVfaayqRwq5zgRQmD7W5aWBfD5mC",
        amount=12300000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with pytest.raises(TrezorFailure) as e:
        btc.sign_tx(client, "Testnet", [inp1], [out1], prev_txes={})
    _check_error_message(prev_hash, client.features.model, e.value.message)


@pytest.mark.parametrize("prev_hash", (None, b"", b"x", b"hello world", b"x" * 33))
def test_invalid_prev_hash_attack(client, prev_hash):
    # prepare input with a valid prev-hash
    inp1 = messages.TxInputType(
        address_n=tools.parse_path("m/44h/0h/0h/0/0"),
        amount=100000000,
        prev_hash=TXHASH_157041,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
    )
    out1 = messages.TxOutputType(
        address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
        amount=100000000 - 10000,
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
        btc.sign_tx(client, "Bitcoin", [inp1], [out1], prev_txes=TxCache("Bitcoin"))

    # check that injection was performed
    assert counter == 0
    _check_error_message(prev_hash, client.features.model, e.value.message)


@pytest.mark.parametrize("prev_hash", (None, b"", b"x", b"hello world", b"x" * 33))
def test_invalid_prev_hash_in_prevtx(client, prev_hash):
    cache = TxCache("Bitcoin")
    prev_tx = cache[TXHASH_157041]

    # smoke check: replace prev_hash with all zeros, reserialize and hash, try to sign
    prev_tx.inputs[0].prev_hash = b"\x00" * 32
    tx_hash = hash_tx(serialize_tx(prev_tx))

    inp0 = messages.TxInputType(
        address_n=tools.parse_path("m/44h/0h/0h/0/0"),
        amount=100000000,
        prev_hash=tx_hash,
        prev_index=0,
    )
    out1 = messages.TxOutputType(
        address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
        amount=99000000,
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
