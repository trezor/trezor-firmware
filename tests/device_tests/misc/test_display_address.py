import pytest

from trezorlib import display_address, messages, ward
from trezorlib.authdb_tree import AuthDbTree
from trezorlib.debuglink import DebugSession as Session

pytestmark = [pytest.mark.models("core")]


def test_display_address_smoke(session: Session) -> None:
    response = session.call(
        messages.DisplayAddress(address="bc1qdemoaddress000000000000000000000000000"),
        expect=messages.Success,
    )
    assert response.message == "Address shown"


def test_display_address_with_ward_label(session: Session) -> None:
    address = "bc1qdemoaddress000000000000000000000000000"
    tree = AuthDbTree()
    tree.insert(address.encode(), b"alice.btc", counter=1)
    ward.debug_set_root(session, tree.get_root_hash())

    shown = display_address.show_address(
        session,
        address,
        ward_value=b"alice.btc",
        ward_proof=tree.get_proof(address.encode()),
        ward_counter=1,
    )
    assert shown == address
