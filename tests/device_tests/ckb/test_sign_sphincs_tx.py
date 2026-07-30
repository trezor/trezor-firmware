"""Device tests for the CKB SPHINCS+ signing flow, including Nervos DAO.

SPHINCS+ keys are derived from an extended BIP-39 mnemonic (36 words for the
128-bit variants), which the debug LoadDevice only accepts with
skip_checksum=True, so every test starts from an uninitialized client and loads
the seed itself.
"""

import pytest

from trezorlib import ckb, debuglink
from trezorlib.debuglink import TrezorTestContext
from trezorlib.exceptions import TrezorFailure

from ...input_flows import InputFlowConfirmAllWarnings
from . import prevtx, spx_ref

pytestmark = [
    pytest.mark.altcoin,
    pytest.mark.ckb,
    pytest.mark.models("t3w1"),
    pytest.mark.setup_client(uninitialized=True),
]

# 3x16 bytes of entropy for the default variant 49. Chunks must be distinct.
_CHUNK_1 = ["all"] * 12
_CHUNK_2 = ["abandon"] * 11 + ["about"]
_CHUNK_3 = ["zoo"] * 11 + ["abstract"]
MNEMONIC_SPHINCS = " ".join(_CHUNK_1 + _CHUNK_2 + _CHUNK_3)
VARIANT = 49

SHANNON = 100_000_000
DAO_CODE_HASH = "82d76d1b75fe2fd9a27dfbaa65a039221a380d76c926f378d3f81cf3e7e13f2e"
# Deployed code hash of the CKB SPHINCS+ lock script (apps.ckb.get_sphincs_address).
SPHINCS_CODE_HASH_MAINNET = (
    "302d35982f865ebcbedb9a9360e40530ed32adb8e10b42fbbe70d8312ff7cedf"
)
SPHINCS_HASH_TYPE_MAINNET = 1


def _load_sphincs_session(test_ctx: TrezorTestContext, mnemonic: str | None = None):
    debuglink.load_device(
        test_ctx.get_seedless_session(),
        mnemonic=mnemonic or MNEMONIC_SPHINCS,
        pin="",
        passphrase_protection=False,
        label="test",
        skip_checksum=True,
    )
    return test_ctx.get_session()


@pytest.mark.parametrize(
    "chunks",
    [
        pytest.param((_CHUNK_1, _CHUNK_2, _CHUNK_1), id="1==3"),
        pytest.param((_CHUNK_1, _CHUNK_1, _CHUNK_1), id="all-equal"),
        pytest.param((_CHUNK_1, _CHUNK_2, _CHUNK_2), id="2==3"),
        pytest.param((_CHUNK_1, _CHUNK_1, _CHUNK_2), id="1==2"),
    ],
)
def test_sphincs_rejects_degenerate_mnemonic(test_ctx: TrezorTestContext, chunks):
    session = _load_sphincs_session(test_ctx, " ".join(sum(chunks, [])))
    with pytest.raises(TrezorFailure, match="sub-phrases must all differ"):
        ckb.get_sphincs_address(session, network="Mainnet", variant=VARIANT)


def _sphincs_lock(session):
    """The signer's lock (lock_args, public_key) as the device derives it."""
    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        resp = ckb.get_sphincs_address(session, network="Mainnet", variant=VARIANT)
    assert len(resp.lock_args) == 32
    return bytes(resp.lock_args), bytes(resp.public_key)


def _sphincs_cell(lock_args: bytes, capacity: int, **kwargs):
    """A cell locked by the signer's SPHINCS+ lock script."""
    return ckb.create_cell_output(
        capacity=capacity,
        lock_code_hash=SPHINCS_CODE_HASH_MAINNET,
        lock_hash_type=SPHINCS_HASH_TYPE_MAINNET,
        lock_args=lock_args,
        **kwargs,
    )


def _external_output(capacity: int):
    return ckb.create_cell_output(
        capacity=capacity,
        lock_code_hash=prevtx.LOCK_CODE_HASH,
        lock_hash_type=1,
        lock_args="aa" * 20,
    )


def _plain_transfer(lock_args: bytes):
    """One SPHINCS+ input funding one external output, fee 1000 shannons."""
    spent = _sphincs_cell(lock_args, 1000 * SHANNON)
    prev_hash = prevtx.raw_tx_hash([], [spent], [b""], [])
    inputs = [ckb.create_cell_input(tx_hash=prev_hash, index=0)]
    outputs = [_external_output(1000 * SHANNON - 1000)]
    return inputs, outputs, {prev_hash: ckb.create_prev_tx(outputs=[spent])}


