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

from ...common import MNEMONIC_SLIP39_BASIC_20_3of6
from ...input_flows import InputFlowConfirmAllWarnings
from . import prevtx, spx_ref
from .test_sign_tx import AR_DEPOSIT, AR_WITHDRAW, _dao_header

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

# 54 words (3x24 bytes) key the n=24 variants.
MNEMONIC_SPHINCS_54 = " ".join(
    ["abandon"] * 17 + ["agent"] + ["all"] * 17 + ["action"] + ["zoo"] * 17 + ["advice"]
)
# 72 words (3x32 bytes) key the n=32 variants.
MNEMONIC_SPHINCS_72 = " ".join(
    ["abandon"] * 23 + ["art"] + ["all"] * 23 + ["answer"] + ["zoo"] * 23 + ["buddy"]
)
VARIANTS_N16 = (48, 49, 54, 55)
VARIANTS_N24 = (50, 51, 56, 57)
VARIANTS_N32 = (52, 53, 58, 59)
MNEMONIC_FOR_STRENGTH = {16: None, 24: MNEMONIC_SPHINCS_54, 32: MNEMONIC_SPHINCS_72}

MNEMONIC_BIP39_12 = " ".join(_CHUNK_1)

SHANNON = 100_000_000
DAO_CODE_HASH = "82d76d1b75fe2fd9a27dfbaa65a039221a380d76c926f378d3f81cf3e7e13f2e"
# Deployed code hash of the on-chain CKB SPHINCS+ lock script.
SPHINCS_CODE_HASH_MAINNET = (
    "302d35982f865ebcbedb9a9360e40530ed32adb8e10b42fbbe70d8312ff7cedf"
)
SPHINCS_HASH_TYPE_MAINNET = 1


