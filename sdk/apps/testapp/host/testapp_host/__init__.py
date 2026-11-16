"""Host side of the test app: load it and call its modui endpoints.

The library is the part meant to outlive manual testing; `cli` is only a
frontend over it, and the device tests build their requests with it too:

    from testapp_host import TestApp, address, messages as m

    app = TestApp.load(session)
    request = m.Review(
        step="send",
        title="Send",
        fields=[address("Recipient", "TQ9JfxgJ9JBz4GZ4MRDrjJeBdA6Mx5yYhq")],
    )
    assert app.call(request) == m.Reply.Confirmed
"""

from . import _codegen

# The messages are generated from the app's .proto files, so both sides of the
# wire always agree; the device tests use the same module.
messages = _codegen.load(__name__ + ".messages")

from . import showcases  # noqa: E402
from .client import (  # noqa: E402
    ARTIFACTS,
    Progress,
    TestApp,
    address,
    amount,
    connect,
    data,
    extras,
    field,
    note,
    text,
    warning,
)

# The example flows live in `showcases`, composed on the host from the endpoints.
SHOWCASES = showcases.SHOWCASES

__all__ = [
    "ARTIFACTS",
    "SHOWCASES",
    "Progress",
    "TestApp",
    "address",
    "amount",
    "connect",
    "data",
    "extras",
    "field",
    "messages",
    "note",
    "showcases",
    "text",
    "warning",
]
