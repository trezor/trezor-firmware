import pytest

from trezorlib import ckb
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import Cancelled, TrezorFailure
from trezorlib.tools import parse_path

from ...common import parametrize_using_common_fixtures

pytestmark = [pytest.mark.altcoin, pytest.mark.ckb, pytest.mark.models("core")]


@parametrize_using_common_fixtures("ckb/get_address.json")
def test_get_address(session: Session, parameters, result):
    address_n = parse_path(parameters["path"])
    address = ckb.get_address(session, address_n, show_display=True)
    assert address == result["address"]


def test_invalid_path(session: Session):
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        ckb.get_address(session, parse_path("m/44h/999h/0h/0/0"), show_display=True)


def test_get_address_cancel_show(session: Session):
    address_n = parse_path("m/44h/309h/0h/0/0")

    def input_flow():
        yield
        session.cancel()

    with pytest.raises(Cancelled), session.test_ctx as client:
        client.set_input_flow(input_flow)
        ckb.get_address(session, address_n, show_display=True)
