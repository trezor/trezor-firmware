import pytest

from trezorlib import ckb, messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures
from ...input_flows import InputFlowConfirmAllWarnings
from . import prevtx

pytestmark = [pytest.mark.altcoin, pytest.mark.ckb, pytest.mark.models("t3w1")]

# blake160 of the public key at m/44'/309'/0'/0/0, the signer in every test here.
SENDER_LOCK_ARGS = bytes.fromhex("0af9cea353cca00eb173c7420547e358aead128f")

SHANNON = 100_000_000
DAO_CODE_HASH = "82d76d1b75fe2fd9a27dfbaa65a039221a380d76c926f378d3f81cf3e7e13f2e"
# Accumulated rates of the deposit and withdraw blocks: +0.5 % compensation.
AR_DEPOSIT = 10_000_000_000_000_000
AR_WITHDRAW = 10_050_000_000_000_000


def _dao_header(number, ar, timestamp=1_573_852_800_000):
    """A block header carrying ``ar`` in its dao field; only number/AR matter here."""
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


def _default_witnesses(inputs_count: int) -> list[bytes]:
    """The witness vector trezorlib sends when the caller passes none: the
    signing WitnessArgs with its 65-byte lock blanked, then empty raw witnesses."""
    return [prevtx.build_witness_args(65)] + [b""] * (inputs_count - 1)


def assert_signature_covers_sighash(
    resp, witnesses=None, group_indices=None, inputs_count=1
):
    """The device must sign sighash_all of the transaction it hashed.

    The tx hash alone says nothing about the digest that was signed, so this
    recomputes sighash_all on the host and recovers the signer from the
    signature. Only a device that hashed the same witnesses, blanked the same
    lock and converted the recovery byte the same way recovers to the signer's
    lock args.
    """
    if witnesses is None:
        witnesses = _default_witnesses(inputs_count)
    if group_indices is None:
        group_indices = list(range(inputs_count))

    sighash = prevtx.sighash_all(
        bytes(resp.serialized.tx_hash), witnesses, group_indices, inputs_count
    )
    recovered = prevtx.recover_lock_args(bytes(resp.serialized.signature), sighash)
    assert recovered == SENDER_LOCK_ARGS, "signature does not cover sighash_all"


def _build_outputs(parameters):
    return [
        ckb.create_cell_output(
            capacity=out["capacity"],
            lock_code_hash=out["lock_code_hash"],
            lock_hash_type=out["lock_hash_type"],
            lock_args=out["lock_args"],
            type_code_hash=out.get("type_code_hash"),
            type_hash_type=out.get("type_hash_type"),
            type_args=out.get("type_args"),
            data=(
                bytes.fromhex(out["data"].removeprefix("0x"))
                if out.get("data")
                else None
            ),
        )
        for out in parameters["outputs"]
    ]


def _outputs_data(outputs):
    return [bytes(o.data) if o.data else b"" for o in outputs]


def _build_sign_tx_components(parameters):
    """Build a signable tx whose inputs are backed by synthetic previous txs.

    The device verifies input capacities by re-hashing each previous tx, so we
    synthesize a previous tx per input and point the input's OutPoint at it. The
    capacities are chosen so the verified fee equals the fixture's declared fee.
    """
    address_n = parse_path(parameters["path"])
    network = parameters.get("network", "Mainnet")

    outputs = _build_outputs(parameters)
    cell_deps = [
        ckb.create_cell_dep(
            tx_hash=dep["tx_hash"],
            index=dep["index"],
            dep_type=dep["dep_type"],
        )
        for dep in parameters.get("cell_deps", [])
    ]

    fee = parameters.get("fee")
    total_out = sum(o.capacity for o in outputs)
    total_in_needed = total_out + (fee or 0)

    raw_inputs = parameters["inputs"]
    n = len(raw_inputs)
    # First input covers the bulk; the rest carry 1 shannon each so every input
    # references a distinct, positive-capacity previous output.
    caps = [total_in_needed - (n - 1)] + [1] * (n - 1)

    inputs = []
    prev_txs = {}
    for i, (raw, cap) in enumerate(zip(raw_inputs, caps)):
        prev, prev_hash = prevtx.synth_prev_tx([cap], salt=i)
        prev_txs[prev_hash] = prev
        inputs.append(
            ckb.create_cell_input(tx_hash=prev_hash, index=0, since=raw.get("since", 0))
        )

    return address_n, network, inputs, outputs, cell_deps, prev_txs


@parametrize_using_common_fixtures("ckb/sign_tx.json")
def test_sign_tx(session: Session, parameters, result):
    address_n, network, inputs, outputs, cell_deps, prev_txs = (
        _build_sign_tx_components(parameters)
    )

    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())

        resp = ckb.sign_tx(
            session,
            address_n,
            inputs=inputs,
            outputs=outputs,
            cell_deps=cell_deps,
            network=network,
            chunkify=True,
            prev_txs=prev_txs,
        )

    sig = resp.serialized.signature
    tx_hash = resp.serialized.tx_hash

    assert sig is not None
    assert tx_hash is not None
    assert len(sig) == 65
    assert len(tx_hash) == 32

    expected = prevtx.raw_tx_hash(inputs, outputs, _outputs_data(outputs), cell_deps)
    assert tx_hash == expected
    # The recorded hash keeps the synthesized inputs from quietly changing.
    assert tx_hash.hex() == result["tx_hash"]

    assert_signature_covers_sighash(resp, inputs_count=len(inputs))


