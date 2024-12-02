from typing import TYPE_CHECKING

from storage.cache_common import InvalidSessionError
from trezor import log, loop, protobuf, utils, workflow
from trezor.enums import FailureType
from trezor.messages import Failure
from trezor.wire.context import UnexpectedMessageException, with_context
from trezor.wire.errors import ActionCancelled, DataError, Error, UnexpectedMessage
from trezor.wire.protocol_common import Context, Message

if TYPE_CHECKING:
    from typing import Any, Callable, Container

    from trezor.wire import Handler, LoadedMessageType, WireInterface

    HandlerFinder = Callable[[Any, Any], Handler | None]
    Filter = Callable[[int, Handler], Handler]

# If set to False protobuf messages marked with "experimental_message" option are rejected.
EXPERIMENTAL_ENABLED = False


def wrap_protobuf_load(
    buffer: bytes,
    expected_type: type[LoadedMessageType],
) -> LoadedMessageType:
    try:
        if __debug__ and utils.EMULATOR and utils.USE_THP:
            log.debug(
                __name__,
                "Buffer to be parsed to a LoadedMessage: %s",
                utils.get_bytes_as_str(buffer),
            )
        msg = protobuf.decode(buffer, expected_type, EXPERIMENTAL_ENABLED)
        if __debug__ and utils.EMULATOR:
            log.debug(
                __name__, "received message contents:\n%s", utils.dump_protobuf(msg)
            )
        return msg
    except Exception as e:
        if __debug__:
            log.exception(__name__, e)
        if e.args:
            raise DataError("Failed to decode message: " + " ".join(e.args))
        else:
            raise DataError("Failed to decode message")


async def handle_single_message(ctx: Context, msg: Message) -> bool:
    """Handle a message that was loaded from a WireInterface by the caller.

    Find the appropriate handler, run it and write its result on the wire. In case
    a problem is encountered at any point, write the appropriate error on the wire.

    The return value indicates whether to override the default restarting behavior. If
    `False` is returned, the caller is allowed to clear the loop and restart the
    MicroPython machine (see `session.py`). This would lose all state and incurs a cost
    in terms of repeated startup time. When handling the message didn't cause any
    significant fragmentation (e.g., if decoding the message was skipped), or if
    the type of message is supposed to be optimized and not disrupt the running state,
    this function will return `True`.
    """
    if __debug__:
        try:
            msg_type = protobuf.type_for_wire(msg.type).MESSAGE_NAME
        except Exception:
            msg_type = f"{msg.type} - unknown message type"
        log.debug(
            __name__,
            "%d receive: <%s>",
            ctx.iface.iface_num(),
            msg_type,
        )

    res_msg: protobuf.MessageType | None = None

    # We need to find a handler for this message type.
    try:
        handler: Handler = find_handler(ctx.iface, msg.type)
    except Error as exc:
        # Handlers are allowed to exception out. In that case, we can skip decoding
        # and return the error.
        await ctx.write(failure(exc))
        return True

    if msg.type in workflow.ALLOW_WHILE_LOCKED:
        workflow.autolock_interrupts_workflow = False

    # Here we make sure we always respond with a Failure response
    # in case of any errors.
    try:
        # Find a protobuf.MessageType subclass that describes this
        # message.  Raises if the type is not found.
        req_type = protobuf.type_for_wire(msg.type)

        # Try to decode the message according to schema from
        # `req_type`. Raises if the message is malformed.
        req_msg = wrap_protobuf_load(msg.data, req_type)

        # Create the handler task.
        task = handler(req_msg)

        # Run the workflow task.  Workflow can do more on-the-wire
        # communication inside, but it should eventually return a
        # response message, or raise an exception (a rather common
        # thing to do).  Exceptions are handled in the code below.

        # Spawn a workflow around the task. This ensures that concurrent
        # workflows are shut down.
        res_msg = await workflow.spawn(with_context(ctx, task))

    except UnexpectedMessageException:
        # Workflow was trying to read a message from the wire, and
        # something unexpected came in.  See Context.read() for
        # example, which expects some particular message and raises
        # UnexpectedMessage if another one comes in.
        # In order not to lose the message, we return it to the caller.

        # We process the unexpected message by aborting the current workflow and
        # possibly starting a new one, initiated by that message. (The main usecase
        # being, the host does not finish the workflow, we want other callers to
        # be able to do their own thing.)
        #
        # The message is stored in the exception, which we re-raise for the caller
        # to process. It is not a standard exception that should be logged and a result
        # sent to the wire.
        raise
    except BaseException as exc:
        # Either:
        # - the message had a type that has a registered handler, but does not have
        #   a protobuf class
        # - the message was not valid protobuf
        # - workflow raised some kind of an exception while running
        # - something canceled the workflow from the outside
        if __debug__:
            if isinstance(exc, ActionCancelled):
                log.debug(__name__, "cancelled: %s", exc.message)
            elif isinstance(exc, loop.TaskClosed):
                log.debug(__name__, "cancelled: loop task was closed")
            else:
                log.exception(__name__, exc)
        res_msg = failure(exc)

    if res_msg is not None:
        # perform the write outside the big try-except block, so that usb write
        # problem bubbles up
        await ctx.write(res_msg)

    # Look into `AVOID_RESTARTING_FOR` to see if this message should avoid restarting.
    return msg.type in AVOID_RESTARTING_FOR


