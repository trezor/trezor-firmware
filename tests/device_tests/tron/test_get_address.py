import pytest

from trezorlib import tron
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import Cancelled, TrezorFailure
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures
from ...input_flows import InputFlowShowAddressQRCode

pytestmark = [pytest.mark.altcoin, pytest.mark.tron, pytest.mark.models("core")]


@parametrize_using_common_fixtures("tron/get_address.json")
def test_get_address(session: Session, parameters, result):
    address_n = parse_path(parameters["path"])
    address = tron.get_address(session, address_n, show_display=True)
    assert address == result["address"]


@parametrize_using_common_fixtures("tron/get_address.json")
def test_get_address_chunkify_details(session: Session, parameters, result):
    with session.test_ctx as client:
        IF = InputFlowShowAddressQRCode(client)
        client.set_input_flow(IF.get())
        address_n = parse_path(parameters["path"])
        address = tron.get_address(session, address_n, show_display=True, chunkify=True)
        assert address == result["address"]


def test_invalid_path(session: Session):
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        tron.get_address(session, parse_path("m/44h/999h/0h/0/0"), show_display=True)


def test_get_address_cancel_show(session: Session):
    address_n = parse_path("m/44h/195h/0h/0/0")

    def input_flow():
        yield
        session.cancel()

    with pytest.raises(Cancelled), session.test_ctx as client:
        client.set_input_flow(input_flow)
        tron.get_address(session, address_n, show_display=True)