def test_sign_tx_streaming_protocol(session: Session):
    parameters = {
        "path": "m/44'/309'/0'/0/0",
        "network": "Mainnet",
        "inputs": [{"since": 0}, {"since": 0}],
        "outputs": [
            {
                "capacity": 10000000000,
                "lock_code_hash": "9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
                "lock_hash_type": 1,
                "lock_args": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            },
            {
                "capacity": 20000000000,
                "lock_code_hash": "9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
                "lock_hash_type": 1,
                "lock_args": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            },
        ],
        "cell_deps": [
            {
                "tx_hash": "3333333333333333333333333333333333333333333333333333333333333333",
                "index": 0,
                "dep_type": 1,
            },
        ],
        "fee": 1000,
    }
    address_n, network, inputs, outputs, cell_deps, prev_txs = (
        _build_sign_tx_components(parameters)
    )

    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())

        witnesses = [ckb.create_witness_args(), ckb.create_witness_raw()]

        res = session.call(
            messages.CKBSignTx(
                address_n=address_n,
                network=network,
                inputs_count=len(inputs),
                outputs_count=len(outputs),
                cell_deps_count=len(cell_deps),
                witnesses_count=len(witnesses),
                sign_group_input_indices=list(range(len(inputs))),
                chunkify=True,
            ),
            expect=messages.CKBTxRequest,
        )

        RT = messages.CKBTxRequestType
        seen = []
        while res.request_type != RT.TXFINISHED:
            assert res.details is not None
            rt = res.request_type
            seen.append(rt)
            idx = res.details.request_index
            if rt == RT.TXINPUT:
                ack = messages.CKBTxAckInput(input=inputs[idx])
            elif rt == RT.TXOUTPUT:
                ack = messages.CKBTxAckOutput(output=outputs[idx])
            elif rt == RT.TXCELLDEP:
                ack = messages.CKBTxAckCellDep(cell_dep=cell_deps[idx])
            elif rt == RT.TXWITNESS:
                ack = witnesses[idx]
            elif rt == RT.TXPREVMETA:
                prev = prev_txs[bytes(res.details.tx_hash)]
                ack = messages.CKBTxAckPrevMeta(
                    version=prev.version,
                    inputs_count=len(prev.inputs),
                    outputs_count=len(prev.outputs),
                    cell_deps_count=len(prev.cell_deps),
                    header_deps=prev.header_deps,
                )
            elif rt == RT.TXPREVINPUT:
                prev = prev_txs[bytes(res.details.tx_hash)]
                ack = messages.CKBTxAckInput(input=prev.inputs[idx])
            elif rt == RT.TXPREVOUTPUT:
                prev = prev_txs[bytes(res.details.tx_hash)]
                ack = messages.CKBTxAckOutput(output=prev.outputs[idx])
            elif rt == RT.TXPREVCELLDEP:
                prev = prev_txs[bytes(res.details.tx_hash)]
                ack = messages.CKBTxAckCellDep(cell_dep=prev.cell_deps[idx])
            else:
                raise AssertionError(f"unexpected request type {rt}")
            res = session.call(ack, expect=messages.CKBTxRequest)

    # Previous txs are verified before the witnesses are requested.
    assert seen.index(RT.TXPREVMETA) < seen.index(RT.TXWITNESS)
    assert RT.TXPREVOUTPUT in seen

    assert res.details is None
    assert res.serialized is not None
    assert len(res.serialized.tx_hash) == 32
    assert_signature_covers_sighash(res, inputs_count=2)


def test_sign_tx_signs_a_non_trivial_witness_structure(session: Session):
    # A signing group not starting at input 0, a trailing witness, and non-empty
    # type slices: the parts of sighash_all no plain transfer reaches.
    outputs = _build_outputs(
        {
            "outputs": [
                {
                    "capacity": 10000000000,
                    "lock_code_hash": "9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
                    "lock_hash_type": 1,
                    "lock_args": "abcdef0123456789abcdef0123456789abcdef01",
                }
            ]
        }
    )
    fee = 1000
    prev_a, hash_a = prevtx.synth_prev_tx([6_000_000_000], salt=0)
    prev_b, hash_b = prevtx.synth_prev_tx([4_000_000_000 + fee], salt=1)
    inputs = [
        ckb.create_cell_input(tx_hash=hash_a, index=0),
        ckb.create_cell_input(tx_hash=hash_b, index=0),
    ]

    input_type = b"\x07" * 8
    output_type = b"\x09" * 3
    leading = b"\xa1" * 4
    trailing = b"\xb2" * 6
    witnesses = [
        ckb.create_witness_raw(leading),
        ckb.create_witness_args(input_type=input_type, output_type=output_type),
        ckb.create_witness_raw(trailing),
    ]

    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        resp = ckb.sign_tx(
            session,
            parse_path("m/44h/309h/0h/0/0"),
            inputs=inputs,
            outputs=outputs,
            network="Mainnet",
            prev_txs={hash_a: prev_a, hash_b: prev_b},
            witnesses=witnesses,
            sign_group_input_indices=[1],
        )

    assert resp.serialized.tx_hash == prevtx.raw_tx_hash(
        inputs, outputs, _outputs_data(outputs), []
    )
    assert_signature_covers_sighash(
        resp,
        witnesses=[
            leading,
            prevtx.build_witness_args(
                65, input_type=input_type, output_type=output_type
            ),
            trailing,
        ],
        group_indices=[1],
        inputs_count=2,
    )


def test_sign_tx_verifies_a_previous_tx_with_inputs_and_cell_deps(session: Session):
    # Previous txs elsewhere carry outputs only, so TXPREVINPUT/TXPREVCELLDEP
    # are never requested; a real funding tx commits both in its hash.
    spent = ckb.create_cell_output(
        capacity=10_000_000_000 + 1000,  # output + fee
        lock_code_hash=prevtx.LOCK_CODE_HASH,
        lock_hash_type=1,
        lock_args="22" * 20,
    )
    prev_inputs = [ckb.create_cell_input(tx_hash="33" * 32, index=7, since=42)]
    prev_cell_deps = [ckb.create_cell_dep(tx_hash="44" * 32, index=1, dep_type=0)]
    prev_hash = prevtx.raw_tx_hash(prev_inputs, [spent], [b""], prev_cell_deps)
    prev = ckb.create_prev_tx(
        outputs=[spent], inputs=prev_inputs, cell_deps=prev_cell_deps
    )

    inputs = [ckb.create_cell_input(tx_hash=prev_hash, index=0)]
    outputs = _build_outputs(
        {
            "outputs": [
                {
                    "capacity": 10000000000,
                    "lock_code_hash": "9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
                    "lock_hash_type": 1,
                    "lock_args": "abcdef0123456789abcdef0123456789abcdef01",
                }
            ]
        }
    )

    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        resp = ckb.sign_tx(
            session,
            parse_path("m/44h/309h/0h/0/0"),
            inputs=inputs,
            outputs=outputs,
            network="Mainnet",
            prev_txs={prev_hash: prev},
        )

    assert resp.serialized.tx_hash == prevtx.raw_tx_hash(
        inputs, outputs, _outputs_data(outputs), []
    )
    assert_signature_covers_sighash(resp)


