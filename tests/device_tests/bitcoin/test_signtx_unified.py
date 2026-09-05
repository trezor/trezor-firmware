# This file is part of the Trezor project.
#
# Copyright (C) 2012-2026 SatoshiLabs and contributors
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

"""Signing with the unified opt-in signature hash (Bitcoin Knots).

Every signature the device produces here is verified against a digest computed
by the reference implementation in unified_sighash.py, which is checked against
the cross-implementation vectors first.
"""

import importlib.util
from pathlib import Path

import ecdsa
import pytest

from trezorlib import btc, messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import hash_160, parse_path

from ...bip32 import deserialize
from ...common import is_core
from ...tx_cache import TxCache
from .signtx import request_finished, request_input, request_meta, request_output
from .unified_sighash import (
    SCRIPT_TYPE_BARE,
    SCRIPT_TYPE_TAPROOT,
    SCRIPT_TYPE_WITNESS_V0,
    parse_tx,
    unified_sighash,
)

B = messages.ButtonRequestType
TX_CACHE_MAINNET = TxCache("Bitcoin")
TX_CACHE_TESTNET = TxCache("Testnet")

# SIGHASH_ALL | SIGHASH_UNIFIED, the only unified hash type the firmware signs.
HASH_TYPE = 0x21

TXHASH_0dac36 = bytes.fromhex(
    "0dac366fd8a67b2a89fbb0d31086e7acded7a5bbf9ef9daa935bc873229ef5b5"
)
TXHASH_50f6f1 = bytes.fromhex(
    "50f6f1209ca92d7359564be803cb2c932cde7d370f7cee50fd1fad6790f6206d"
)
TXHASH_beafc7 = bytes.fromhex(
    "beafc7cbd873d06dbee88a7002768ad5864228639db514c81cfb29f108bb1e7a"
)
TXHASH_ac4ca0 = bytes.fromhex(
    "ac4ca0e7827a1228f44449cb57b4b9a809a667ca044dc43bb124627fed4bc10a"
)
TXHASH_65047a = bytes.fromhex(
    "65047a2b107d6301d72d4a1e49e7aea9cf06903fdc4ae74a4a9bba9bc1a414d2"
)
TXHASH_6b07c1 = bytes.fromhex(
    "6b07c1321b52d9c85743f9695e13eb431b41708cdf4e1585258d51208e5b93fc"
)
TXHASH_b9abfa = bytes.fromhex(
    "b9abfa0d4a28f6f25e1f6c0f974bfc3f7c5a44c4d381b1796e3fbeef51b560a6"
)
TXHASH_d159fd = bytes.fromhex(
    "d159fd2fcb5854a7c8b275d598765a446f1e2ff510bf077545a404a0c9db65f7"
)
TXHASH_ec5194 = bytes.fromhex(
    "ec519494bea3746bd5fbdd7a15dac5049a873fa674c67e596d46505b9b835425"
)


