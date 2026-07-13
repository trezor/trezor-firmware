import pytest

from . import tron_ext
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import Cancelled, TrezorFailure
from trezorlib.tools import parse_path

from .common import parametrize_using_common_fixtures
from .input_flows import InputFlowShowAddressQRCode



@parametrize_using_common_fixtures("get_address.json")
def test_get_address(session: Session, instance_id: int, parameters, result):
    address_n = parse_path(parameters["path"])
    address = tron_ext.get_address(session, instance_id, address_n, show_display=True)
    assert address == result["address"]


@parametrize_using_common_fixtures("get_address.json")
def test_get_address_chunkify_details(session: Session, instance_id: int, parameters, result):
    with session.test_ctx as client:
        IF = InputFlowShowAddressQRCode(client)
        client.set_input_flow(IF.get())
        address_n = parse_path(parameters["path"])
        address = tron_ext.get_address(session, instance_id, address_n, show_display=True, chunkify=True)
        assert address == result["address"]


def test_invalid_path(session: Session, instance_id: int,):
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        tron_ext.get_address(session, instance_id,parse_path("m/44h/999h/0h/0/0"), show_display=True)


def test_get_address_cancel_show(session: Session, instance_id: int,):
    address_n = parse_path("m/44h/195h/0h/0/0")

    def input_flow():
        yield
        session.cancel()

    with pytest.raises(Cancelled), session.test_ctx as client:
        client.set_input_flow(input_flow)
        tron_ext.get_address(session, instance_id, address_n, show_display=True)
