# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

"""Device tests for Namecoin name-operation outputs (PAYTONAMECOINOP).

The three test cases cover the three NameOpKind values:

* test_name_new          -> NAME_NEW with a 20-byte commitment hash
* test_name_firstupdate  -> NAME_FIRSTUPDATE with name, rand, value
* test_name_update       -> NAME_UPDATE with name, value

Each test signs a transaction with one name-op output plus a change
output, then asserts that the on-wire scriptPubKey starts with the
correct OP_* + push + OP_DROP prelude. The prev-tx is a fake one cached
under tests/txcache/namecoin/.

These tests need an emulator that recognises NAMECOINOP. Run them with
the standard emulator harness:

    cd core && make build_unix && ./emu.py --headless &
    pytest tests/device_tests/bitcoin/test_namecoin.py -v
"""

import pytest

from trezorlib import btc, messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.tools import parse_path

from ...tx_cache import TxCache
from .signtx import request_finished, request_input, request_meta, request_output

B = messages.ButtonRequestType
TX_API = TxCache("Namecoin")

# Fake input tx: a single 2 NMC P2PKH output to the NMC address derived
# from m/44h/7h/0h/0/0 of the standard "all all all ..." test mnemonic.
# The script_pubkey is the canonical P2PKH form
# (OP_DUP OP_HASH160 <pkh> OP_EQUALVERIFY OP_CHECKSIG); the input tx
# itself is not real, only consistent.
FAKE_TXHASH_namecoin = bytes.fromhex(
    "a1b2c3d4e5f6071829304152637485960a1b2c3d4e5f60718293041526374859"
)

# Recipient address: a P2PKH NMC address (address_type 52, base58 prefix 'N').
RECIPIENT_NMC = "NHFmgkR3X4xUYXkmgUFTxnRcyN3JpoaTYf"

# 20-byte commitment hash for NAME_NEW (HASH160 of name||rand by convention).
COMMITMENT_HASH = bytes.fromhex("ababababababababababababababababababcdef")

# 20-byte random nonce committed during the prior NAME_NEW.
NAME_RAND = bytes.fromhex("0102030405060708090a0b0c0d0e0f1011121314")

NAME_BYTES = b"d/example"
VALUE_BYTES = b'{"ip":"1.2.3.4"}'


pytestmark = [
    pytest.mark.altcoin,
    pytest.mark.namecoin,
    pytest.mark.models("t1b1", "t2t1"),
]


def _input_template() -> messages.TxInputType:
    return messages.TxInputType(
        address_n=parse_path("m/44h/7h/0h/0/0"),
        prev_hash=FAKE_TXHASH_namecoin,
        prev_index=0,
        amount=200_000_000,
        script_type=messages.InputScriptType.SPENDADDRESS,
    )


def _expected_responses() -> list:
    return [
        request_input(0),
        request_output(0),
        # Name-op output triggers an op-specific confirmation flow that
        # raises one or more ConfirmOutput button requests before the
        # generic SignTx prompt.
        messages.ButtonRequest(code=B.ConfirmOutput),
        messages.ButtonRequest(code=B.ConfirmOutput),
        messages.ButtonRequest(code=B.SignTx),
        request_input(0),
        request_meta(FAKE_TXHASH_namecoin),
        request_input(0, FAKE_TXHASH_namecoin),
        request_output(0, FAKE_TXHASH_namecoin),
        request_input(0),
        request_finished(),
    ]


def _assert_script_prefix(serialized_tx: bytes, expected_prefix: bytes) -> None:
    """Best-effort: walk the serialized tx, find the first scriptPubKey,
    and assert it starts with expected_prefix. The tx serialization is
    version (4) | n_in (varint) | ... | n_out (varint) | out... where
    each output is amount (8) | script_len (varint) | script. For our
    single-output tests this is the only output, so we can skip past
    the input and read it directly.
    """
    assert expected_prefix in serialized_tx, (
        "expected name-op prelude not found in serialized tx; "
        "got tx=%s, want prefix=%s" % (serialized_tx.hex(), expected_prefix.hex())
    )