def test_sign_tx_with_header_deps(session: Session):
    # header_deps are a Byte32Vec field of the RawTransaction and are committed
    # in its hash (e.g. Nervos DAO withdrawals reference the deposit/withdraw
    # block headers). The device must hash them, otherwise its tx_hash — and the
    # signature over it — would not match the transaction the host broadcasts.
    parameters = {
        "path": "m/44'/309'/0'/0/0",
        "network": "Mainnet",
        "inputs": [{"since": 0}],
        "outputs": [
            {
                "capacity": 10000000000,
                "lock_code_hash": "9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
                "lock_hash_type": 1,
                "lock_args": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            },
        ],
        "fee": 1000,
    }
    address_n, network, inputs, outputs, cell_deps, prev_txs = (
        _build_sign_tx_components(parameters)
    )
    header_deps = [bytes.fromhex("11" * 32), bytes.fromhex("22" * 32)]

    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())

        resp = ckb.sign_tx(
            session,
            address_n,
            inputs=inputs,
            outputs=outputs,
            cell_deps=cell_deps,
            network=network,
            prev_txs=prev_txs,
            header_deps=header_deps,
        )

    tx_hash = resp.serialized.tx_hash
    outputs_data = _outputs_data(outputs)

    # The device commits exactly the header_deps we passed...
    expected = prevtx.raw_tx_hash(
        inputs, outputs, outputs_data, cell_deps, header_deps=header_deps
    )
    assert tx_hash == expected

    # ...and the hash genuinely depends on them: dropping the header_deps yields a
    # different tx hash, proving the field is not silently ignored.
    without = prevtx.raw_tx_hash(inputs, outputs, outputs_data, cell_deps)
    assert tx_hash != without

    assert_signature_covers_sighash(resp, inputs_count=len(inputs))


def test_sign_tx_dao_withdraw(session: Session):
    # A Nervos DAO phase-2 withdrawal: the input is a withdrawing cell whose
    # unlocked value (deposit + compensation) exceeds its plain capacity, so the
    # single output is LARGER than the input capacity. The device must accept it
    # by verifying the deposit/withdraw block headers and crediting the
    # compensation, instead of rejecting with "Inputs do not cover outputs".
    deposit_number = 100
    withdraw_number = 200_000

    deposit_header = _dao_header(deposit_number, AR_DEPOSIT)
    withdraw_header = _dao_header(withdraw_number, AR_WITHDRAW, 1_576_852_800_000)
    headers = [deposit_header, withdraw_header]
    header_deps = [
        prevtx.header_hash(deposit_header),
        prevtx.header_hash(withdraw_header),
    ]

    # The spent cell is a DAO withdrawing cell (DAO type script, data = deposit
    # block number) with 20000 CKB of capacity.
    deposit_capacity = 20000 * SHANNON
    cell_data = deposit_number.to_bytes(8, "little")
    withdrawing_cell = ckb.create_cell_output(
        capacity=deposit_capacity,
        lock_code_hash=prevtx.LOCK_CODE_HASH,
        lock_hash_type=1,
        lock_args="11" * 20,
        type_code_hash=DAO_CODE_HASH,
        type_hash_type=1,
        type_args=b"",
        data=cell_data,
    )
    prev = ckb.create_prev_tx(outputs=[withdrawing_cell])
    prev_hash = prevtx.raw_tx_hash([], [withdrawing_cell], [cell_data], [])

    inp = ckb.create_cell_input(
        tx_hash=prev_hash,
        index=0,
        dao_deposit_header_index=0,
        dao_withdraw_header_index=1,
    )

    # Max withdraw the device should credit (RFC 0023), via the same helper the
    # chain-anchored golden test pins to real data.
    occupied = prevtx.occupied_capacity(lock_args_len=20, type_args_len=0, data_len=8)
    max_withdraw = prevtx.dao_maximum_withdraw(
        deposit_capacity, occupied, AR_DEPOSIT, AR_WITHDRAW
    )
    fee = 1000
    out_capacity = max_withdraw - fee
    assert out_capacity > deposit_capacity

    output = ckb.create_cell_output(
        capacity=out_capacity,
        lock_code_hash=prevtx.LOCK_CODE_HASH,
        lock_hash_type=1,
        lock_args="aa" * 20,
    )

    # The DAO type script reads the deposit header's index in header_deps from
    # the witness, so a phase-2 withdrawal always carries it.
    deposit_index = (0).to_bytes(8, "little")
    witnesses = [ckb.create_witness_args(input_type=deposit_index)]

    address_n = parse_path("m/44'/309'/0'/0/0")
    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())

        resp = ckb.sign_tx(
            session,
            address_n,
            inputs=[inp],
            outputs=[output],
            cell_deps=[],
            network="Mainnet",
            prev_txs={prev_hash: prev},
            header_deps=header_deps,
            headers=headers,
            witnesses=witnesses,
        )

    expected = prevtx.raw_tx_hash([inp], [output], [b""], [], header_deps=header_deps)
    assert resp.serialized.tx_hash == expected
    assert_signature_covers_sighash(
        resp,
        witnesses=[prevtx.build_witness_args(65, input_type=deposit_index)],
        group_indices=[0],
        inputs_count=1,
    )

    # Bound the credited compensation from above as well: spending one shannon
    # more than the maximum withdraw must be refused.
    too_much = ckb.create_cell_output(
        capacity=max_withdraw + 1,
        lock_code_hash=prevtx.LOCK_CODE_HASH,
        lock_hash_type=1,
        lock_args="aa" * 20,
    )
    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        with pytest.raises(TrezorFailure, match="Inputs do not cover outputs"):
            ckb.sign_tx(
                session,
                address_n,
                inputs=[inp],
                outputs=[too_much],
                cell_deps=[],
                network="Mainnet",
                prev_txs={prev_hash: prev},
                header_deps=header_deps,
                headers=headers,
                witnesses=witnesses,
            )


def test_sign_tx_rejects_dao_withdraw_tampered_header(session: Session):
    # The device must reject a DAO withdrawal whose supplied header does not hash
    # to the committed header_deps entry (a host inflating the compensation).
    deposit_number = 100

    honest_deposit = _dao_header(deposit_number, AR_DEPOSIT)
    honest_withdraw = _dao_header(200_000, AR_WITHDRAW)
    header_deps = [
        prevtx.header_hash(honest_deposit),
        prevtx.header_hash(honest_withdraw),
    ]
    # Host lies: serves a withdraw header with a much higher AR than the one whose
    # hash is committed in header_deps.
    lying_withdraw = _dao_header(200_000, 99_000_000_000_000_000)
    headers = [honest_deposit, lying_withdraw]

    cell_data = deposit_number.to_bytes(8, "little")
    withdrawing_cell = ckb.create_cell_output(
        capacity=20000 * SHANNON,
        lock_code_hash=prevtx.LOCK_CODE_HASH,
        lock_hash_type=1,
        lock_args="11" * 20,
        type_code_hash=DAO_CODE_HASH,
        type_hash_type=1,
        type_args=b"",
        data=cell_data,
    )
    prev = ckb.create_prev_tx(outputs=[withdrawing_cell])
    prev_hash = prevtx.raw_tx_hash([], [withdrawing_cell], [cell_data], [])
    inp = ckb.create_cell_input(
        tx_hash=prev_hash,
        index=0,
        dao_deposit_header_index=0,
        dao_withdraw_header_index=1,
    )
    output = ckb.create_cell_output(
        capacity=20100 * SHANNON,
        lock_code_hash=prevtx.LOCK_CODE_HASH,
        lock_hash_type=1,
        lock_args="aa" * 20,
    )

    address_n = parse_path("m/44'/309'/0'/0/0")
    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())

        with pytest.raises(TrezorFailure, match="header hash mismatch"):
            ckb.sign_tx(
                session,
                address_n,
                inputs=[inp],
                outputs=[output],
                cell_deps=[],
                network="Mainnet",
                prev_txs={prev_hash: prev},
                header_deps=header_deps,
                headers=headers,
            )


