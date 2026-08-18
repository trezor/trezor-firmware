# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor.enums import MessageType

from apps.workflow_handlers import find_registered_handler

# Every WARD message the device is dispatched. Acks are absent on purpose: the device sends
# those, so nothing resolves a handler for them, and this test asserts that too.
WARD_REQUESTS = (
    "WardGetEntry",
    "WardSetEntry",
    "WardDeleteEntry",
    "WardSync",
    "WardIngestAttestation",
    "WardReconcile",
    "WardVerifyChain",
    "WardRollback",
    "WardRecoverCounter",
    "WardPinCachedEntry",
    "WardEraseCachedEntry",
    "WardFlushQueue",
)


class TestWardHandlerWiring(unittest.TestCase):
    """Every registered WARD handler must actually resolve to a callable.

    WHY THIS IS WORTH A FILE FOR AN ASSERTION THIS SMALL. `find_registered_handler` derives
    the handler FUNCTION name from the last component of the module path it is registered
    under:

        handler_name = modname[modname.rfind(".") + 1 :]
        module = __import__(modname, None, None, (handler_name,), 0)
        return getattr(module, handler_name)

    So `apps.ward.recover` must define `recover`. That rule is undocumented and invisible at
    the registration site, and getting it wrong fails at `getattr` -- BEFORE any line of the
    handler body runs. Every request then fails identically whatever it asked for, which
    looks like anything except a naming problem: naming the recovery handler
    `recover_counter` cost a full device-test cycle and three wrong hypotheses before the
    cause was found. A rename can reintroduce it silently, and a partial one compiles.

    This is the only check that catches it without building firmware and running the
    emulator. Note it costs almost nothing: every WARD handler module imports only `typing`
    at module level and defers the rest inside the function, so resolving them all pulls in
    no UI, no crypto and no storage.

    A mismatch does not even reach an assertion here -- `find_registered_handler` catches
    only ValueError, so the AttributeError propagates and the test errors out by name.
    """

    def test_every_ward_request_resolves_to_a_callable(self):
        for name in WARD_REQUESTS:
            handler = find_registered_handler(getattr(MessageType, name))
            self.assertTrue(handler is not None, "no handler registered for " + name)
            self.assertTrue(
                callable(handler), "handler for " + name + " is not callable"
            )

    def test_the_set_of_dispatched_ward_messages_is_exactly_this_list(self):
        """Guards both directions, which one list alone cannot.

        A handler that stops resolving drops out of `resolved` and is caught above. A handler
        registered by someone who did not add it here shows up as an extra, and would
        otherwise ship unexercised by this file -- the failure mode that let the recovery
        handler through in the first place.
        """
        resolved = set()
        for name in dir(MessageType):
            if not name.startswith("Ward"):
                continue
            if find_registered_handler(getattr(MessageType, name)) is not None:
                resolved.add(name)
        self.assertEqual(resolved, set(WARD_REQUESTS))


if __name__ == "__main__":
    unittest.main()