def _load_vectors():
    path = Path(__file__).resolve().parents[3] / "core/tests/unified_sighash_vectors.py"
    spec = importlib.util.spec_from_file_location("unified_sighash_vectors", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.VECTORS


def parse_signed_tx(raw: bytes):
    """Deserialize a signed transaction, witness included."""
    o = 0

    def take(n):
        nonlocal o
        o += n
        return raw[o - n : o]

    def cs():
        nonlocal o
        first = raw[o]
        o += 1
        if first < 0xFD:
            return first
        return int.from_bytes(take({0xFD: 2, 0xFE: 4, 0xFF: 8}[first]), "little")

    version = int.from_bytes(take(4), "little")
    segwit = raw[o] == 0x00
    if segwit:
        assert take(2) == b"\x00\x01"
    vin, script_sigs = [], []
    for _ in range(cs()):
        txid_le = take(32)
        n = int.from_bytes(take(4), "little")
        script_sigs.append(take(cs()))
        vin.append((txid_le, n, int.from_bytes(take(4), "little")))
    vout = []
    for _ in range(cs()):
        amount = int.from_bytes(take(8), "little")
        vout.append((amount, take(cs())))
    if segwit:
        witnesses = [[take(cs()) for _ in range(cs())] for _ in vin]
    else:
        witnesses = [[] for _ in vin]
    lock_time = int.from_bytes(take(4), "little")
    assert o == len(raw)
    return version, vin, vout, lock_time, script_sigs, witnesses


def spent_outputs(inputs, tx_cache):
    out = []
    for txi in inputs:
        prev = tx_cache[txi.prev_hash].bin_outputs[txi.prev_index]
        assert prev.amount == txi.amount
        out.append((prev.amount, prev.script_pubkey))
    return out


def p2pkh_script(pubkey: bytes) -> bytes:
    return b"\x76\xa9\x14" + hash_160(pubkey) + b"\x88\xac"


def script_pushes(script: bytes) -> list:
    """Split a scriptSig into the items it pushes, OP_0 included as empty."""
    items, o = [], 0
    while o < len(script):
        op = script[o]
        o += 1
        if op == 0x00:  # OP_0, the placeholder for a missing signature
            items.append(b"")
        elif op <= 0x4B:
            items.append(script[o : o + op])
            o += op
        elif op == 0x4C:
            length = script[o]
            o += 1
            items.append(script[o : o + length])
            o += length
        else:
            raise ValueError(f"unexpected opcode {op:#x} in scriptSig")
    return items


def verify_ecdsa(pubkey: bytes, signature: bytes, digest: bytes) -> None:
    key = ecdsa.VerifyingKey.from_string(pubkey, curve=ecdsa.SECP256k1)
    key.verify_digest(signature, digest, sigdecode=ecdsa.util.sigdecode_der)


def digest_for(serialized_tx, inputs, in_idx, script_type, script_code, tx_cache):
    version, vin, vout, lock_time, _, _ = parse_signed_tx(serialized_tx)
    return unified_sighash(
        version,
        lock_time,
        vin,
        vout,
        spent_outputs(inputs, tx_cache),
        in_idx,
        script_type,
        HASH_TYPE,
        script_code=script_code,
    )


def check_ecdsa_input(
    serialized_tx, inputs, in_idx, script_type, script_code, tx_cache, pubkey
):
    """Recompute the unified digest for one input and verify what the device signed."""
    _, _, _, _, script_sigs, witnesses = parse_signed_tx(serialized_tx)
    digest = digest_for(
        serialized_tx, inputs, in_idx, script_type, script_code, tx_cache
    )

    # P2WPKH witness is [signature, pubkey]; multisig is ['', sig..., script].
    # A P2PKH scriptSig pushes the signature then the pubkey, a P2SH multisig
    # one pushes OP_0, the signatures and the redeemScript.
    items = witnesses[in_idx] or script_pushes(script_sigs[in_idx])
    signature = next(i for i in items if i and i[0] == 0x30)

    assert signature[-1] == HASH_TYPE, hex(signature[-1])
    verify_ecdsa(pubkey, signature[:-1], digest)


def test_reference_matches_vectors():
    """Anchor the reference implementation before anything is verified with it."""
    run = skipped = 0
    for (
        script_code,
        raw_tx,
        in_idx,
        hash_type,
        script_type,
        spent,
        expected,
    ) in _load_vectors():
        if script_type == 3:  # tapscript, the vectors carry no tapleaf hash
            skipped += 1
            continue
        version, vin, vout, lock_time = parse_tx(bytes.fromhex(raw_tx))
        result = unified_sighash(
            version,
            lock_time,
            vin,
            vout,
            [(a, bytes.fromhex(s)) for a, s in spent],
            in_idx,
            script_type,
            hash_type,
            script_code=bytes.fromhex(script_code) if script_type in (0, 1) else None,
        )
        assert result.hex() == expected
        run += 1
    assert (run, skipped) == (154, 12)


def test_p2pkh(session: Session):
    """Bare and P2SH are script type 0. For a P2PKH spend the scriptCode is the
    scriptPubKey itself. Also pins the approval screen: the user is told which
    signature hash is being used, by name."""
    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/5h/0/9"),
        amount=63_988,
        prev_hash=TXHASH_0dac36,
        prev_index=0,
        unified_sighash=True,
    )
    out1 = messages.TxOutputType(
        address="13Hbso8zgV5Wmqn3uA7h3QVtmPzs47wcJ7",
        amount=50_248,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with session.test_ctx as client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core(session), messages.ButtonRequest(code=B.ConfirmOutput)),
                # Legacy firmware does not populate ButtonRequest.name.
                messages.ButtonRequest(
                    code=B.SignTx,
                    name="unified_sighash" if is_core(session) else None,
                ),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_0dac36),
                request_input(0, TXHASH_0dac36),
                request_output(0, TXHASH_0dac36),
                request_output(1, TXHASH_0dac36),
                # On core the opt-in takes its digest from the cached
                # sub-hashes, so the second pass over every input and output
                # does not happen. Model One keeps that pass, because there it
                # is also what checks the inputs against the ones approved.
                request_input(0),
                request_output(0),
                (not is_core(session), request_output(0)),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            session, "Bitcoin", [inp1], [out1], prev_txes=TX_CACHE_MAINNET
        )

    _, _, _, _, script_sigs, _ = parse_signed_tx(serialized_tx)
    pubkey = script_pushes(script_sigs[0])[1]
    check_ecdsa_input(
        serialized_tx,
        [inp1],
        0,
        SCRIPT_TYPE_BARE,
        p2pkh_script(pubkey),
        TX_CACHE_MAINNET,
        pubkey,
    )


