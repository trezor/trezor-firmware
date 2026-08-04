import binascii
import json

import pytest

from trezorlib import protobuf
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import Cancelled, TrezorFailure
from trezorlib.tools import parse_path

from . import tron_ext
from .common import COMMON_FIXTURES_DIR, parametrize_using_common_fixtures
from .generated import messages as tron_messages
from .input_flows import InputFlowConfirmAllWarnings


@parametrize_using_common_fixtures("sign_tx.json")
def test_sign_tx(session: Session, instance_id: int, parameters: dict, result: dict):
    address_n = parse_path(parameters["address_n"])
    tx = protobuf.dict_to_proto(tron_messages.SignTx, parameters["tx"])
    contract = make_contract(parameters["contract"])

    parsed_tx, parsed_contract = tron_ext.from_raw_data(
        bytes.fromhex(parameters["raw_data_hex"])
    )
    assert parsed_tx == tx
    assert parsed_contract == contract

    with session.test_ctx as client:
        client.set_input_flow(InputFlowConfirmAllWarnings(client).get())
        print("expected result is:", result)
        if "signature" in result:
            print("expecting signature:", result["signature"])
            response = tron_ext.sign_tx(
                session,
                instance_id,
                tx,
                contract,
                address_n,
                parameters.get("chunkify", True),
            )
            print("got response:", response)
            assert response.signature == binascii.unhexlify(result["signature"])
        elif "error_message" in result:
            with pytest.raises(TrezorFailure, match=result["error_message"]):
                tron_ext.sign_tx(
                    session,
                    instance_id,
                    tx,
                    contract,
                    address_n,
                    parameters.get("chunkify", True),
                )
        else:
            assert False, "Invalid expected result"


@pytest.mark.parametrize(
    "fixture",
    [
        "TransferContract",
        "Note_hello_world",
        "TriggerSmartContract_USDT_transfer",
        "Stake_for_Energy",
        "Claim_Voting_Rewards_different_owner",
        "Claim_Unfrozen_Balance_different_owner",
    ],
)
def test_cancel_sign_tx(session: Session, instance_id: int, fixture: str):
    tx, contract, address_n = build_from_fixture(fixture)

    def input_flow():
        yield
        session.cancel()

    with pytest.raises(Cancelled), session.test_ctx as client:
        client.set_input_flow(input_flow)
        tron_ext.sign_tx(session, instance_id, tx, contract, address_n)


@pytest.mark.parametrize(
    "fixture",
    [
        # "TransferContract",
        "Stake_for_Energy",
        "Stake_for_Bandwidth",
        "TriggerSmartContract_USDT_transfer",
    ],
)
def test_ui_cancel_flow(session: Session, instance_id: int, fixture: str):
    tx, contract, address_n = build_from_fixture(fixture)

    def ui_cancel_flow():
        yield
        session.debug.press_yes()
        yield
        session.debug.press_no()  # Wrong staking reason / wrong amount / wrong token

    with pytest.raises(Cancelled), session.test_ctx as client:
        client.set_input_flow(ui_cancel_flow)
        tron_ext.sign_tx(session, instance_id, tx, contract, address_n)


@pytest.mark.parametrize(
    "fixture",
    [
        "TriggerSmartContract_unknown_contract",
    ],
)
def test_ui_cancel_unknown_contract(session: Session, instance_id: int, fixture: str):
    tx, contract, address_n = build_from_fixture(fixture)

    def ui_cancel_flow():
        yield
        session.debug.press_yes()  # Accept warning
        yield
        session.debug.press_yes()  # Accept contract address
        yield
        session.debug.press_no()  # Data feels wrong

    with pytest.raises(Cancelled), session.test_ctx as client:
        client.set_input_flow(ui_cancel_flow)
        tron_ext.sign_tx(session, instance_id, tx, contract, address_n)


def make_contract(contract):
    type_name = contract["_message_type"]
    cls = getattr(tron_messages, type_name)
    return protobuf.dict_to_proto(cls, contract)


def build_from_fixture(name: str):
    fixtures = json.loads((COMMON_FIXTURES_DIR / "sign_tx.json").read_text())
    entry = next(t for t in fixtures["tests"] if t.get("name") == name)
    params = entry["parameters"]
    address_n = parse_path(params["address_n"])
    tx = protobuf.dict_to_proto(tron_messages.SignTx, params["tx"])
    contract = make_contract(params["contract"])
    return tx, contract, address_n
