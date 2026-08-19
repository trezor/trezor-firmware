import pytest

from trezorlib import ckb, messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures
from ...input_flows import InputFlowConfirmAllWarnings
from . import prevtx

pytestmark = [pytest.mark.altcoin, pytest.mark.ckb, pytest.mark.models("t3w1")]

SHANNON = 100_000_000
DAO_CODE_HASH = "82d76d1b75fe2fd9a27dfbaa65a039221a380d76c926f378d3f81cf3e7e13f2e"
AR_DEPOSIT = 10_000_000_000_000_000


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

    # The device must hash exactly the transaction we sent; check it against an
    # independent host-side serialization rather than a stored golden value
    # (the inputs are synthesized, so the old recorded hashes no longer apply).
    expected = prevtx.raw_tx_hash(inputs, outputs, _outputs_data(outputs), cell_deps)
    assert tx_hash == expected


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

    # The current tx is streamed first, then the previous txs are verified, then
    # the witnesses are requested.
    assert seen.index(RT.TXINPUT) < seen.index(RT.TXPREVMETA)
    assert seen.index(RT.TXPREVMETA) < seen.index(RT.TXWITNESS)
    assert RT.TXPREVOUTPUT in seen

    assert res.details is None
    assert res.serialized is not None
    assert len(res.serialized.signature) == 65
    assert len(res.serialized.tx_hash) == 32


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


def test_sign_tx_dao_withdraw(session: Session):
    # A Nervos DAO phase-2 withdrawal: the input is a withdrawing cell whose
    # unlocked value (deposit + compensation) exceeds its plain capacity, so the
    # single output is LARGER than the input capacity. The device must accept it
    # by verifying the deposit/withdraw block headers and crediting the
    # compensation, instead of rejecting with "Inputs do not cover outputs".
    ar_deposit = AR_DEPOSIT
    ar_withdraw = 10_050_000_000_000_000  # +0.5% accumulated rate
    deposit_number = 100
    withdraw_number = 200_000

    deposit_header = _dao_header(deposit_number, ar_deposit)
    withdraw_header = _dao_header(withdraw_number, ar_withdraw, 1_576_852_800_000)
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
        deposit_capacity, occupied, ar_deposit, ar_withdraw
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
        )

    assert resp.serialized.signature is not None
    assert len(resp.serialized.signature) == 65
    expected = prevtx.raw_tx_hash([inp], [output], [b""], [], header_deps=header_deps)
    assert resp.serialized.tx_hash == expected


def test_sign_tx_rejects_dao_withdraw_tampered_header(session: Session):
    # The device must reject a DAO withdrawal whose supplied header does not hash
    # to the committed header_deps entry (a host inflating the compensation).
    deposit_number = 100

    honest_deposit = _dao_header(deposit_number, AR_DEPOSIT)
    honest_withdraw = _dao_header(200_000, 10_050_000_000_000_000)
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
    ar_deposit = AR_DEPOSIT
    ar_real = ar_deposit * 120 // 100
    ar_decoy = ar_deposit * 10001 // 10000
    deposit_number = 100

    headers = [
        _dao_header(deposit_number, ar_deposit),
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
        deposit_capacity, occupied, ar_deposit, ar_real
    )
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
    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        with pytest.raises(TrezorFailure, match="Duplicate input outpoint"):
            ckb.sign_tx(
                session,
                parse_path("m/44h/309h/0h/0/0"),
                inputs=inputs,
                outputs=outputs,
                network="Mainnet",
                prev_txs={prev_hash: prev},
            )


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
    # Input supplies less capacity than the outputs require.
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
    # Fee far above 10 % of the sent amount: the warning flow is exercised and
    # the transaction still signs once confirmed.
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

    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        resp = ckb.sign_tx(
            session,
            parse_path("m/44h/309h/0h/0/0"),
            inputs=inputs,
            outputs=outputs,
            network="Mainnet",
            chunkify=True,
            prev_txs={prev_hash: prev},
        )
    assert len(resp.serialized.signature) == 65


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
    assert resp.serialized.signature is not None
    assert len(resp.serialized.signature) == 65


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
    SHANNON = 100_000_000
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
