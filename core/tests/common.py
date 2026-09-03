import unittest  # noqa: F401
from typing import TYPE_CHECKING, Any

from trezor import utils  # noqa: F401
from trezor.wire import context

from apps.common.paths import HARDENED

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from trezor.messages import TxRequest
    from trezor.protobuf import MessageType

    from apps.bitcoin.sign_tx.bitcoin import Bitcoin


def H_(x: int) -> int:
    """
    Shortcut function that "hardens" a number in a BIP44 path.
    """
    return x | HARDENED


def await_result(task: Awaitable) -> Any:
    value = None
    while True:
        try:
            result = task.send(value)
        except StopIteration as e:
            return e.value

        if result:
            value = await_result(result)
        else:
            value = None


class TestCaseWithContext(unittest.TestCase):
    def setUpClass(self):
        if utils.USE_THP:
            from thp_common import create_context

            context.CURRENT_CONTEXT = create_context()
        else:
            from trezor.wire.codec.codec_context import CodecContext

            context.CURRENT_CONTEXT = CodecContext(None, bytearray(64))

    def tearDownClass(self):
        context.CURRENT_CONTEXT = None


class TestCaseWithSeed(TestCaseWithContext):
    """
    Patch `apps.common.seed.get_seed` to return the "all" seed.
    """

    def setUpClass(self):
        from mock import MockAsync, patch
        from trezor.crypto import bip39

        from apps.common import seed as seed_module

        super().setUpClass()
        seed = bip39.seed(" ".join(["all"] * 12), "")
        self._seed_patch = patch(seed_module, "get_seed", MockAsync(return_value=seed))
        self._seed_patch.__enter__()

    def tearDownClass(self):
        self._seed_patch.__exit__(None, None, None)
        super().tearDownClass()


class _ScriptEnded(Exception):
    pass


_SIGNING_UI_STUBS = (
    "confirm_output",
    "confirm_decred_sstx_submission",
    "show_payment_request_details",
    "confirm_replacement",
    "confirm_modify_output",
    "confirm_modify_fee",
    "confirm_total",
    "confirm_joint_total",
    "confirm_feeoverthreshold",
    "confirm_change_count_over_threshold",
    "confirm_unverified_external_input",
    "confirm_foreign_address",
    "confirm_nondefault_locktime",
    "confirm_multiple_accounts",
)


class UiCall:
    """Expected (or recorded) call of a `apps.bitcoin.sign_tx.layout` function."""

    def __init__(
        self, name: str, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> None:
        self.name = name
        self.args = args
        self.kwargs = kwargs

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, UiCall)
            and self.name == other.name
            and self.args == other.args
            and self.kwargs == other.kwargs
        )

    def __repr__(self) -> str:
        return f"<UiCall {self.name} args={self.args} kwargs={self.kwargs}>"


class _UiExpectations:
    """`ui.confirm_output(...)` builds the expected `UiCall` for `layout.confirm_output(...)`."""

    def __getattr__(self, name: str):
        if name not in _SIGNING_UI_STUBS:
            raise AttributeError(name)

        def expect(*args, **kwargs) -> UiCall:
            return UiCall(name, args, kwargs)

        return expect


ui = _UiExpectations()


class ScriptedContext:
    """Fake wire context that asserts TxRequests and returns scripted acknowledgements.

    Expected signing UI calls (`UiCall`s) are interleaved with the TxRequests in the
    same script, so their relative order is asserted as well.
    """

    def __init__(self, script: list, testcase: unittest.TestCase) -> None:
        self._script = script
        self._index = 0
        self._tc = testcase

    def _next_expected(self, actual) -> None:
        if self._index >= len(self._script):
            self._tc.fail(f"unexpected {actual} after end of script")
        expected = self._script[self._index]
        self._index += 1
        if isinstance(expected, UiCall) != isinstance(actual, UiCall):
            self._tc.fail(f"expected {expected}, got {actual}")
        self._tc.assertEqual(actual, expected)

    async def call(self, msg, expected_type: MessageType):
        self._next_expected(msg)
        if self._index >= len(self._script):
            raise _ScriptEnded
        ack = self._script[self._index]
        self._index += 1
        if not expected_type.is_type_of(ack):
            self._tc.fail(
                f"expected {expected_type.MESSAGE_NAME}, got {ack.MESSAGE_NAME}"
            )
        return ack

    def ui_call(self, name: str, args: tuple, kwargs: dict) -> bool:
        self._next_expected(UiCall(name, args, kwargs))
        if self._index >= len(self._script):
            raise _ScriptEnded
        return True  # auto-confirm


def stub_signing_ui(ctx: ScriptedContext) -> None:
    from apps.bitcoin.sign_tx import layout

    def make_confirm_fn(name: str):
        async def confirm_fn(*args, **kwargs) -> bool:
            # make sure confirmation call matches the expected UiCall.
            return ctx.ui_call(name, args, kwargs)

        return confirm_fn

    for name in _SIGNING_UI_STUBS:
        assert hasattr(layout, name)
        setattr(layout, name, make_confirm_fn(name))


def run_signer(
    testcase: unittest.TestCase, signer: Bitcoin, messages: list
) -> TxRequest | None:
    """Drive a bitcoin signer against a TxRequest / TxAck / UiCall script.

    `messages` is a flat list of expected `TxRequest`s interleaved with the
    corresponding acknowledgements, and expected signing UI calls (built via
    `ui.<layout function>(...)`), which are auto-confirmed. A trailing
    `TxRequest` with `request_type=TXFINISHED` is asserted against
    `signer.tx_req` after the signer returns, and is not treated as a
    `context.call()`.
    """
    from trezor.enums import RequestType
    from trezor.messages import TxRequest

    finished = None
    if messages:
        last = messages[-1]
        if TxRequest.is_type_of(last) and last.request_type == RequestType.TXFINISHED:
            finished = last
            messages = messages[:-1]

    ctx = ScriptedContext(messages, testcase)
    stub_signing_ui(ctx)
    try:
        await_result(context.with_context(ctx, signer.signer()))
    except _ScriptEnded:
        if finished is not None:
            testcase.fail("signer stopped before TXFINISHED")
        if ctx._index != len(ctx._script):
            testcase.fail("script not fully consumed")
        return None

    if ctx._index != len(ctx._script):
        testcase.fail("script not fully consumed")
    if finished is not None:
        testcase.assertEqual(signer.tx_req, finished)
    return signer.tx_req