def _load_sphincs_session(
    test_ctx: TrezorTestContext,
    mnemonic: str | list[str] | None = None,
    passphrase_protection: bool = False,
):
    debuglink.load_device(
        test_ctx.get_seedless_session(),
        mnemonic=mnemonic or MNEMONIC_SPHINCS,
        pin="",
        passphrase_protection=passphrase_protection,
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


def test_sphincs_rejects_passphrase_protection(test_ctx: TrezorTestContext):
    # The derivation bypasses PBKDF2 passphrase mixing, so without this refusal
    # a hidden wallet would silently share keys with the standard one.
    session = _load_sphincs_session(test_ctx, passphrase_protection=True)
    with pytest.raises(TrezorFailure, match="does not yet support BIP-39 passphrase"):
        ckb.get_sphincs_address(session, network="Mainnet", variant=VARIANT)


def test_sphincs_rejects_slip39_backup(test_ctx: TrezorTestContext):
    session = _load_sphincs_session(test_ctx, MNEMONIC_SLIP39_BASIC_20_3of6)
    with pytest.raises(TrezorFailure, match="requires a BIP-39 extended mnemonic"):
        ckb.get_sphincs_address(session, network="Mainnet", variant=VARIANT)


def test_sphincs_rejects_standard_mnemonic(test_ctx: TrezorTestContext):
    session = _load_sphincs_session(test_ctx, MNEMONIC_BIP39_12)
    with pytest.raises(TrezorFailure, match="requires an extended mnemonic"):
        ckb.get_sphincs_address(session, network="Mainnet", variant=VARIANT)


def test_sphincs_rejects_uninitialized_device(test_ctx: TrezorTestContext):
    with pytest.raises(TrezorFailure, match="Device not initialized"):
        ckb.get_sphincs_address(
            test_ctx.get_seedless_session(), network="Mainnet", variant=VARIANT
        )


def test_sphincs_rejects_variant_wider_than_the_mnemonic(test_ctx: TrezorTestContext):
    # The refusal must name the variants that do fit the stored strength, or the
    # user has no way to know which ones to pick.
    session = _load_sphincs_session(test_ctx)

    with pytest.raises(TrezorFailure) as excinfo:
        ckb.get_sphincs_address(session, network="Mainnet", variant=50)

    message = excinfo.value.message
    assert "does not match the stored" in message
    assert "SHA2_192F" in message, f"the rejected variant is not named: {message}"
    for allowed in ("SHA2_128F", "SHA2_128S", "SHAKE_128F", "SHAKE_128S"):
        assert allowed in message, f"{allowed} missing from {message}"


@pytest.mark.parametrize(
    "mnemonic,variants,strength",
    [
        pytest.param(MNEMONIC_SPHINCS_54, VARIANTS_N24, 24, id="n24"),
        pytest.param(MNEMONIC_SPHINCS_72, VARIANTS_N32, 32, id="n32"),
    ],
)
def test_sphincs_wide_mnemonic_keys_its_own_variants(
    test_ctx: TrezorTestContext, mnemonic, variants, strength
):
    # Only coverage of n=24/n=32. No golden exists for these keys, so the lock
    # args are recomputed on the host from the returned key instead.
    session = _load_sphincs_session(test_ctx, mnemonic)

    public_keys = []
    for variant in variants:
        resp = ckb.get_sphincs_address(session, network="Mainnet", variant=variant)
        assert resp.variant == variant
        assert len(resp.public_key) == 2 * strength
        assert bytes(resp.lock_args) == prevtx.sphincs_lock_args(
            bytes(resp.public_key), variant
        )
        public_keys.append(bytes(resp.public_key))

    # Public keys, not lock args: lock args hash the variant flag and would
    # differ even if two variant IDs dispatched to the same parameter set.
    assert len(set(public_keys)) == len(variants)

    with pytest.raises(TrezorFailure, match="does not match the stored"):
        ckb.get_sphincs_address(session, network="Mainnet", variant=VARIANT)


def test_sphincs_rejects_invalid_variant(test_ctx: TrezorTestContext):
    # Each handler carries its own copy of the check, so all three are exercised.
    session = _load_sphincs_session(test_ctx)

    with pytest.raises(TrezorFailure, match="Invalid SPHINCS. variant"):
        ckb.get_sphincs_address(session, network="Mainnet", variant=47)
    with pytest.raises(TrezorFailure, match="Invalid SPHINCS. variant"):
        ckb.sign_sphincs_message(session, b"hi", variant=47)
    with pytest.raises(TrezorFailure, match="Invalid SPHINCS. variant"):
        ckb.sign_sphincs_tx(
            session,
            network="Mainnet",
            variant=47,
            inputs=[ckb.create_cell_input(tx_hash=b"\x11" * 32, index=0)],
            outputs=[_external_output(100 * SHANNON)],
        )


def test_sphincs_rejects_invalid_network(test_ctx: TrezorTestContext):
    session = _load_sphincs_session(test_ctx)

    with pytest.raises(TrezorFailure, match="Invalid CKB network"):
        ckb.get_sphincs_address(session, network="Devnet", variant=VARIANT)
    with pytest.raises(TrezorFailure, match="Invalid CKB network"):
        ckb.sign_sphincs_message(session, b"hi", network="Devnet", variant=VARIANT)
    with pytest.raises(TrezorFailure, match="Invalid CKB network"):
        ckb.sign_sphincs_tx(
            session,
            network="Devnet",
            variant=VARIANT,
            inputs=[ckb.create_cell_input(tx_hash=b"\x11" * 32, index=0)],
            outputs=[_external_output(100 * SHANNON)],
        )


def test_sphincs_rejects_out_of_range_account_index(test_ctx: TrezorTestContext):
    # 1_000_000 is the last index that fits the C-side HKDF info buffer; the
    # field is unsigned, so this is the only reachable edge.
    session = _load_sphincs_session(test_ctx)
    too_big = 1_000_001

    with pytest.raises(TrezorFailure, match="Invalid SPHINCS. account index"):
        ckb.get_sphincs_address(
            session, network="Mainnet", variant=VARIANT, account_index=too_big
        )
    with pytest.raises(TrezorFailure, match="Invalid SPHINCS. account index"):
        ckb.sign_sphincs_message(session, b"hi", variant=VARIANT, account_index=too_big)
    with pytest.raises(TrezorFailure, match="Invalid SPHINCS. account index"):
        ckb.sign_sphincs_tx(
            session,
            network="Mainnet",
            variant=VARIANT,
            account_index=too_big,
            inputs=[ckb.create_cell_input(tx_hash=b"\x11" * 32, index=0)],
            outputs=[_external_output(100 * SHANNON)],
        )

    # The bound itself must still work (`>`, not `>=`).
    resp = ckb.get_sphincs_address(
        session, network="Mainnet", variant=VARIANT, account_index=1_000_000
    )
    assert len(resp.lock_args) == 32


def _sphincs_lock(session):
    """The signer's lock (lock_args, public_key) as the device derives it."""
    # No input flow: without show_display the device answers silently.
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
    # input_type = deposit header's index in header_deps, per the DAO type script.
    return [ckb.create_witness_args(input_type=(0).to_bytes(8, "little"))]


def _sign(session, screens: list[str] | None = None, **kwargs):
    """Sign, optionally recording each confirmed screen's text: confirming every
    warning also confirms the wrong one, so label tests must read them."""

    def _record(layout):
        screens.append(layout.text_content())

    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(
                InputFlowConfirmAllWarnings(
                    client, on_page=_record if screens is not None else None
                ).get()
            )
        return ckb.sign_sphincs_tx(
            session, network="Mainnet", variant=VARIANT, **kwargs
        )


def _assert_labelled(screens: list[str], expected: str, *forbidden: str) -> None:
    """Without the forbidden half, swapping any two of the three type-script
    screens would leave these tests green."""
    assert any(expected in s for s in screens), f"{expected!r} not shown: {screens}"
    for text in forbidden:
        assert not any(text in s for s in screens), f"{text!r} shown: {screens}"


# Both DAO screens share the "Nervos DAO" title; only these phrases differ.
_DEPOSIT_LABEL = "Deposit"
_WITHDRAW_LABEL = "Start withdrawing"
_UNKNOWN_LABEL = "unrecognized type script"


def _assert_witness_lock(witness_lock: bytes, public_key: bytes):
    """Check the assembled witness lock structure (multisig header || pk || sig)."""
    flag = ((VARIANT << 1) | 1) & 0xFF
    assert witness_lock[:5] == bytes([0x80, 0x01, 0x01, 0x01, flag])
    assert witness_lock[5 : 5 + len(public_key)] == public_key
    assert len(witness_lock) == 5 + len(public_key) + 7856  # SLH-DSA-128s


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
        spx_ref.skip_or_fail(exc)

    assert ok, "device signature does not cover the expected ckb_tx_message_all"

    # Guard against the assertion above passing vacuously.
    tampered = bytearray(message)
    tampered[0] ^= 0x01
    assert not spx_ref.verify_sha2_128s(
        prevtx.fips205_pure(bytes(tampered)), signature, public_key
    )


def test_sign_sphincs_tx_signature_covers_a_multi_witness_message(
    test_ctx: TrezorTestContext,
):
    # A two-input group with a trailing witness and non-empty type slices: the
    # parts of ckb_tx_message_all the single-input test cannot reach.
    session = _load_sphincs_session(test_ctx)
    lock_args, public_key = _sphincs_lock(session)

    spent = [
        _sphincs_cell(lock_args, 1000 * SHANNON),
        _sphincs_cell(lock_args, 500 * SHANNON),
    ]
    prev_hash = prevtx.raw_tx_hash([], spent, [b"", b""], [])
    inputs = [
        ckb.create_cell_input(tx_hash=prev_hash, index=0),
        ckb.create_cell_input(tx_hash=prev_hash, index=1),
    ]
    outputs = [_external_output(1500 * SHANNON - 1000)]

    input_type = b"\x11" * 8
    output_type = b"\x22" * 4
    group_witness = b"\xdd" * 5
    trailing_witness = b"\xcc" * 6
    witnesses = [
        ckb.create_witness_args(input_type=input_type, output_type=output_type),
        ckb.create_witness_raw(group_witness),
        ckb.create_witness_raw(trailing_witness),
    ]

    signed = _sign(
        session,
        inputs=inputs,
        outputs=outputs,
        witnesses=witnesses,
        prev_txs={prev_hash: ckb.create_prev_tx(outputs=spent)},
    )
    signature = signed.witness_lock[5 + len(public_key) :]

    # message_with() is built on the device's own tx_hash; without this anchor a
    # mis-serialized shape would be signed and reported consistently.
    assert signed.tx_hash == prevtx.raw_tx_hash(inputs, outputs, [b""], [])

    def message_with(witnesses_raw, witnesses_count):
        return prevtx.ckb_tx_message_all(
            tx_hash=signed.tx_hash,
            input_cells=[(spent[0], b""), (spent[1], b"")],
            group_indices=[0, 1],
            first_input_type=prevtx.bytes_opt(input_type),
            first_output_type=prevtx.bytes_opt(output_type),
            witnesses_raw=witnesses_raw,
            inputs_count=2,
            witnesses_count=witnesses_count,
        )

    message = message_with({1: group_witness, 2: trailing_witness}, 3)
    try:
        ok = spx_ref.verify_sha2_128s(
            prevtx.fips205_pure(message), signature, public_key
        )
    except spx_ref.BuildUnavailable as exc:
        spx_ref.skip_or_fail(exc)

    assert ok, "device signature does not cover the multi-witness message"

    # Prove the trailing witness is really folded in.
    assert not spx_ref.verify_sha2_128s(
        prevtx.fips205_pure(message_with({1: group_witness}, 2)),
        signature,
        public_key,
    )

    _assert_witness_lock(signed.witness_lock, public_key)


def test_sign_sphincs_tx_plain(test_ctx: TrezorTestContext):
    session = _load_sphincs_session(test_ctx)
    lock_args, public_key = _sphincs_lock(session)
    inputs, outputs, prev_txs = _plain_transfer(lock_args)

    signed = _sign(session, inputs=inputs, outputs=outputs, prev_txs=prev_txs)

    assert signed.tx_hash == prevtx.raw_tx_hash(inputs, outputs, [b""], [])
    _assert_witness_lock(signed.witness_lock, public_key)


def test_sign_sphincs_tx_commits_header_deps(test_ctx: TrezorTestContext):
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

    screens: list[str] = []
    signed = _sign(
        session,
        screens=screens,
        inputs=inputs,
        outputs=outputs,
        prev_txs={prev_hash: ckb.create_prev_tx(outputs=[spent])},
    )

    _assert_labelled(screens, _DEPOSIT_LABEL, _WITHDRAW_LABEL, _UNKNOWN_LABEL)
    assert signed.tx_hash == prevtx.raw_tx_hash(
        inputs, outputs, [deposit_data, b""], []
    )
    _assert_witness_lock(signed.witness_lock, public_key)


def test_sign_sphincs_tx_dao_start_withdraw(test_ctx: TrezorTestContext):
    session = _load_sphincs_session(test_ctx)
    lock_args, public_key = _sphincs_lock(session)

    deposit_data = bytes(8)
    spent = _sphincs_cell(
        lock_args,
        600 * SHANNON,
        type_code_hash=DAO_CODE_HASH,
        type_hash_type=1,
        type_args=b"",
        data=deposit_data,
    )
    prev_hash = prevtx.raw_tx_hash([], [spent], [deposit_data], [])
    inputs = [ckb.create_cell_input(tx_hash=prev_hash, index=0)]

    withdraw_data = (100).to_bytes(8, "little")
    outputs = [
        _sphincs_cell(
            lock_args,
            500 * SHANNON,
            type_code_hash=DAO_CODE_HASH,
            type_hash_type=1,
            type_args=b"",
            data=withdraw_data,
        ),
        _sphincs_cell(lock_args, 100 * SHANNON - 1000),  # change
    ]

    screens: list[str] = []
    signed = _sign(
        session,
        screens=screens,
        inputs=inputs,
        outputs=outputs,
        prev_txs={prev_hash: ckb.create_prev_tx(outputs=[spent])},
    )

    _assert_labelled(screens, _WITHDRAW_LABEL, _DEPOSIT_LABEL, _UNKNOWN_LABEL)
    assert signed.tx_hash == prevtx.raw_tx_hash(
        inputs, outputs, [withdraw_data, b""], []
    )
    _assert_witness_lock(signed.witness_lock, public_key)


def test_sign_sphincs_tx_unknown_type_script(test_ctx: TrezorTestContext):
    # DAO code hash with non-empty type_args: the near-miss must not be labelled
    # a DAO cell just because the code hash matches.
    session = _load_sphincs_session(test_ctx)
    lock_args, public_key = _sphincs_lock(session)

    spent = _sphincs_cell(lock_args, 600 * SHANNON)
    prev_hash = prevtx.raw_tx_hash([], [spent], [b""], [])
    inputs = [ckb.create_cell_input(tx_hash=prev_hash, index=0)]

    cell_data = bytes(8)
    outputs = [
        _sphincs_cell(
            lock_args,
            500 * SHANNON,
            type_code_hash=DAO_CODE_HASH,
            type_hash_type=1,
            type_args=b"\x01",
            data=cell_data,
        ),
        _sphincs_cell(lock_args, 100 * SHANNON - 1000),  # change
    ]

    screens: list[str] = []
    signed = _sign(
        session,
        screens=screens,
        inputs=inputs,
        outputs=outputs,
        prev_txs={prev_hash: ckb.create_prev_tx(outputs=[spent])},
    )

    _assert_labelled(screens, _UNKNOWN_LABEL, _DEPOSIT_LABEL, _WITHDRAW_LABEL)
    assert signed.tx_hash == prevtx.raw_tx_hash(inputs, outputs, [cell_data, b""], [])
    _assert_witness_lock(signed.witness_lock, public_key)


def test_sign_sphincs_tx_dao_withdraw(test_ctx: TrezorTestContext):
    # Phase-2 withdrawal: the credited value (deposit + compensation) exceeds
    # the cell's plain capacity, so signing proves the headers were verified.
    session = _load_sphincs_session(test_ctx)
    lock_args, public_key = _sphincs_lock(session)

    deposit_number = 100
    deposit_capacity = 20000 * SHANNON

    deposit_header = _dao_header(deposit_number, AR_DEPOSIT)
    withdraw_header = _dao_header(200_000, AR_WITHDRAW, timestamp=1_576_852_800_000)
    header_deps = [
        prevtx.header_hash(deposit_header),
        prevtx.header_hash(withdraw_header),
    ]

    inp, prev_txs = _withdrawing_input(lock_args, deposit_number, deposit_capacity)

    occupied = prevtx.occupied_capacity(lock_args_len=32, type_args_len=0, data_len=8)
    max_withdraw = prevtx.dao_maximum_withdraw(
        deposit_capacity, occupied, AR_DEPOSIT, AR_WITHDRAW
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


def _expect_sign_failure(session, match, **kwargs):
    """Drive a signing flow that must fail with ``match``, confirming any screens
    shown on the way (the errors here surface after the output confirmations)."""
    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        with pytest.raises(TrezorFailure, match=match):
            ckb.sign_sphincs_tx(session, network="Mainnet", variant=VARIANT, **kwargs)


def test_sign_sphincs_tx_rejects_foreign_inputs(test_ctx: TrezorTestContext):
    # Nothing to sign: silently signing anyway would make the device a blind
    # oracle for a transaction it has no stake in.
    session = _load_sphincs_session(test_ctx)

    spent = _external_output(1000 * SHANNON)
    prev_hash = prevtx.raw_tx_hash([], [spent], [b""], [])
    _expect_sign_failure(
        session,
        "No input belongs to the signer",
        inputs=[ckb.create_cell_input(tx_hash=prev_hash, index=0)],
        outputs=[_external_output(1000 * SHANNON - 1000)],
        prev_txs={prev_hash: ckb.create_prev_tx(outputs=[spent])},
    )


def test_sign_sphincs_tx_rejects_wrong_sign_group(test_ctx: TrezorTestContext):
    # The claimed group (input 0) does not match where the signer's lock really
    # is (input 1); the host's witness layout was built for the wrong index.
    session = _load_sphincs_session(test_ctx)
    lock_args, _ = _sphincs_lock(session)

    spent = [_external_output(500 * SHANNON), _sphincs_cell(lock_args, 1000 * SHANNON)]
    prev_hash = prevtx.raw_tx_hash([], spent, [b"", b""], [])
    _expect_sign_failure(
        session,
        "do not match the signer's inputs",
        inputs=[
            ckb.create_cell_input(tx_hash=prev_hash, index=0),
            ckb.create_cell_input(tx_hash=prev_hash, index=1),
        ],
        outputs=[_external_output(1500 * SHANNON - 1000)],
        sign_group_input_indices=[0],
        prev_txs={prev_hash: ckb.create_prev_tx(outputs=spent)},
    )


def test_sign_sphincs_tx_rejects_short_input_hash(test_ctx: TrezorTestContext):
    # Exact message: a short hash is also caught later by _serialize_cell_input,
    # so a loose pattern would stay green with the early check deleted.
    session = _load_sphincs_session(test_ctx)
    with pytest.raises(TrezorFailure, match="previous_output_tx_hash must be 32 bytes"):
        ckb.sign_sphincs_tx(
            session,
            network="Mainnet",
            variant=VARIANT,
            inputs=[ckb.create_cell_input(tx_hash=b"\x11" * 31, index=0)],
            outputs=[_external_output(100 * SHANNON)],
        )


def test_sign_sphincs_tx_rejects_raw_signing_witness(test_ctx: TrezorTestContext):
    # A raw blob in the signing slot would leave the signed bytes
    # host-controlled; the device must build that witness itself.
    session = _load_sphincs_session(test_ctx)
    lock_args, _ = _sphincs_lock(session)
    inputs, outputs, prev_txs = _plain_transfer(lock_args)

    _expect_sign_failure(
        session,
        "Missing WitnessArgs for signing witness",
        inputs=inputs,
        outputs=outputs,
        witnesses=[ckb.create_witness_raw(b"\x00" * 10)],
        prev_txs=prev_txs,
    )


def test_sign_sphincs_tx_rejects_witness_args_outside_group(
    test_ctx: TrezorTestContext,
):
    session = _load_sphincs_session(test_ctx)
    lock_args, _ = _sphincs_lock(session)
    inputs, outputs, prev_txs = _plain_transfer(lock_args)

    _expect_sign_failure(
        session,
        "Unexpected WitnessArgs for non-signing witness",
        inputs=inputs,
        outputs=outputs,
        witnesses=[ckb.create_witness_args(), ckb.create_witness_args()],
        prev_txs=prev_txs,
    )


def test_sign_sphincs_tx_rejects_empty_witness_vector(test_ctx: TrezorTestContext):
    # witnesses_count = 0 leaves no slot for the signature itself.
    session = _load_sphincs_session(test_ctx)
    lock_args, _ = _sphincs_lock(session)
    inputs, outputs, prev_txs = _plain_transfer(lock_args)

    _expect_sign_failure(
        session,
        "Signing witness index out of range",
        inputs=inputs,
        outputs=outputs,
        witnesses=[],
        prev_txs=prev_txs,
    )


def test_sign_sphincs_tx_rejects_tampered_dao_header(test_ctx: TrezorTestContext):
    # A host inflating compensation: the served withdraw header does not hash to
    # the committed header_deps entry.
    session = _load_sphincs_session(test_ctx)
    lock_args, _ = _sphincs_lock(session)

    deposit_number = 100
    honest_deposit = _dao_header(deposit_number, AR_DEPOSIT)
    honest_withdraw = _dao_header(200_000, AR_WITHDRAW)
    lying_withdraw = _dao_header(200_000, 99_000_000_000_000_000)
    inp, prev_txs = _withdrawing_input(lock_args, deposit_number, 20000 * SHANNON)

    _expect_sign_failure(
        session,
        "header hash mismatch",
        inputs=[inp],
        outputs=[_external_output(20100 * SHANNON)],
        witnesses=_phase2_witnesses(),
        prev_txs=prev_txs,
        header_deps=[
            prevtx.header_hash(honest_deposit),
            prevtx.header_hash(honest_withdraw),
        ],
        headers=[honest_deposit, lying_withdraw],
    )
