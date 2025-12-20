import binascii
import json

import pytest

from trezorlib import messages, protobuf, tron
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import Cancelled, TrezorFailure
from trezorlib.tools import parse_path

from ...common import COMMON_FIXTURES_DIR, parametrize_using_common_fixtures

pytestmark = [pytest.mark.altcoin, pytest.mark.tron, pytest.mark.models("core")]


@parametrize_using_common_fixtures("tron/sign_tx.json")
def test_sign_tx(session: Session, parameters, result):
    address_n = parse_path(parameters["address_n"])
    tx = protobuf.dict_to_proto(messages.TronSignTx, parameters["tx"])
    contract = make_contract(parameters["contract"])

    parsed_tx, parsed_contract = tron.from_raw_data(
        bytes.fromhex(parameters["raw_data_hex"])
    )
    assert parsed_tx == tx
    assert parsed_contract == contract

    if "signature" in result:
        response = tron.sign_tx(session, tx, contract, address_n)
        assert response.signature == binascii.unhexlify(result["signature"])
    elif "error_message" in result:
        with pytest.raises(TrezorFailure, match=result["error_message"]):
            tron.sign_tx(session, tx, contract, address_n)
    else:
        assert False, "Invalid expected result"


def test_cancel_transfer(session: Session):
    tx, contract, address_n = build_from_fixture("TransferContract")

    def input_flow():
        yield
        session.cancel()

    with pytest.raises(Cancelled), session.client as client:
        client.set_input_flow(input_flow)
        tron.sign_tx(session, tx, contract, address_n)


def test_cancel_transfer_with_note(session: Session):
    tx, contract, address_n = build_from_fixture("Note_hello_world")

    def input_flow():
        yield
        session.cancel()

    with pytest.raises(Cancelled), session.client as client:
        client.set_input_flow(input_flow)
        tron.sign_tx(session, tx, contract, address_n)


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
