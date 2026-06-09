import pytest

from trezorlib import ckb, messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures
from ...input_flows import InputFlowConfirmAllWarnings
from . import prevtx

pytestmark = [pytest.mark.altcoin, pytest.mark.ckb, pytest.mark.models("t3w1")]


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
