"""Host side of the test app: load it and call its layouts.

The library is the part meant to outlive manual testing; `cli` is only a
frontend over it. A test would use it the same way:

    from testapp_host import TestApp, address, messages as m

    app = TestApp.load(session)
    request = m.Review(
        step="send",
        title="Send",
        fields=[address("Recipient", "TQ9JfxgJ9JBz4GZ4MRDrjJeBdA6Mx5yYhq")],
    )
    assert app.call(request).reply == m.Reply.Confirmed
"""

from . import _codegen

# The messages are generated from the app's .proto files, so both sides of the
# wire always agree; the device tests use the same module.
messages = _codegen.load(__name__ + ".messages")

from .client import (  # noqa: E402
    ARTIFACTS,
    SHOWCASES,
    Progress,
    TestApp,
    UiResult,
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

__all__ = [
    "ARTIFACTS",
    "SHOWCASES",
    "Progress",
    "TestApp",
    "UiResult",
    "address",
    "amount",
    "connect",
    "data",
    "extras",
    "field",
    "messages",
    "note",
    "text",
    "warning",
]
