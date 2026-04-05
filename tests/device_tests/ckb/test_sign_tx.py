import pytest

from trezorlib import ckb, messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures
from ...input_flows import InputFlowConfirmAllWarnings

pytestmark = [pytest.mark.altcoin, pytest.mark.ckb, pytest.mark.models("core")]


def _build_sign_tx_components(parameters):
    address_n = parse_path(parameters["path"])
    network = parameters.get("network", "Mainnet")

    inputs = [
        ckb.create_cell_input(
            tx_hash=inp["tx_hash"],
            index=inp["index"],
            since=inp.get("since", 0),
        )
        for inp in parameters["inputs"]
    ]

    outputs = [
        ckb.create_cell_output(
            capacity=out["capacity"],
            lock_code_hash=out["lock_code_hash"],
            lock_hash_type=out["lock_hash_type"],
            lock_args=out["lock_args"],
            type_code_hash=out.get("type_code_hash"),
            type_hash_type=out.get("type_hash_type"),
            type_args=out.get("type_args"),
            data=bytes.fromhex(out["data"].removeprefix("0x"))
            if out.get("data")
            else None,
        )
        for out in parameters["outputs"]
    ]

    cell_deps = [
        ckb.create_cell_dep(
            tx_hash=dep["tx_hash"],
            index=dep["index"],
            dep_type=dep["dep_type"],
        )
        for dep in parameters.get("cell_deps", [])
    ]

    return address_n, network, inputs, outputs, cell_deps, parameters.get("fee")


@parametrize_using_common_fixtures("ckb/sign_tx.json")
def test_sign_tx(session: Session, parameters, result):
    address_n, network, inputs, outputs, cell_deps, fee = _build_sign_tx_components(
        parameters
    )

    resp = ckb.sign_tx(
        session,
        address_n,
        inputs=inputs,
        outputs=outputs,
        cell_deps=cell_deps,
        network=network,
        fee=fee,
    )

    sig = resp.serialized.signature
    tx_hash = resp.serialized.tx_hash

    # Verify signature and tx_hash are present and correct length
    assert sig is not None
    assert tx_hash is not None

    if "signature_length" in result:
        assert len(sig) == result["signature_length"]
    if "tx_hash_length" in result:
        assert len(tx_hash) == result["tx_hash_length"]
    if "signature" in result:
        assert sig.hex() == result["signature"]
    if "tx_hash" in result:
        assert tx_hash.hex() == result["tx_hash"]


def test_sign_tx_streaming_protocol(session: Session):
    parameters = {
        "path": "m/44'/309'/0'/0/0",
        "network": "Mainnet",
        "inputs": [
            {
                "tx_hash": "1111111111111111111111111111111111111111111111111111111111111111",
                "index": 0,
                "since": 0,
            },
            {
                "tx_hash": "2222222222222222222222222222222222222222222222222222222222222222",
                "index": 1,
                "since": 0,
            },
        ],
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
            {
                "tx_hash": "4444444444444444444444444444444444444444444444444444444444444444",
                "index": 1,
                "dep_type": 1,
            },
        ],
        "fee": 1000,
    }
    address_n, network, inputs, outputs, cell_deps, fee = _build_sign_tx_components(
        parameters
    )

    with session.test_ctx as client:
        if not session.debug.legacy_debug:
            client.set_input_flow(InputFlowConfirmAllWarnings(client).get())

        res = session.call(
            messages.CKBSignTx(
                address_n=address_n,
                network=network,
                inputs_count=len(inputs),
                outputs_count=len(outputs),
                cell_deps_count=len(cell_deps),
                fee=fee,
            ),
            expect=messages.CKBTxRequest,
        )

        expected_steps = [
            (
                messages.CKBTxRequestType.TXINPUT,
                0,
                messages.CKBTxAckInput(input=inputs[0]),
            ),
            (
                messages.CKBTxRequestType.TXINPUT,
                1,
                messages.CKBTxAckInput(input=inputs[1]),
            ),
            (
                messages.CKBTxRequestType.TXOUTPUT,
                0,
                messages.CKBTxAckOutput(output=outputs[0]),
            ),
            (
                messages.CKBTxRequestType.TXOUTPUT,
                1,
                messages.CKBTxAckOutput(output=outputs[1]),
            ),
            (
                messages.CKBTxRequestType.TXCELLDEP,
                0,
                messages.CKBTxAckCellDep(cell_dep=cell_deps[0]),
            ),
            (
                messages.CKBTxRequestType.TXCELLDEP,
                1,
                messages.CKBTxAckCellDep(cell_dep=cell_deps[1]),
            ),
        ]

        for request_type, request_index, ack in expected_steps:
            assert res.request_type == request_type
            assert res.details is not None
            assert res.details.request_index == request_index
            assert res.serialized is None

            res = session.call(ack, expect=messages.CKBTxRequest)

    assert res.request_type == messages.CKBTxRequestType.TXFINISHED
    assert res.details is None
    assert res.serialized is not None
    assert res.serialized.signature is not None
    assert res.serialized.tx_hash is not None
    assert len(res.serialized.signature) == 65
    assert len(res.serialized.tx_hash) == 32


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
        )
