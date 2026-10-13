"""Host side of the test app: load it and call its blocks.

The library is the part meant to outlive manual testing; `cli` is only a
frontend over it. A test would use it the same way:

    from testapp_host import TestApp, messages as m

    app = TestApp.load(session)
    result = app.call(m.ConfirmAction(title="Send", action="Really?", br="t/1"))
    assert result.reply == m.Reply.Confirmed
"""

from . import _codegen

# The messages are generated from the app's .proto files, so both sides of the
# wire always agree; regenerated whenever a .proto is newer.
_codegen.ensure()

from . import messages  # noqa: E402
from .client import (  # noqa: E402
    ARTIFACTS,
    Progress,
    TestApp,
    UiResult,
    connect,
    extras,
    props,
)

__all__ = [
    "ARTIFACTS",
    "Progress",
    "TestApp",
    "UiResult",
    "connect",
    "extras",
    "messages",
    "props",
]