AVOID_RESTARTING_FOR: Container[int] = ()


def failure(exc: BaseException) -> Failure:
    if isinstance(exc, Error):
        return Failure(code=exc.code, message=exc.message)
    elif isinstance(exc, loop.TaskClosed):
        return Failure(code=FailureType.ActionCancelled, message="Cancelled")
    elif isinstance(exc, InvalidSessionError):
        return Failure(code=FailureType.InvalidSession, message="Invalid session")
    else:
        # NOTE: when receiving generic `FirmwareError` on non-debug build,
        # change the `if __debug__` to `if True` to get the full error message.
        if __debug__:
            message = str(exc)
        else:
            message = "Firmware error"
        return Failure(code=FailureType.FirmwareError, message=message)


def unexpected_message() -> Failure:
    return Failure(code=FailureType.UnexpectedMessage, message="Unexpected message")


def find_handler(iface: WireInterface, msg_type: int) -> Handler:
    import usb

    from apps import workflow_handlers

    handler = workflow_handlers.find_registered_handler(msg_type)
    if handler is None:
        raise UnexpectedMessage("Unexpected message")

    if __debug__ and iface is usb.iface_debug:
        # no filtering allowed for debuglink
        return handler

    for filter in filters:
        handler = filter(msg_type, handler)

    return handler


filters: list[Filter] = []
"""Filters for the wire handler.

Filters are applied in order. Each filter gets a message id and a preceding handler. It
must either return a handler (the same one or a modified one), or raise an exception
that gets sent to wire directly.

Filters are not applied to debug sessions.

The filters are designed for:
 * rejecting messages -- while in Recovery mode, most messages are not allowed
 * adding additional behavior -- while device is soft-locked, a PIN screen will be shown
   before allowing a message to trigger its original behavior.

For this, the filters are effectively deny-first. If an earlier filter rejects the
message, the later filters are not called. But if a filter adds behavior, the latest
filter "wins" and the latest behavior triggers first.
Please note that this behavior is really unsuited to anything other than what we are
using it for now. It might be necessary to modify the semantics if we need more complex
usecases.

NB: `filters` is currently public so callers can have control over where they insert
new filters, but removal should be done using `remove_filter`!
We should, however, change it such that filters must be added using an `add_filter`
and `filters` becomes private!
"""


def remove_filter(filter: Filter) -> None:
    try:
        filters.remove(filter)
    except ValueError:
        pass
