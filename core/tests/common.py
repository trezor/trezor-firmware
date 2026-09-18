import unittest  # noqa: F401
from typing import TYPE_CHECKING, Any

from trezor import utils  # noqa: F401
from trezor.wire import context

from apps.common.paths import HARDENED

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from trezor.messages import TxRequest

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


class _ScriptEnded(Exception):
    pass


async def _auto_confirm(*args, **kwargs):
    return True


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


def stub_signing_ui() -> None:
    from apps.bitcoin.sign_tx import helpers

    for name in _SIGNING_UI_STUBS:
        setattr(helpers, name, _auto_confirm)


class ScriptedContext:
    """Fake wire context that asserts TxRequests and returns scripted acknowledgements."""

    def __init__(self, script: list, testcase: unittest.TestCase) -> None:
        self._script = script
        self._index = 0
        self._tc = testcase

    async def call(self, msg, expected_type):
        if self._index >= len(self._script):
            self._tc.fail(f"unexpected TxRequest after end of script: {msg}")
        expected = self._script[self._index]
        self._index += 1
        self._tc.assertEqual(msg, expected)
        if self._index >= len(self._script):
            raise _ScriptEnded
        ack = self._script[self._index]
        self._index += 1
        return ack


def run_signer(
    testcase: unittest.TestCase, signer: Bitcoin, messages: list
) -> TxRequest | None:
    """Drive a bitcoin signer against a TxRequest / TxAck script.

    `messages` is a flat list of expected `TxRequest`s interleaved with the
    corresponding acknowledgements. A trailing `TxRequest` with
    `request_type=TXFINISHED` is asserted against `signer.tx_req` after the
    signer returns, and is not treated as a `context.call()`.
    """
    from trezor.enums import RequestType
    from trezor.messages import TxRequest

    stub_signing_ui()

    finished = None
    if messages:
        last = messages[-1]
        if TxRequest.is_type_of(last) and last.request_type == RequestType.TXFINISHED:
            finished = last
            messages = messages[:-1]

    ctx = ScriptedContext(messages, testcase)
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