def test_sign_tx_dao_withdraw_credits_the_highest_header_rate(session: Session):
    # The device cannot know which header_dep is the withdrawing cell's block, so
    # it must credit the highest rate among headers after the deposit whichever
    # index the host names: real withdraw block (+20 %) at 1, decoy (+0.01 %) at 2.
    deposit_number = 100
    ar_real = AR_DEPOSIT * 120 // 100
    ar_decoy = AR_DEPOSIT * 10001 // 10000
    headers = [
        _dao_header(deposit_number, AR_DEPOSIT),
        _dao_header(200_000, ar_real, 1_576_852_800_000),
        _dao_header(150_000, ar_decoy, 1_575_852_800_000),
    ]
    header_deps = [prevtx.header_hash(h) for h in headers]

    deposit_capacity = 20000 * SHANNON
    cell_data = deposit_number.to_bytes(8, "little")
    withdrawing_cell = ckb.create_cell_output(
        capacity=deposit_capacity,
        lock_code_hash=prevtx.LOCK_CODE_HASH,
        lock_hash_type=1,
        lock_args="11" * 20,
        type_code_hash=DAO_CODE_HASH,
        type_hash_type=1,
        type_args=b"",
        data=cell_data,
    )
    prev = ckb.create_prev_tx(outputs=[withdrawing_cell])
    prev_hash = prevtx.raw_tx_hash([], [withdrawing_cell], [cell_data], [])
    occupied = prevtx.occupied_capacity(lock_args_len=20, type_args_len=0, data_len=8)
    max_withdraw = prevtx.dao_maximum_withdraw(
        deposit_capacity, occupied, AR_DEPOSIT, ar_real
    )
    witnesses = [ckb.create_witness_args(input_type=(0).to_bytes(8, "little"))]
    address_n = parse_path("m/44'/309'/0'/0/0")

    def _sign(withdraw_index: int, out_capacity: int, screens: list[str]):
        inp = ckb.create_cell_input(
            tx_hash=prev_hash,
            index=0,
            dao_deposit_header_index=0,
            dao_withdraw_header_index=withdraw_index,
        )
        output = ckb.create_cell_output(
            capacity=out_capacity,
            lock_code_hash=prevtx.LOCK_CODE_HASH,
            lock_hash_type=1,
            lock_args="aa" * 20,
        )
        with session.test_ctx as client:
            if not session.debug.legacy_debug:
                client.set_input_flow(
                    InputFlowConfirmAllWarnings(
                        client,
                        on_page=lambda layout: screens.append(layout.text_content()),
                    ).get()
                )
            return ckb.sign_tx(
                session,
                address_n,
                inputs=[inp],
                outputs=[output],
                cell_deps=[],
                network="Mainnet",
                prev_txs={prev_hash: prev},
                header_deps=header_deps,
                headers=headers,
                witnesses=witnesses,
            )

    # Up to the real maximum is accepted even when the host names the decoy...
    _sign(2, max_withdraw - 1000, [])

    # ...and the fee shown is the real one: leaving the whole compensation as fee
    # triggers the high-fee warning for either index.
    for withdraw_index in (1, 2):
        screens: list[str] = []
        _sign(withdraw_index, 20001 * SHANNON, screens)
        assert any(
            "unusually high" in screen for screen in screens
        ), f"index {withdraw_index}: fee understated; screens: {screens}"


def test_sign_tx_rejects_tampered_prev_tx(session: Session):
    # The host claims an input OutPoint but supplies a previous tx that hashes to
    # something else (here: a different capacity). The device must refuse.
    outputs = _build_outputs(
        {
            "outputs": [
                {
                    "capacity": 10000000000,
                    "lock_code_hash": "9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
                    "lock_hash_type": 1,
                    "lock_args": "abcdef0123456789abcdef0123456789abcdef01",
                }
            ]
        }
    )
    _, claimed_hash = prevtx.synth_prev_tx([10000001000])
    tampered_prev, _ = prevtx.synth_prev_tx([99999999999])
    inputs = [ckb.create_cell_input(tx_hash=claimed_hash, index=0)]

    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        with pytest.raises(TrezorFailure, match="Previous transaction hash mismatch"):
            ckb.sign_tx(
                session,
                parse_path("m/44h/309h/0h/0/0"),
                inputs=inputs,
                outputs=outputs,
                network="Mainnet",
                chunkify=True,
                prev_txs={claimed_hash: tampered_prev},
            )


def test_sign_tx_rejects_inputs_below_outputs(session: Session):
    outputs = _build_outputs(
        {
            "outputs": [
                {
                    "capacity": 10000000000,
                    "lock_code_hash": "9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
                    "lock_hash_type": 1,
                    "lock_args": "abcdef0123456789abcdef0123456789abcdef01",
                }
            ]
        }
    )
    prev, prev_hash = prevtx.synth_prev_tx([9000000000])
    inputs = [ckb.create_cell_input(tx_hash=prev_hash, index=0)]

    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        with pytest.raises(TrezorFailure, match="Inputs do not cover outputs"):
            ckb.sign_tx(
                session,
                parse_path("m/44h/309h/0h/0/0"),
                inputs=inputs,
                outputs=outputs,
                network="Mainnet",
                chunkify=True,
                prev_txs={prev_hash: prev},
            )


def test_sign_tx_high_fee_warns_and_signs(session: Session):
    outputs = _build_outputs(
        {
            "outputs": [
                {
                    "capacity": 10000000000,
                    "lock_code_hash": "9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
                    "lock_hash_type": 1,
                    "lock_args": "abcdef0123456789abcdef0123456789abcdef01",
                }
            ]
        }
    )
    fee = 5000000000  # 50 % of the sent amount
    prev, prev_hash = prevtx.synth_prev_tx([10000000000 + fee])
    inputs = [ckb.create_cell_input(tx_hash=prev_hash, index=0)]

    # InputFlowConfirmAllWarnings also passes when no warning appears at all, so
    # the screens are recorded and the warning text is required among them.
    screens: list[str] = []

    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(
                InputFlowConfirmAllWarnings(
                    client, on_page=lambda layout: screens.append(layout.text_content())
                ).get()
            )
        resp = ckb.sign_tx(
            session,
            parse_path("m/44h/309h/0h/0/0"),
            inputs=inputs,
            outputs=outputs,
            network="Mainnet",
            chunkify=True,
            prev_txs={prev_hash: prev},
        )

    assert any(
        "unusually high" in screen for screen in screens
    ), f"high-fee warning was not shown; screens: {screens}"
    assert_signature_covers_sighash(resp)