def _withdrawing_input(lock_args: bytes, deposit_number: int, capacity: int):
    """A phase-2 DAO withdrawing cell spent with header_deps indices 0/1."""
    cell_data = deposit_number.to_bytes(8, "little")
    cell = _sphincs_cell(
        lock_args,
        capacity,
        type_code_hash=DAO_CODE_HASH,
        type_hash_type=1,
        type_args=b"",
        data=cell_data,
    )
    prev_hash = prevtx.raw_tx_hash([], [cell], [cell_data], [])
    inp = ckb.create_cell_input(
        tx_hash=prev_hash,
        index=0,
        dao_deposit_header_index=0,
        dao_withdraw_header_index=1,
    )
    return inp, {prev_hash: ckb.create_prev_tx(outputs=[cell])}


def _phase2_witnesses():
    # input_type holds the deposit header's index in header_deps, as the
    # on-chain DAO type script requires.
    return [ckb.create_witness_args(input_type=(0).to_bytes(8, "little"))]


def _sign(session, **kwargs):
    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        return ckb.sign_sphincs_tx(
            session, network="Mainnet", variant=VARIANT, **kwargs
        )


def _assert_witness_lock(witness_lock: bytes, public_key: bytes):
    """Check the assembled witness lock structure (multisig header || pk || sig)."""
    flag = ((VARIANT << 1) | 1) & 0xFF
    # require_first_n is 1, set by "fix(ckb): correct SPHINCS+ address generation".
    assert witness_lock[:5] == bytes([0x80, 0x01, 0x01, 0x01, flag])
    assert witness_lock[5 : 5 + len(public_key)] == public_key
    # An SLH-DSA-128s signature is 7856 bytes.
    assert len(witness_lock) == 5 + len(public_key) + 7856


def _make_header(number, ar, timestamp=1_573_852_800_000):
    return ckb.create_block_header(
        version=0,
        compact_target=0x1A08A97E,
        timestamp=timestamp,
        number=number,
        epoch=0,
        parent_hash="00" * 32,
        transactions_root="00" * 32,
        proposals_hash="00" * 32,
        extra_hash="00" * 32,
        dao=prevtx.make_dao(1, ar, 2, 3),
        nonce="00" * 16,
    )


def test_sign_sphincs_tx_signature_covers_the_right_message(
    test_ctx: TrezorTestContext,
):
    # The other tests would pass on a device that signed a constant.
    session = _load_sphincs_session(test_ctx)
    lock_args, public_key = _sphincs_lock(session)
    inputs, outputs, prev_txs = _plain_transfer(lock_args)

    signed = _sign(session, inputs=inputs, outputs=outputs, prev_txs=prev_txs)
    signature = signed.witness_lock[5 + len(public_key) :]

    spent = prev_txs[bytes(inputs[0].previous_output_tx_hash)].outputs[0]
    message = prevtx.ckb_tx_message_all(
        tx_hash=signed.tx_hash,
        input_cells=[(spent, b"")],
        group_indices=[0],
        first_input_type=b"",
        first_output_type=b"",
        witnesses_raw={},
        inputs_count=1,
        witnesses_count=1,
    )

    try:
        ok = spx_ref.verify_sha2_128s(
            prevtx.fips205_pure(message), signature, public_key
        )
    except spx_ref.BuildUnavailable as exc:
        pytest.skip(f"reference verifier unavailable: {exc}")

    assert ok, "device signature does not cover the expected ckb_tx_message_all"

    # Guard against the assertion above passing vacuously.
    tampered = bytearray(message)
    tampered[0] ^= 0x01
    assert not spx_ref.verify_sha2_128s(
        prevtx.fips205_pure(bytes(tampered)), signature, public_key
    )


def test_sign_sphincs_tx_plain(test_ctx: TrezorTestContext):
    # Baseline: a plain transfer without header_deps still signs, and the device
    # hashes exactly the streamed transaction.
    session = _load_sphincs_session(test_ctx)
    lock_args, public_key = _sphincs_lock(session)
    inputs, outputs, prev_txs = _plain_transfer(lock_args)

    signed = _sign(session, inputs=inputs, outputs=outputs, prev_txs=prev_txs)

    assert signed.tx_hash == prevtx.raw_tx_hash(inputs, outputs, [b""], [])
    _assert_witness_lock(signed.witness_lock, public_key)


def test_sign_sphincs_tx_commits_header_deps(test_ctx: TrezorTestContext):
    # header_deps are committed in the raw tx hash; a device that ignored them
    # would sign a hash that does not match the broadcast transaction.
    session = _load_sphincs_session(test_ctx)
    lock_args, public_key = _sphincs_lock(session)
    inputs, outputs, prev_txs = _plain_transfer(lock_args)
    header_deps = [bytes.fromhex("11" * 32), bytes.fromhex("22" * 32)]

    signed = _sign(
        session,
        inputs=inputs,
        outputs=outputs,
        prev_txs=prev_txs,
        header_deps=header_deps,
    )

    with_deps = prevtx.raw_tx_hash(inputs, outputs, [b""], [], header_deps=header_deps)
    without_deps = prevtx.raw_tx_hash(inputs, outputs, [b""], [])
    assert signed.tx_hash == with_deps
    assert signed.tx_hash != without_deps
    _assert_witness_lock(signed.witness_lock, public_key)


