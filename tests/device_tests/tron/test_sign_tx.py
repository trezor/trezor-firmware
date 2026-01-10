import binascii
import json

import pytest

from trezorlib import messages, protobuf, tron
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import Cancelled, TrezorFailure
from trezorlib.tools import parse_path

from ...common import COMMON_FIXTURES_DIR, parametrize_using_common_fixtures
from ...input_flows import InputFlowConfirmAllWarnings

pytestmark = [pytest.mark.altcoin, pytest.mark.tron, pytest.mark.models("core")]


@parametrize_using_common_fixtures("tron/sign_tx.json")
def test_sign_tx(session: Session, parameters: dict, result: dict):
    input_flow = (
        InputFlowConfirmAllWarnings(session.client).get()
        if not session.client.debug.legacy_debug
        else None
    )
    _do_test_signtx(session, parameters, result, input_flow)


def _do_test_signtx(session: Session, parameters: dict, result: dict, input_flow=None):

    address_n = parse_path(parameters["address_n"])
    tx = protobuf.dict_to_proto(messages.TronSignTx, parameters["tx"])
    contract = make_contract(parameters["contract"])

    parsed_tx, parsed_contract = tron.from_raw_data(
        bytes.fromhex(parameters["raw_data_hex"])
    )
    assert parsed_tx == tx
    assert parsed_contract == contract

    if "signature" in result:
        with session.client as client:
            client.set_input_flow(input_flow)
            response = tron.sign_tx(session, tx, contract, address_n)
            assert response.signature == binascii.unhexlify(result["signature"])
    elif "error_message" in result:
        with (
            pytest.raises(TrezorFailure, match=result["error_message"]),
            session.client as client,
        ):
            client.set_input_flow(input_flow)
            tron.sign_tx(session, tx, contract, address_n)
    else:
        assert False, "Invalid expected result"


def _do_cancel_sign_tx(session: Session, fixture: str):
    tx, contract, address_n = build_from_fixture(fixture)

    def input_flow():
        yield
        session.cancel()

    with pytest.raises(Cancelled), session.client as client:
        client.set_input_flow(input_flow)
        tron.sign_tx(session, tx, contract, address_n)


@pytest.mark.parametrize(
    "fixture",
    [
        "TransferContract",
        "Note_hello_world",
        "TriggerSmartContract_USDT_transfer",
    ],
)
def test_cancel_sign_tx(session: Session, fixture: str):
    _do_cancel_sign_tx(session, fixture)


def make_contract(contract):
    type_name = contract["_message_type"]
    assert type_name.startswith("Tron") and type_name.endswith("Contract")
    cls = getattr(messages, type_name)
    return protobuf.dict_to_proto(cls, contract)


def build_from_fixture(name: str):
    fixtures = json.loads((COMMON_FIXTURES_DIR / "tron" / "sign_tx.json").read_text())
    entry = next(t for t in fixtures["tests"] if t.get("name") == name)
    params = entry["parameters"]
    address_n = parse_path(params["address_n"])
    tx = protobuf.dict_to_proto(messages.TronSignTx, params["tx"])
    contract = make_contract(params["contract"])
    return tx, contract, address_n