def test_sign_tx_invalid_path(session: Session):
    inputs = [
        ckb.create_cell_input(
            tx_hash="d7aa3d44cd6e05823e9b76e4f74932545707832785e3a8ed92b7e409f46c18ac",
            index=0,
        )
    ]
    outputs = [
        ckb.create_cell_output(
            capacity=10000000000,
            lock_code_hash="9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
            lock_hash_type=1,
            lock_args="abcdef0123456789abcdef0123456789abcdef01",
        )
    ]

    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        ckb.sign_tx(
            session,
            parse_path("m/44h/999h/0h/0/0"),
            inputs=inputs,
            outputs=outputs,
            network="Mainnet",
            chunkify=True,
        )


def test_rejects_invalid_network(session: Session):
    inputs = [
        ckb.create_cell_input(
            tx_hash="d7aa3d44cd6e05823e9b76e4f74932545707832785e3a8ed92b7e409f46c18ac",
            index=0,
        )
    ]
    outputs = [
        ckb.create_cell_output(
            capacity=10000000000,
            lock_code_hash="9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
            lock_hash_type=1,
            lock_args="abcdef0123456789abcdef0123456789abcdef01",
        )
    ]

    with pytest.raises(TrezorFailure, match="Invalid CKB network"):
        ckb.sign_tx(
            session,
            parse_path("m/44h/309h/0h/0/0"),
            inputs=inputs,
            outputs=outputs,
            network="Devnet",
            chunkify=True,
        )


MAINNET_SECP_DEP_GROUP = (
    "71a7ba8fc96349fea0ed3a5c47992e3b4084b031a42264a018e0072e8172e46c"
)
TESTNET_SECP_DEP_GROUP = (
    "f8de3bb47d055cdf460d93a2a6e1b05f7432f9777c8c474abf4eec1d4aee5d37"
)


def _network_binding_case(network: str, dep_tx_hash: str | None):
    outputs = [
        ckb.create_cell_output(
            capacity=10_000_000_000,
            lock_code_hash=prevtx.LOCK_CODE_HASH,
            lock_hash_type=1,
            lock_args="ab" * 20,
        )
    ]
    prev, prev_hash = prevtx.synth_prev_tx([10_000_001_000])
    inputs = [ckb.create_cell_input(tx_hash=prev_hash, index=0)]
    cell_deps = (
        [ckb.create_cell_dep(tx_hash=dep_tx_hash, index=0, dep_type=1)]
        if dep_tx_hash
        else []
    )
    return dict(
        inputs=inputs,
        outputs=outputs,
        cell_deps=cell_deps,
        network=network,
        prev_txs={prev_hash: prev},
    )


@pytest.mark.parametrize(
    "network,dep_tx_hash",
    [
        # A dep on the other network's genesis gives the deception away: signing
        # a Mainnet-spending tx under a "Testnet" confirmation, or vice versa.
        pytest.param(
            "Testnet", MAINNET_SECP_DEP_GROUP, id="testnet-claims-mainnet-dep"
        ),
        pytest.param(
            "Mainnet", TESTNET_SECP_DEP_GROUP, id="mainnet-claims-testnet-dep"
        ),
    ],
)
def test_sign_tx_rejects_contradicting_genesis_dep(session, network, dep_tx_hash):
    other = "Mainnet" if network == "Testnet" else "Testnet"
    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        with pytest.raises(TrezorFailure, match=f"reference the CKB {other} genesis"):
            ckb.sign_tx(
                session,
                parse_path("m/44h/309h/0h/0/0"),
                **_network_binding_case(network, dep_tx_hash),
            )


@pytest.mark.parametrize(
    "network,dep_tx_hash",
    [
        ("Mainnet", MAINNET_SECP_DEP_GROUP),
        ("Testnet", TESTNET_SECP_DEP_GROUP),
        ("Testnet", None),  # no genesis dep is not a contradiction: still signs
    ],
)
def test_sign_tx_signs_when_no_dep_contradicts_the_network(
    session, network, dep_tx_hash
):
    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        resp = ckb.sign_tx(
            session,
            parse_path("m/44h/309h/0h/0/0"),
            **_network_binding_case(network, dep_tx_hash),
        )
    assert_signature_covers_sighash(resp)


def test_sign_tx_invalid_input_tx_hash_length(session: Session):
    inputs = [
        ckb.create_cell_input(
            tx_hash="d7aa3d44cd6e05823e9b76e4f74932545707832785e3a8ed",
            index=0,
        )
    ]
    outputs = [
        ckb.create_cell_output(
            capacity=10000000000,
            lock_code_hash="9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
            lock_hash_type=1,
            lock_args="abcdef0123456789abcdef0123456789abcdef01",
        )
    ]

    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        with pytest.raises(TrezorFailure, match="CellInput tx_hash must be 32 bytes"):
            ckb.sign_tx(
                session,
                parse_path("m/44h/309h/0h/0/0"),
                inputs=inputs,
                outputs=outputs,
                network="Mainnet",
                chunkify=True,
            )


def test_sign_tx_invalid_output_code_hash_length(session: Session):
    inputs = [
        ckb.create_cell_input(
            tx_hash="d7aa3d44cd6e05823e9b76e4f74932545707832785e3a8ed92b7e409f46c18ac",
            index=0,
        )
    ]
    outputs = [
        ckb.create_cell_output(
            capacity=10000000000,
            lock_code_hash="9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d",
            lock_hash_type=1,
            lock_args="abcdef0123456789abcdef0123456789abcdef01",
        )
    ]

    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        with pytest.raises(TrezorFailure, match="Script code_hash must be 32 bytes"):
            ckb.sign_tx(
                session,
                parse_path("m/44h/309h/0h/0/0"),
                inputs=inputs,
                outputs=outputs,
                network="Mainnet",
                chunkify=True,
            )


