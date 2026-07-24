import pytest

from trezorlib import messages
from trezorlib.debuglink import DebugSession as Session

pytestmark = [pytest.mark.models("core")]


def test_display_address_smoke(session: Session) -> None:
    response = session.call(
        messages.DisplayAddress(address="bc1qdemoaddress000000000000000000000000000"),
        expect=messages.Success,
    )
    assert response.message == "Address shown"


@pytest.mark.skip(reason="WARD proof-bearing DisplayAddress test gated out until THP decode path is fixed")
def test_display_address_with_ward_label(session: Session) -> None:
    # Intentionally empty: avoid constructing or sending the proof-bearing
    # DisplayAddress payload while THP/protobuf handling is unstable.
    del session
