# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor.enums import MessageType
from trezor.wire import DataError

from apps.ward.label import resolve_label
from apps.workflow_handlers import find_registered_handler


class TestDisplayAddressWiring(unittest.TestCase):
    """The two things about this app that fail BEFORE any of its code runs.

    `find_registered_handler` derives the handler FUNCTION name from the last component of
    the module path it is registered under -- `apps.display_address.show` must define
    `show` -- and a mismatch raises at `getattr`, so every request fails identically
    whatever it asked for. See the longer note in test_apps.ward.handlers.py; this is the
    same trap, and the same cheap check.
    """

    def test_display_address_resolves_to_a_callable(self):
        handler = find_registered_handler(MessageType.DisplayAddress)
        self.assertTrue(handler is not None, "no handler registered for DisplayAddress")
        self.assertTrue(callable(handler), "DisplayAddress handler is not callable")


class TestLabelCapability(unittest.TestCase):
    """The capability list is what bounds which firmware modules can turn WARD into a
    label lookup. It has to refuse before it derives anything -- a gate that ran after the
    seed was touched would still have done the work it was meant to prevent -- so this
    asserts the refusal on a device with no seed at all, where any derivation would fail
    with a different error entirely.
    """

    def test_an_unlisted_principal_is_refused(self):
        try:
            await_result(resolve_label("no_such_app", b"addr1"))
        except DataError as e:
            # The MESSAGE is asserted, not just the type, because `require_initialized`
            # raises from the very next line -- a bare type check would pass whether the
            # gate ran or not, which is the one thing this test exists to establish.
            #
            # READ OFF `.message`, never `str(e)`. `trezor.wire.errors.Error` calls
            # `Exception.__init__()` with no arguments and keeps the text in an attribute,
            # so `str(e)` is the empty string for every one of these and asserting on it
            # passes nothing and fails everything.
            self.assertTrue("not authorized" in e.message, e.message)
        else:
            self.fail("an unlisted principal was allowed to resolve a label")


if __name__ == "__main__":
    unittest.main()