def test_sign_tx_invalid_cell_dep_tx_hash_length(session: Session):
    inputs = [
        ckb.create_cell_input(
            tx_hash="d7aa3d44cd6e05823e9b76e4f74932545707832785e3a8ed92b7e409f46c18ac",
            index=0,
        )
    ]
    outputs = [
        ckb.create_cell_output(
            capacity=10000000000,
            lock_code_hash="9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
            lock_hash_type=1,
            lock_args="abcdef0123456789abcdef0123456789abcdef01",
        )
    ]
    cell_deps = [
        ckb.create_cell_dep(
            tx_hash="f8de3bb47d055cdf460d93a2a6e1b05f7432f9777c8c474abf4eec1d",
            index=0,
            dep_type=1,
        )
    ]

    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        with pytest.raises(TrezorFailure, match="CellDep tx_hash must be 32 bytes"):
            ckb.sign_tx(
                session,
                parse_path("m/44h/309h/0h/0/0"),
                inputs=inputs,
                outputs=outputs,
                cell_deps=cell_deps,
                network="Mainnet",
                chunkify=True,
            )


def test_sign_tx_zero_inputs(session: Session):
    outputs = [
        ckb.create_cell_output(
            capacity=10000000000,
            lock_code_hash="9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
            lock_hash_type=1,
            lock_args="abcdef0123456789abcdef0123456789abcdef01",
        )
    ]

    with pytest.raises(TrezorFailure, match="Transaction must have at least one input"):
        ckb.sign_tx(
            session,
            parse_path("m/44h/309h/0h/0/0"),
            inputs=[],
            outputs=outputs,
            network="Mainnet",
            chunkify=True,
        )


def test_sign_tx_zero_outputs(session: Session):
    inputs = [
        ckb.create_cell_input(
            tx_hash="d7aa3d44cd6e05823e9b76e4f74932545707832785e3a8ed92b7e409f46c18ac",
            index=0,
        )
    ]

    with pytest.raises(
        TrezorFailure, match="Transaction must have at least one output"
    ):
        ckb.sign_tx(
            session,
            parse_path("m/44h/309h/0h/0/0"),
            inputs=inputs,
            outputs=[],
            network="Mainnet",
            chunkify=True,
        )


_TRANSFER_CAPACITY = 10_000_000_000
_TRANSFER_FEE = 1000


def _transfer_components(n_inputs=1):
    """A one-output transfer funded by ``n_inputs`` synthetic previous txs."""
    outputs = [
        ckb.create_cell_output(
            capacity=_TRANSFER_CAPACITY,
            lock_code_hash=prevtx.LOCK_CODE_HASH,
            lock_hash_type=1,
            lock_args="ab" * 20,
        )
    ]
    caps = [_TRANSFER_CAPACITY + _TRANSFER_FEE - (n_inputs - 1)] + [1] * (n_inputs - 1)
    inputs = []
    prev_txs = {}
    for i, cap in enumerate(caps):
        prev, prev_hash = prevtx.synth_prev_tx([cap], salt=i)
        prev_txs[prev_hash] = prev
        inputs.append(ckb.create_cell_input(tx_hash=prev_hash, index=0))
    return inputs, outputs, prev_txs


def _expect_sign_failure(session, match, inputs, outputs, prev_txs, **kwargs):
    """Drive an ECDSA signing flow that must fail with ``match``, confirming the
    output screens shown before the error surfaces."""
    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        with pytest.raises(TrezorFailure, match=match):
            ckb.sign_tx(
                session,
                parse_path("m/44h/309h/0h/0/0"),
                inputs=inputs,
                outputs=outputs,
                network="Mainnet",
                prev_txs=prev_txs,
                **kwargs,
            )


def test_sign_tx_rejects_duplicate_input_outpoint(session: Session):
    # Consensus refuses it; the device must not credit the cell twice.
    prev, prev_hash = prevtx.synth_prev_tx([10_000_000_000])
    inputs = [
        ckb.create_cell_input(tx_hash=prev_hash, index=0),
        ckb.create_cell_input(tx_hash=prev_hash, index=0),
    ]
    outputs = [
        ckb.create_cell_output(
            capacity=19_000_000_000,
            lock_code_hash=prevtx.LOCK_CODE_HASH,
            lock_hash_type=1,
            lock_args="ab" * 20,
        )
    ]
    _expect_sign_failure(
        session, "Duplicate input outpoint", inputs, outputs, {prev_hash: prev}
    )


def test_sign_tx_rejects_duplicate_sign_group_indices(session: Session):
    inputs, outputs, prev_txs = _transfer_components(n_inputs=2)
    _expect_sign_failure(
        session,
        "sorted and unique",
        inputs,
        outputs,
        prev_txs,
        sign_group_input_indices=[0, 0],
    )


def test_sign_tx_rejects_out_of_range_group_index(session: Session):
    inputs, outputs, prev_txs = _transfer_components(n_inputs=2)
    _expect_sign_failure(
        session,
        "Signing group index out of range",
        inputs,
        outputs,
        prev_txs,
        sign_group_input_indices=[0, 5],
    )


def test_sign_tx_rejects_empty_witness_vector(session: Session):
    # witnesses_count = 0 leaves no slot for the signature itself.
    inputs, outputs, prev_txs = _transfer_components()
    _expect_sign_failure(
        session,
        "Signing witness index out of range",
        inputs,
        outputs,
        prev_txs,
        witnesses=[],
    )


def test_sign_tx_rejects_raw_signing_witness(session: Session):
    # A raw blob in the signing slot would make the signed preimage
    # host-controlled; the device must build that witness itself.
    inputs, outputs, prev_txs = _transfer_components()
    _expect_sign_failure(
        session,
        "Missing WitnessArgs for signing witness",
        inputs,
        outputs,
        prev_txs,
        witnesses=[ckb.create_witness_raw(b"\x00" * 16)],
    )


def test_sign_tx_rejects_witness_args_outside_signing_slot(session: Session):
    inputs, outputs, prev_txs = _transfer_components()
    _expect_sign_failure(
        session,
        "Unexpected WitnessArgs for non-signing witness",
        inputs,
        outputs,
        prev_txs,
        witnesses=[ckb.create_witness_args(), ckb.create_witness_args()],
    )


def test_sign_tx_rejects_nonstandard_lock_size(session: Session):
    # Any size but the lock script's 65 bytes hashes a preimage the on-chain
    # verifier cannot reproduce.
    inputs, outputs, prev_txs = _transfer_components()
    _expect_sign_failure(
        session,
        "Unexpected lock size for signing witness",
        inputs,
        outputs,
        prev_txs,
        witnesses=[ckb.create_witness_args(lock_size=64)],
    )


def test_sign_tx_rejects_out_of_range_prev_output_index(session: Session):
    # The previous tx itself verifies, so the index check is the only guard.
    prev, prev_hash = prevtx.synth_prev_tx([10_000_001_000])
    inputs = [ckb.create_cell_input(tx_hash=prev_hash, index=3)]
    outputs = [
        ckb.create_cell_output(
            capacity=10_000_000_000,
            lock_code_hash=prevtx.LOCK_CODE_HASH,
            lock_hash_type=1,
            lock_args="ab" * 20,
        )
    ]
    _expect_sign_failure(
        session,
        "previous_output_index out of range",
        inputs,
        outputs,
        {prev_hash: prev},
    )