def test_p2sh_multisig(session: Session):
    """Script type 0 again, but the scriptCode is the redeemScript. A P2PKH-only
    test cannot tell the two apart."""
    nodes = [
        btc.get_public_node(
            session, parse_path(f"m/48h/1h/{index}h/0h"), coin_name="Testnet"
        ).node
        for index in range(1, 4)
    ]
    multisig = messages.MultisigRedeemScriptType(
        nodes=nodes, address_n=[0, 0], signatures=[b"", b"", b""], m=2
    )
    inp1 = messages.TxInputType(
        address_n=parse_path("m/48h/1h/1h/0h/0/0"),
        amount=1_496_278,
        prev_hash=TXHASH_6b07c1,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDMULTISIG,
        multisig=multisig,
        unified_sighash=True,
    )
    out1 = messages.TxOutputType(
        address="mnY26FLTzfC94mDoUcyDJh1GVE3LuAUMbs",
        amount=1_496_278 - 10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    pubkey = btc.get_public_node(
        session, parse_path("m/48h/1h/1h/0h/0/0"), coin_name="Testnet"
    ).node.public_key

    _, serialized_tx = btc.sign_tx(
        session, "Testnet", [inp1], [out1], prev_txes=TX_CACHE_TESTNET
    )

    # The redeemScript is the last push of the scriptSig.
    _, _, _, _, script_sigs, _ = parse_signed_tx(serialized_tx)
    redeem_script = script_pushes(script_sigs[0])[-1]
    assert redeem_script[0] == 0x52  # OP_2
    check_ecdsa_input(
        serialized_tx,
        [inp1],
        0,
        SCRIPT_TYPE_BARE,
        redeem_script,
        TX_CACHE_TESTNET,
        pubkey,
    )


def test_p2sh_multisig_2_of_3(session: Session):
    """Two signing sessions on different keys, the second carrying the first's
    signature. Both rounds have to arrive at the same digest and the same
    scriptCode; a single-signature multisig never exercises that."""
    pubnodes = [
        btc.get_public_node(
            session, parse_path(f"m/48h/1h/{i}h/0h"), coin_name="Testnet"
        ).node
        for i in (1, 2, 3)
    ]

    def redeem(signatures):
        return messages.MultisigRedeemScriptType(
            nodes=pubnodes, address_n=[0, 0], signatures=signatures, m=2
        )

    def sign(multisig, index):
        inp = messages.TxInputType(
            address_n=parse_path(f"m/48h/1h/{index}h/0h/0/0"),
            amount=1_496_278,
            prev_hash=TXHASH_6b07c1,
            prev_index=0,
            script_type=messages.InputScriptType.SPENDMULTISIG,
            multisig=multisig,
            unified_sighash=True,
        )
        out = messages.TxOutputType(
            address="mnY26FLTzfC94mDoUcyDJh1GVE3LuAUMbs",
            amount=1_496_278 - 10_000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        )
        return (
            btc.sign_tx(session, "Testnet", [inp], [out], prev_txes=TX_CACHE_TESTNET),
            inp,
        )

    empty = [b"", b"", b""]
    (first, _), inp1 = sign(redeem(empty), 1)
    (_, serialized_tx), _ = sign(redeem([first[0], b"", b""]), 2)

    _, _, _, _, script_sigs, _ = parse_signed_tx(serialized_tx)
    items = script_pushes(script_sigs[0])
    redeem_script = items[-1]
    assert redeem_script[0] == 0x52  # OP_2
    signatures = [i for i in items if i and i[0] == 0x30]
    assert len(signatures) == 2

    # Both signatures, made in independent sessions, against one recomputed digest.
    for index, signature in zip((1, 2), signatures):
        assert signature[-1] == HASH_TYPE, hex(signature[-1])
        pubkey = btc.get_public_node(
            session, parse_path(f"m/48h/1h/{index}h/0h/0/0"), coin_name="Testnet"
        ).node.public_key
        digest = digest_for(
            serialized_tx, [inp1], 0, SCRIPT_TYPE_BARE, redeem_script, TX_CACHE_TESTNET
        )
        verify_ecdsa(pubkey, signature[:-1], digest)


def test_p2sh_p2wpkh_and_p2wpkh(session: Session):
    """Two inputs in one transaction. P2SH-wrapped SegWit is script type 1, not
    0: the byte follows the sigversion the input is signed under, not the outer
    script."""
    inp1 = messages.TxInputType(
        address_n=parse_path("m/49h/1h/0h/0/0"),
        amount=40_000,
        prev_hash=TXHASH_65047a,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        unified_sighash=True,
    )
    inp2 = messages.TxInputType(
        address_n=parse_path("m/84h/1h/0h/0/87"),
        amount=100_000,
        prev_hash=TXHASH_d159fd,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
        unified_sighash=True,
    )
    out1 = messages.TxOutputType(
        address="tb1q54un3q39sf7e7tlfq99d6ezys7qgc62a6rxllc",
        amount=25_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address="mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q",
        amount=100_000 + 40_000 - 25_000 - 10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    inputs = [inp1, inp2]
    _, serialized_tx = btc.sign_tx(
        session, "Testnet", inputs, [out1, out2], prev_txes=TX_CACHE_TESTNET
    )

    _, _, _, _, _, witnesses = parse_signed_tx(serialized_tx)
    for i in (0, 1):
        check_ecdsa_input(
            serialized_tx,
            inputs,
            i,
            SCRIPT_TYPE_WITNESS_V0,
            p2pkh_script(witnesses[i][1]),
            TX_CACHE_TESTNET,
            witnesses[i][1],
        )


def test_p2sh_p2wsh_multisig(session: Session):
    """Script type 1 with a witnessScript rather than the implied P2PKH one."""
    nodes = [
        btc.get_public_node(
            session, parse_path(f"m/49h/1h/{index}h"), coin_name="Testnet"
        )
        for index in range(1, 4)
    ]
    multisig = messages.MultisigRedeemScriptType(
        nodes=[deserialize(n.xpub) for n in nodes],
        address_n=[0, 0],
        signatures=[b"", b"", b""],
        m=2,
    )
    inp1 = messages.TxInputType(
        address_n=parse_path("m/49h/1h/1h/0/0"),
        prev_hash=TXHASH_b9abfa,
        prev_index=4,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        multisig=multisig,
        amount=100_000,
        unified_sighash=True,
    )
    out1 = messages.TxOutputType(
        address="tb1qch62pf820spe9mlq49ns5uexfnl6jzcezp7d328fw58lj0rhlhasge9hzy",
        amount=100_000 - 10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    pubkey = btc.get_public_node(
        session, parse_path("m/49h/1h/1h/0/0"), coin_name="Testnet"
    ).node.public_key

    _, serialized_tx = btc.sign_tx(
        session, "Testnet", [inp1], [out1], prev_txes=TX_CACHE_TESTNET
    )

    _, _, _, _, _, witnesses = parse_signed_tx(serialized_tx)
    witness_script = witnesses[0][-1]
    assert witness_script[0] == 0x52  # OP_2
    check_ecdsa_input(
        serialized_tx,
        [inp1],
        0,
        SCRIPT_TYPE_WITNESS_V0,
        witness_script,
        TX_CACHE_TESTNET,
        pubkey,
    )


def test_p2tr(session: Session):
    """Taproot key path is script type 2. There is no unified form of
    SIGHASH_DEFAULT, so the signature carries the hash type byte and is 65
    bytes."""
    inp1 = messages.TxInputType(
        address_n=parse_path("m/86h/1h/0h/1/0"),
        amount=4_600,
        prev_hash=TXHASH_ec5194,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDTAPROOT,
        unified_sighash=True,
    )
    out1 = messages.TxOutputType(
        address="tb1paxhjl357yzctuf3fe58fcdx6nul026hhh6kyldpfsf3tckj9a3wslqd7zd",
        amount=4_450,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    _, serialized_tx = btc.sign_tx(
        session, "Testnet", [inp1], [out1], prev_txes=TX_CACHE_TESTNET
    )

    _, _, _, _, _, witnesses = parse_signed_tx(serialized_tx)
    assert len(witnesses[0]) == 1
    assert len(witnesses[0][0]) == 65
    assert witnesses[0][0][64] == HASH_TYPE

    digest = digest_for(
        serialized_tx, [inp1], 0, SCRIPT_TYPE_TAPROOT, None, TX_CACHE_TESTNET
    )
    output_key = TX_CACHE_TESTNET[TXHASH_ec5194].bin_outputs[0].script_pubkey[2:]
    assert bip340_verify(output_key, witnesses[0][0][:64], digest)


def test_external_input_refused(session: Session):
    inp1 = messages.TxInputType(
        amount=100_000,
        prev_hash=TXHASH_d159fd,
        prev_index=0,
        script_type=messages.InputScriptType.EXTERNAL,
        script_pubkey=bytes.fromhex("0014b7c1b6be1a45e0f18e1c5b0f0a3d5cc9d9b13cf8"),
        unified_sighash=True,
    )
    out1 = messages.TxOutputType(
        address="mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q",
        amount=90_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with pytest.raises(TrezorFailure, match="external inputs"):
        btc.sign_tx(session, "Testnet", [inp1], [out1], prev_txes=TX_CACHE_TESTNET)


@pytest.mark.altcoin
def test_altcoin_refused(session: Session):
    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/2h/0h/0/0"),
        amount=100_000,
        prev_hash=TXHASH_d159fd,
        prev_index=0,
        unified_sighash=True,
    )
    out1 = messages.TxOutputType(
        address="LcubERmHD31PWup1fbozpKuiqBd2ZDPaCC",
        amount=90_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with pytest.raises(TrezorFailure, match="not enabled on this coin"):
        btc.sign_tx(session, "Litecoin", [inp1], [out1], prev_txes={})


def test_sibling_amount_is_committed_to(session: Session):
    """CVE-2020-14199: the message commits to every spent amount, not just this
    input's, so a signer told the wrong amount for a sibling input produces a
    signature that does not verify against the truth. BIP-143 does not."""
    inp1 = messages.TxInputType(
        address_n=parse_path("m/49h/1h/0h/0/0"),
        amount=40_000,
        prev_hash=TXHASH_65047a,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        unified_sighash=True,
    )
    inp2 = messages.TxInputType(
        address_n=parse_path("m/84h/1h/0h/0/87"),
        amount=100_000,
        prev_hash=TXHASH_d159fd,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
        unified_sighash=True,
    )
    out1 = messages.TxOutputType(
        address="mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q",
        amount=100_000 + 40_000 - 10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    inputs = [inp1, inp2]
    _, serialized_tx = btc.sign_tx(
        session, "Testnet", inputs, [out1], prev_txes=TX_CACHE_TESTNET
    )
    version, vin, vout, lock_time, _, witnesses = parse_signed_tx(serialized_tx)
    spent = spent_outputs(inputs, TX_CACHE_TESTNET)
    script_code = p2pkh_script(witnesses[0][1])

    def digest(spent_outs):
        return unified_sighash(
            version,
            lock_time,
            vin,
            vout,
            spent_outs,
            0,
            SCRIPT_TYPE_WITNESS_V0,
            HASH_TYPE,
            script_code=script_code,
        )

    # Only the sibling's amount changes; input 0 is untouched.
    lied = [spent[0], (spent[1][0] + 1, spent[1][1])]
    assert digest(spent) != digest(lied)

    signature = witnesses[0][0][:-1]
    verify_ecdsa(witnesses[0][1], signature, digest(spent))
    with pytest.raises(ecdsa.BadSignatureError):
        verify_ecdsa(witnesses[0][1], signature, digest(lied))


def _two_legacy_inputs(first_unified: bool, second_unified: bool):
    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/0h/0/55"),
        amount=10_000,
        prev_hash=TXHASH_ac4ca0,
        prev_index=1,
        unified_sighash=first_unified,
    )
    inp2 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/0h/1/7"),
        amount=83_130,
        prev_hash=TXHASH_ac4ca0,
        prev_index=0,
        unified_sighash=second_unified,
    )
    out1 = messages.TxOutputType(
        address_n=parse_path("m/44h/0h/0h/1/8"),
        amount=71_790,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address="1ByqmhXkC6U5GuUNnAhJsuEVjHt5GhEuJL",
        amount=10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    return [inp1, inp2], [out1, out2]


@pytest.mark.parametrize(
    "flags",
    ((True, False), (False, True), (True, True)),
    ids=("first", "second", "both"),
)
def test_mixed_legacy_inputs(session: Session, flags):
    """The opt-in is per input, so a transaction can carry both kinds. Each
    input has to get the algorithm it asked for, and the progress bar has to
    account for the ones that no longer re-stream the transaction."""
    inputs, outputs = _two_legacy_inputs(*flags)

    _, serialized_tx = btc.sign_tx(
        session, "Bitcoin", inputs, outputs, prev_txes=TX_CACHE_MAINNET
    )

    _, _, _, _, script_sigs, _ = parse_signed_tx(serialized_tx)
    for i, unified in enumerate(flags):
        items = script_pushes(script_sigs[i])
        signature, pubkey = items[0], items[1]
        assert signature[-1] == (HASH_TYPE if unified else 0x01), hex(signature[-1])
        if unified:
            check_ecdsa_input(
                serialized_tx,
                inputs,
                i,
                SCRIPT_TYPE_BARE,
                p2pkh_script(pubkey),
                TX_CACHE_MAINNET,
                pubkey,
            )


def test_fee_bump_of_a_legacy_transaction(session: Session):
    """Replacing a transaction that was signed the legacy way with one that opts
    in. The original's own inputs are still verified with the legacy digest, by
    re-streaming it, which the progress accounting has to count even though the
    replacement no longer needs that pass for itself."""
    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/0h/0/4"),
        amount=174_998,
        prev_hash=TXHASH_beafc7,
        prev_index=0,
        orig_hash=TXHASH_50f6f1,
        orig_index=0,
        unified_sighash=True,
    )
    out1 = messages.TxOutputType(
        address_n=parse_path("m/44h/0h/0h/1/2"),
        amount=174_998 - 50_000 - 15_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        orig_hash=TXHASH_50f6f1,
        orig_index=0,
    )
    out2 = messages.TxOutputType(
        address="1GA9u9TfCG7SWmKCveBumdA1TZpfom6ZdJ",
        amount=50_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        orig_hash=TXHASH_50f6f1,
        orig_index=1,
    )

    _, serialized_tx = btc.sign_tx(
        session, "Bitcoin", [inp1], [out1, out2], prev_txes=TX_CACHE_MAINNET
    )

    _, _, _, _, script_sigs, _ = parse_signed_tx(serialized_tx)
    pubkey = script_pushes(script_sigs[0])[1]
    check_ecdsa_input(
        serialized_tx,
        [inp1],
        0,
        SCRIPT_TYPE_BARE,
        p2pkh_script(pubkey),
        TX_CACHE_MAINNET,
        pubkey,
    )


def test_replacement_cannot_drop_the_opt_in(session: Session):
    """The opt-in is what the user was warned about and approved. A replacement
    that changes nothing else is confirmed with the TXID screen alone, so if it
    could quietly drop the opt-in the host would walk away with a
    pre-fork-valid signature over the same transaction."""
    orig = TX_CACHE_MAINNET[TXHASH_50f6f1]
    for txi in orig.inputs:
        txi.unified_sighash = True
    prev_txes = {TXHASH_50f6f1: orig, TXHASH_beafc7: TX_CACHE_MAINNET[TXHASH_beafc7]}

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/0h/0/4"),
        amount=174_998,
        prev_hash=TXHASH_beafc7,
        prev_index=0,
        orig_hash=TXHASH_50f6f1,
        orig_index=0,
        unified_sighash=False,
    )
    out1 = messages.TxOutputType(
        address_n=parse_path("m/44h/0h/0h/1/2"),
        amount=174_998 - 50_000 - 15_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        orig_hash=TXHASH_50f6f1,
        orig_index=0,
    )
    out2 = messages.TxOutputType(
        address="1GA9u9TfCG7SWmKCveBumdA1TZpfom6ZdJ",
        amount=50_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        orig_hash=TXHASH_50f6f1,
        orig_index=1,
    )

    with pytest.raises(TrezorFailure, match="unified signature hash"):
        btc.sign_tx(session, "Bitcoin", [inp1], [out1, out2], prev_txes=prev_txes)


def test_signature_only(session: Session):
    """serialize=False returns signatures without building the transaction. The
    opt-in changes which digest is signed, not how the result is returned."""
    inputs, outputs = _two_legacy_inputs(True, True)

    signatures, serialized_tx = btc.sign_tx(
        session, "Bitcoin", inputs, outputs, prev_txes=TX_CACHE_MAINNET, serialize=False
    )
    assert serialized_tx == b""
    assert all(sig for sig in signatures)

    _, full_tx = btc.sign_tx(
        session, "Bitcoin", inputs, outputs, prev_txes=TX_CACHE_MAINNET
    )
    _, _, _, _, script_sigs, _ = parse_signed_tx(full_tx)
    for i, sig in enumerate(signatures):
        # The serialized scriptSig carries the same signature plus the hash type.
        assert script_pushes(script_sigs[i])[0] == sig + bytes([HASH_TYPE])


@pytest.mark.parametrize("approved", (True, False))
def test_opt_in_cannot_change_after_approval(session: Session, approved: bool):
    """The opt-in picks the signing algorithm and is what the approval screen
    reports, and both algorithms produce a valid signature. So a host that gets
    one approved and streams the other at signing time has to be refused, and
    nothing else in the protocol would catch it."""
    inp1 = messages.TxInputType(
        address_n=parse_path("m/84h/1h/0h/0/87"),
        amount=100_000,
        prev_hash=TXHASH_d159fd,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
        unified_sighash=approved,
    )
    out1 = messages.TxOutputType(
        address="mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q",
        amount=90_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    # Our input is streamed four times: approval, verification, serialization
    # and signing. Flip the flag on the last one only, so the checks that were
    # already there have all passed by the time it is seen.
    seen = 0

    def attack_processor(msg):
        nonlocal seen
        if msg.tx.inputs and msg.tx.inputs[0].prev_hash == TXHASH_d159fd:
            seen += 1
            if seen == 4:
                msg.tx.inputs[0].unified_sighash = not approved
        return msg

    with session.test_ctx as client:
        client.set_filter(messages.TxAck, attack_processor)
        with pytest.raises(TrezorFailure, match="Transaction has changed"):
            btc.sign_tx(session, "Testnet", [inp1], [out1], prev_txes=TX_CACHE_TESTNET)
    assert seen == 4


def bip340_verify(output_key: bytes, signature: bytes, digest: bytes) -> bool:
    """BIP-340 Schnorr verification, from the BIP's own pseudocode."""
    p = 2**256 - 2**32 - 977
    n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    curve = ecdsa.SECP256k1.curve
    gen = ecdsa.SECP256k1.generator

    from .unified_sighash import tagged_hash

    x = int.from_bytes(output_key, "big")
    if x >= p:
        return False
    y_sq = (pow(x, 3, p) + 7) % p
    y = pow(y_sq, (p + 1) // 4, p)
    if pow(y, 2, p) != y_sq:
        return False
    if y % 2 != 0:
        y = p - y  # even y, as BIP-340 lifts it
    point = ecdsa.ellipticcurve.Point(curve, x, y, n)

    r = int.from_bytes(signature[:32], "big")
    s = int.from_bytes(signature[32:], "big")
    if r >= p or s >= n:
        return False
    e = (
        int.from_bytes(
            tagged_hash("BIP0340/challenge", signature[:32] + output_key + digest),
            "big",
        )
        % n
    )
    result = s * gen + (n - e) * point
    if result is ecdsa.ellipticcurve.INFINITY:
        return False
    return result.y() % 2 == 0 and result.x() == r