def test_sign_sphincs_tx_dao_deposit(test_ctx: TrezorTestContext):
    # A Nervos DAO deposit: an output carrying the DAO type script and 8 zero
    # bytes of data. It must be signable and surfaced with the type-script
    # warning, not mistaken for hidden change (which requires no type script).
    session = _load_sphincs_session(test_ctx)
    lock_args, public_key = _sphincs_lock(session)

    spent = _sphincs_cell(lock_args, 600 * SHANNON)
    prev_hash = prevtx.raw_tx_hash([], [spent], [b""], [])
    inputs = [ckb.create_cell_input(tx_hash=prev_hash, index=0)]

    deposit_data = bytes(8)
    outputs = [
        _sphincs_cell(
            lock_args,
            500 * SHANNON,
            type_code_hash=DAO_CODE_HASH,
            type_hash_type=1,
            type_args=b"",
            data=deposit_data,
        ),
        _sphincs_cell(lock_args, 100 * SHANNON - 1000),  # change
    ]

    signed = _sign(
        session,
        inputs=inputs,
        outputs=outputs,
        prev_txs={prev_hash: ckb.create_prev_tx(outputs=[spent])},
    )

    assert signed.tx_hash == prevtx.raw_tx_hash(
        inputs, outputs, [deposit_data, b""], []
    )
    _assert_witness_lock(signed.witness_lock, public_key)


def test_sign_sphincs_tx_dao_withdraw(test_ctx: TrezorTestContext):
    # A Nervos DAO phase-2 withdrawal: the input is a withdrawing cell locked by
    # the signer's SPHINCS+ lock whose unlocked value (deposit + compensation)
    # exceeds its plain capacity. The device must verify the deposit/withdraw
    # headers against header_deps and credit the compensation instead of
    # rejecting with "Inputs do not cover outputs".
    session = _load_sphincs_session(test_ctx)
    lock_args, public_key = _sphincs_lock(session)

    ar_deposit = 10_000_000_000_000_000
    ar_withdraw = 10_050_000_000_000_000  # +0.5% accumulated rate
    deposit_number = 100
    deposit_capacity = 20000 * SHANNON

    deposit_header = _make_header(deposit_number, ar_deposit)
    withdraw_header = _make_header(200_000, ar_withdraw, timestamp=1_576_852_800_000)
    header_deps = [
        prevtx.header_hash(deposit_header),
        prevtx.header_hash(withdraw_header),
    ]

    inp, prev_txs = _withdrawing_input(lock_args, deposit_number, deposit_capacity)

    occupied = prevtx.occupied_capacity(lock_args_len=32, type_args_len=0, data_len=8)
    max_withdraw = prevtx.dao_maximum_withdraw(
        deposit_capacity, occupied, ar_deposit, ar_withdraw
    )
    fee = 1000
    out_capacity = max_withdraw - fee
    assert out_capacity > deposit_capacity
    output = _external_output(out_capacity)

    signed = _sign(
        session,
        inputs=[inp],
        outputs=[output],
        witnesses=_phase2_witnesses(),
        prev_txs=prev_txs,
        header_deps=header_deps,
        headers=[deposit_header, withdraw_header],
    )

    assert signed.tx_hash == prevtx.raw_tx_hash(
        [inp], [output], [b""], [], header_deps=header_deps
    )
    _assert_witness_lock(signed.witness_lock, public_key)


def test_sign_sphincs_tx_rejects_tampered_dao_header(test_ctx: TrezorTestContext):
    # The device must reject a DAO withdrawal whose supplied header does not
    # hash to the committed header_deps entry (a host inflating compensation).
    session = _load_sphincs_session(test_ctx)
    lock_args, _ = _sphincs_lock(session)

    deposit_number = 100
    honest_deposit = _make_header(deposit_number, 10_000_000_000_000_000)
    honest_withdraw = _make_header(200_000, 10_050_000_000_000_000)
    header_deps = [
        prevtx.header_hash(honest_deposit),
        prevtx.header_hash(honest_withdraw),
    ]
    # Host lies: serves a withdraw header with a much higher AR than the one
    # whose hash is committed in header_deps.
    lying_withdraw = _make_header(200_000, 99_000_000_000_000_000)

    inp, prev_txs = _withdrawing_input(lock_args, deposit_number, 20000 * SHANNON)
    output = _external_output(20100 * SHANNON)

    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        with pytest.raises(TrezorFailure, match="header hash mismatch"):
            ckb.sign_sphincs_tx(
                session,
                inputs=[inp],
                outputs=[output],
                witnesses=_phase2_witnesses(),
                network="Mainnet",
                variant=VARIANT,
                prev_txs=prev_txs,
                header_deps=header_deps,
                headers=[honest_deposit, lying_withdraw],
            )