@pytest.mark.parametrize(
    "field,value,match",
    [
        pytest.param("inputs_count", 257, "Invalid inputs_count", id="inputs"),
        pytest.param("outputs_count", 257, "Invalid outputs_count", id="outputs"),
        pytest.param("cell_deps_count", 65, "Invalid cell_deps_count", id="cell-deps"),
        pytest.param("witnesses_count", 513, "Invalid witnesses_count", id="witnesses"),
    ],
)
def test_sign_tx_rejects_oversized_counts(session: Session, field, value, match):
    # Each count is one over its limit and fails before anything is streamed or
    # shown, so no signing workflow is left half-open.
    fields = dict(
        address_n=parse_path("m/44h/309h/0h/0/0"),
        network="Mainnet",
        inputs_count=1,
        outputs_count=1,
        cell_deps_count=0,
        witnesses_count=1,
        sign_group_input_indices=[0],
    )
    fields[field] = value

    with pytest.raises(TrezorFailure, match=match):
        session.call(messages.CKBSignTx(**fields), expect=messages.Failure)


@pytest.mark.parametrize(
    "field,match",
    [
        pytest.param("witnesses_count", "Missing witnesses_count", id="witnesses"),
        pytest.param(
            "sign_group_input_indices",
            "Missing sign_group_input_indices",
            id="sign-group",
        ),
    ],
)
def test_sign_tx_rejects_missing_witness_declaration(session: Session, field, match):
    # ckb.sign_tx() always fills both fields in, so the opening message is built
    # by hand and the rest of the stream served as usual.
    from trezorlib.ckb import _serve_tx_requests

    inputs, outputs, prev_txs = _transfer_components()
    fields = dict(
        address_n=parse_path("m/44h/309h/0h/0/0"),
        network="Mainnet",
        inputs_count=1,
        outputs_count=1,
        cell_deps_count=0,
        witnesses_count=1,
        sign_group_input_indices=[0],
    )
    del fields[field]

    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        res = session.call(messages.CKBSignTx(**fields), expect=messages.CKBTxRequest)
        with pytest.raises(TrezorFailure, match=match):
            _serve_tx_requests(
                session,
                res,
                inputs=inputs,
                outputs=outputs,
                cell_deps=[],
                witnesses=[],
                prev_tx_map=prev_txs,
                headers=None,
            )


def test_sign_tx_rejects_lying_prev_meta_counts(session: Session):
    # The bound must fire on the declared count, not after the streaming.
    inputs, outputs, _ = _transfer_components()
    RT = messages.CKBTxRequestType

    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        res = session.call(
            messages.CKBSignTx(
                address_n=parse_path("m/44h/309h/0h/0/0"),
                network="Mainnet",
                inputs_count=1,
                outputs_count=1,
                cell_deps_count=0,
                witnesses_count=1,
                sign_group_input_indices=[0],
            ),
            expect=messages.CKBTxRequest,
        )
        with pytest.raises(
            TrezorFailure, match="Previous transaction inputs_count out of range"
        ):
            for _ in range(20):
                if res.request_type == RT.TXINPUT:
                    ack = messages.CKBTxAckInput(input=inputs[0])
                elif res.request_type == RT.TXOUTPUT:
                    ack = messages.CKBTxAckOutput(output=outputs[0])
                elif res.request_type == RT.TXPREVMETA:
                    ack = messages.CKBTxAckPrevMeta(
                        version=0,
                        inputs_count=2000,  # > _MAX_PREV_INPUTS
                        outputs_count=1,
                        cell_deps_count=0,
                        header_deps=[],
                    )
                else:
                    raise AssertionError(f"unexpected request type {res.request_type}")
                res = session.call(ack, expect=messages.CKBTxRequest)


def _dao_withdraw_kwargs(
    ar_deposit=AR_DEPOSIT,
    ar_withdraw=AR_WITHDRAW,
    deposit_number=100,
    withdraw_number=200_000,
    cell_number=None,
    capacity=20_000 * SHANNON,
    header_indices=(0, 1),
):
    """kwargs for a phase-2 DAO withdrawal, with knobs to break each invariant.

    The output simply returns the plain capacity, so a scenario that fails
    during input verification never reaches the fee check.
    """
    deposit_header = _dao_header(deposit_number, ar_deposit)
    withdraw_header = _dao_header(withdraw_number, ar_withdraw, 1_576_852_800_000)

    cell_data = (deposit_number if cell_number is None else cell_number).to_bytes(
        8, "little"
    )
    withdrawing_cell = ckb.create_cell_output(
        capacity=capacity,
        lock_code_hash=prevtx.LOCK_CODE_HASH,
        lock_hash_type=1,
        lock_args="11" * 20,
        type_code_hash=DAO_CODE_HASH,
        type_hash_type=1,
        type_args=b"",
        data=cell_data,
    )
    prev_hash = prevtx.raw_tx_hash([], [withdrawing_cell], [cell_data], [])

    dep_idx, wit_idx = header_indices if header_indices else (None, None)
    inp = ckb.create_cell_input(
        tx_hash=prev_hash,
        index=0,
        dao_deposit_header_index=dep_idx,
        dao_withdraw_header_index=wit_idx,
    )
    output = ckb.create_cell_output(
        capacity=capacity,
        lock_code_hash=prevtx.LOCK_CODE_HASH,
        lock_hash_type=1,
        lock_args="aa" * 20,
    )
    return dict(
        inputs=[inp],
        outputs=[output],
        witnesses=[ckb.create_witness_args(input_type=(0).to_bytes(8, "little"))],
        prev_txs={prev_hash: ckb.create_prev_tx(outputs=[withdrawing_cell])},
        header_deps=[
            prevtx.header_hash(deposit_header),
            prevtx.header_hash(withdraw_header),
        ],
        headers=[deposit_header, withdraw_header],
    )


