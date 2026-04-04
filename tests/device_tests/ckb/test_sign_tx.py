import pytest

from trezorlib import ckb
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures

pytestmark = [pytest.mark.altcoin, pytest.mark.ckb, pytest.mark.models("core")]


@parametrize_using_common_fixtures("ckb/sign_tx.json")
def test_sign_tx(session: Session, parameters, result):
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

    fee = parameters.get("fee")

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
