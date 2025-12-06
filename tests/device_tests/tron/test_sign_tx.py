import binascii

import pytest

from trezorlib import messages, protobuf, tron
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures

pytestmark = [pytest.mark.altcoin, pytest.mark.tron, pytest.mark.models("core")]


@parametrize_using_common_fixtures("tron/sign_tx.json")
def test_sign_tx(session: Session, parameters, result):
    def make_contract(contract):
        type_name = contract["_message_type"]
        assert type_name.startswith("Tron") and type_name.endswith("Contract")
        cls = getattr(messages, type_name)
        return protobuf.dict_to_proto(cls, contract)

    address_n = parse_path(parameters["address_n"])
    tx = protobuf.dict_to_proto(messages.TronSignTx, parameters["tx"])
    contract = make_contract(parameters["contract"])

    parsed_tx, parsed_contract = tron.from_raw_data(
        bytes.fromhex(parameters["raw_data_hex"])
    )
    assert parsed_tx == tx
    assert parsed_contract == contract

    response = tron.sign_tx(session, tx, contract, address_n)
    assert response.signature == binascii.unhexlify(result["signature"])