@pytest.mark.parametrize(
    "overrides,match",
    [
        pytest.param(
            {"header_indices": None},
            "DAO withdrawal input requires header indices",
            id="missing-indices",
        ),
        pytest.param(
            {"header_indices": (5, 1)},
            "DAO header index out of range",
            id="index-out-of-range",
        ),
        pytest.param(
            {"cell_number": 101},
            "DAO deposit header does not match cell",
            id="wrong-deposit-header",
        ),
        pytest.param(
            {"withdraw_number": 100},
            "DAO withdraw header must be after the deposit header",
            id="withdraw-before-deposit",
        ),
        pytest.param(
            {"ar_deposit": 0, "ar_withdraw": 0},
            "Invalid DAO deposit rate",
            id="zero-deposit-rate",
        ),
        pytest.param(
            {"ar_withdraw": AR_DEPOSIT - 1},
            "DAO compensation must be non-negative",
            id="negative-compensation",
        ),
        pytest.param(
            # this cell occupies 102 bytes, i.e. 102 CKB it cannot cover
            {"capacity": 100 * SHANNON},
            "DAO occupied capacity exceeds deposit",
            id="occupied-exceeds-deposit",
        ),
    ],
)
def test_sign_tx_rejects_invalid_dao_withdrawals(session: Session, overrides, match):
    # Each case breaks exactly one invariant of the RFC 0023 verification while
    # the rest of the transaction stays valid.
    kwargs = _dao_withdraw_kwargs(**overrides)
    _expect_sign_failure(
        session,
        match,
        kwargs.pop("inputs"),
        kwargs.pop("outputs"),
        kwargs.pop("prev_txs"),
        **kwargs,
    )


@pytest.mark.parametrize(
    "field,value,match",
    [
        pytest.param(
            "parent_hash", "00" * 31, "CKB header field must be 32 bytes", id="hash"
        ),
        pytest.param(
            "nonce", "00" * 15, "CKB header nonce must be 16 bytes", id="nonce"
        ),
    ],
)
def test_sign_tx_rejects_malformed_dao_header(session: Session, field, value, match):
    # A field of the wrong width must fail as a clean wire error. (Omitting the
    # header entirely is stopped by the protobuf decoder: the field is required.)
    kwargs = _dao_withdraw_kwargs()
    malformed = _dao_header(100, AR_DEPOSIT)
    setattr(malformed, field, bytes.fromhex(value))
    kwargs["headers"][0] = malformed

    _expect_sign_failure(
        session,
        match,
        kwargs.pop("inputs"),
        kwargs.pop("outputs"),
        kwargs.pop("prev_txs"),
        **kwargs,
    )


def test_ckb_header_hash_matches_real_block():
    # Real CKB testnet block 0x14862de (get_header). prevtx.header_hash mirrors the
    # device, so matching the real block hash proves the device serializes headers
    # like the chain. The Molecule nonce is little-endian, so the RPC value is reversed.
    nonce_be = bytes.fromhex("dca82cb7e9a6532774df50405ea8f7b4")
    header = ckb.create_block_header(
        version=0,
        compact_target=0x1D092A51,
        timestamp=0x19EF54A43FF,
        number=0x14862DE,
        epoch=0x708030D00340F,
        parent_hash="2ce3fc21e61547b9f3cf64607ede99db89b57105f863fc0d54e2551a4b73ae11",
        transactions_root="459a8d141f32618ab6b0d0009e6c0519dabee211eda82ff0bc6f8bf440bc14a5",
        proposals_hash="d89c1955e7aede1c654347f5fbc7b01eaaa42de9b8b8f38fd435502ccf40a3ad",
        extra_hash="2a1c789d4f5b25c7314d9b519d136cdfacf639c066cb15496fd9c0f0050703fb",
        dao="92e19928da715f5721051281c41d2a00ec383bac641ff50900032e1e81ec5c09",
        nonce=nonce_be[::-1],
    )

    assert (
        prevtx.header_hash(header).hex()
        == "6e94518dac325b38b689e0632cb8f7d39bc5feb1f4761140acb02174ccadb4d0"
    )


def test_dao_maximum_withdraw_matches_real_chain():
    # Expected value from CKB's own calculate_dao_maximum_withdraw RPC for a real
    # testnet DAO cell (100000 CKB; deposit block 19863841, withdraw block 19876418),
    # so the formula is checked against the chain, not just the synthetic test above.
    # AR is the second uint64 (LE) of each block's `dao` field.
    # Use the same helpers the device tests check the device against, so this
    # anchors the (device-mirrored) occupied + compensation math to the chain.
    occupied = prevtx.occupied_capacity(lock_args_len=20, type_args_len=0, data_len=8)
    max_withdraw = prevtx.dao_maximum_withdraw(
        capacity=100_000 * SHANNON,
        occupied=occupied,
        ar_deposit=11_747_530_930_063_161,
        ar_withdraw=11_748_349_830_170_696,
    )

    assert occupied == 102 * SHANNON
    assert max_withdraw == 10_000_696_371_717


def test_raw_tx_hash_matches_real_block_tx():
    # Anchor the RawTransaction serialization (prevtx.raw_tx_hash mirrors the
    # device's _compute_raw_tx_hash) to a real CKB testnet transaction, so the
    # device tests that rely on this hash are not only self-consistent.
    # Tx 0x9a8ad792... on CKB testnet (get_transaction): 1 input, 1 secp256k1
    # output, 1 dep_group cell_dep, no header_deps.
    inputs = [
        ckb.create_cell_input(
            tx_hash="7337f83101d63e1c94b485062281e33429c72b5a290649cbdb43395b17d0576b",
            index=0,
        )
    ]
    outputs = [
        ckb.create_cell_output(
            capacity=27_135_496_481,
            lock_code_hash="9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
            lock_hash_type=1,  # "type"
            lock_args="fa9e6338fb52b39ff39a3ca11c0ad793c0efeaf6",
        )
    ]
    cell_deps = [
        ckb.create_cell_dep(
            tx_hash="f8de3bb47d055cdf460d93a2a6e1b05f7432f9777c8c474abf4eec1d4aee5d37",
            index=0,
            dep_type=1,  # "dep_group"
        )
    ]

    tx_hash = prevtx.raw_tx_hash(inputs, outputs, [b""], cell_deps)

    assert tx_hash.hex() == (
        "9a8ad7922b5f03a3072fc5cb4aac6194e55a5f2c4ee43483010002b42d3b44dc"
    )


def test_sighash_all_matches_real_signed_tx():
    # Anchor sighash_all (prevtx.sighash_all mirrors the device's
    # _compute_sighash_all) to a real signed CKB transaction. The device tests
    # only assert the tx_hash, not the digest the device actually signs, so this
    # locks the signing-witness hashing and lock blanking. The expected digest
    # was confirmed by recovering the on-chain signature of tx 0x9a8ad792 to its
    # address (recovered blake160 == the input lock args fa9e6338...c0efeaf6).
    tx_hash = bytes.fromhex(
        "9a8ad7922b5f03a3072fc5cb4aac6194e55a5f2c4ee43483010002b42d3b44dc"
    )
    # One secp256k1 signer: the signing witness has its 65-byte lock blanked.
    blanked = prevtx.build_witness_args(65)

    sighash = prevtx.sighash_all(tx_hash, [blanked], [0], 1)

    assert sighash.hex() == (
        "b8bba12b59dbf39447ae69006c63e67ce7f8d94020cd3ee4110787dc4c83e77a"
    )
