import binascii

import pytest

from trezorlib import messages, protobuf, tron
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures
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
    contract = _make_contract(parameters["contract"])

    parsed_tx, parsed_contract = tron.from_raw_data(
        bytes.fromhex(parameters["raw_data_hex"])
    )
    assert parsed_tx == tx
    assert parsed_contract == contract

    with session.client as client:
        if input_flow:
            client.watch_layout()
            client.set_input_flow(input_flow)
        if "signature" in result:
            response = tron.sign_tx(session, tx, contract, address_n)
            assert response.signature == binascii.unhexlify(result["signature"])
        elif "error_message" in result:
            with pytest.raises(TrezorFailure, match=result["error_message"]):
                tron.sign_tx(session, tx, contract, address_n)
        else:
            assert False, "Invalid expected result"

def _make_contract(contract):
    type_name = contract["_message_type"]
    assert type_name.startswith("Tron") and type_name.endswith("Contract")
    cls = getattr(messages, type_name)
    return protobuf.dict_to_proto(cls, contract)