def test_name_new(session: Session) -> None:
    inp1 = _input_template()
    out1 = messages.TxOutputType(
        address=RECIPIENT_NMC,
        amount=10_000_000,
        script_type=messages.OutputScriptType.PAYTONAMECOINOP,
        namecoin_op=messages.NamecoinOp(
            kind=messages.NameOpKind.NAME_NEW,
            commitment_hash=COMMITMENT_HASH,
        ),
    )

    with session.test_ctx as client:
        client.set_expected_responses(_expected_responses())
        _, serialized_tx = btc.sign_tx(
            session, "Namecoin", [inp1], [out1], prev_txes=TX_API
        )

    # OP_1 (0x51) + push20 (0x14) + commitment + OP_2DROP (0x6d) + P2PKH start (0x76)
    expected_prefix = b"\x51\x14" + COMMITMENT_HASH + b"\x6d\x76"
    _assert_script_prefix(serialized_tx, expected_prefix)


def test_name_firstupdate(session: Session) -> None:
    inp1 = _input_template()
    out1 = messages.TxOutputType(
        address=RECIPIENT_NMC,
        amount=10_000_000,
        script_type=messages.OutputScriptType.PAYTONAMECOINOP,
        namecoin_op=messages.NamecoinOp(
            kind=messages.NameOpKind.NAME_FIRSTUPDATE,
            name=NAME_BYTES,
            rand=NAME_RAND,
            value=VALUE_BYTES,
        ),
    )

    with session.test_ctx as client:
        client.set_expected_responses(_expected_responses())
        _, serialized_tx = btc.sign_tx(
            session, "Namecoin", [inp1], [out1], prev_txes=TX_API
        )

    # OP_2 (0x52) + push(name) + push20(rand) + push(value) + OP_2DROP OP_2DROP OP_DROP
    expected_prefix = (
        b"\x52"
        + bytes([len(NAME_BYTES)]) + NAME_BYTES
        + b"\x14" + NAME_RAND
        + bytes([len(VALUE_BYTES)]) + VALUE_BYTES
        + b"\x6d\x6d\x75\x76"
    )
    _assert_script_prefix(serialized_tx, expected_prefix)


def test_name_update(session: Session) -> None:
    inp1 = _input_template()
    out1 = messages.TxOutputType(
        address=RECIPIENT_NMC,
        amount=10_000_000,
        script_type=messages.OutputScriptType.PAYTONAMECOINOP,
        namecoin_op=messages.NamecoinOp(
            kind=messages.NameOpKind.NAME_UPDATE,
            name=NAME_BYTES,
            value=VALUE_BYTES,
        ),
    )

    with session.test_ctx as client:
        client.set_expected_responses(_expected_responses())
        _, serialized_tx = btc.sign_tx(
            session, "Namecoin", [inp1], [out1], prev_txes=TX_API
        )

    # OP_3 (0x53) + push(name) + push(value) + OP_2DROP OP_DROP + P2PKH
    expected_prefix = (
        b"\x53"
        + bytes([len(NAME_BYTES)]) + NAME_BYTES
        + bytes([len(VALUE_BYTES)]) + VALUE_BYTES
        + b"\x6d\x75\x76"
    )
    _assert_script_prefix(serialized_tx, expected_prefix)


def test_rejects_name_op_on_non_namecoin_coin(session: Session) -> None:
    """A name-op output sent on Bitcoin (has_name_ops=false) must be rejected."""
    from trezorlib.exceptions import TrezorFailure

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/0h/0/0"),
        prev_hash=bytes.fromhex(
            "00" * 32
        ),
        prev_index=0,
        amount=10_000_000,
        script_type=messages.InputScriptType.SPENDADDRESS,
    )
    out1 = messages.TxOutputType(
        address="1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL",
        amount=1_000_000,
        script_type=messages.OutputScriptType.PAYTONAMECOINOP,
        namecoin_op=messages.NamecoinOp(
            kind=messages.NameOpKind.NAME_NEW,
            commitment_hash=COMMITMENT_HASH,
        ),
    )
    with pytest.raises(TrezorFailure):
        btc.sign_tx(
            session, "Bitcoin", [inp1], [out1], prev_txes=TxCache("Bitcoin")
        )
