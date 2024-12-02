from trezor import log, loop
from trezor.enums import FailureType
from trezor.messages import Failure, ThpCreateNewSession, ThpNewSession
from trezor.wire.context import get_context
from trezor.wire.errors import ActionCancelled, DataError
from trezor.wire.thp import SessionState


async def create_new_session(message: ThpCreateNewSession) -> ThpNewSession | Failure:
    """
    Creates a new `ThpSession` based on the provided parameters and returns a
    `ThpNewSession` message containing the new session ID.

    Returns an appropriate `Failure` message if session creation fails.
    """
    from trezor.wire import NotInitialized
    from trezor.wire.thp.session_context import GenericSessionContext
    from trezor.wire.thp.session_manager import create_new_session

    from apps.common.seed import derive_and_store_roots

    ctx = get_context()

    # Assert that context `ctx` is `GenericSessionContext`
    assert isinstance(ctx, GenericSessionContext)

    channel = ctx.channel

    # Do not use `ctx` beyond this point, as it is techically
    # allowed to change in between await statements

    new_session = create_new_session(channel)
    try:
        await derive_and_store_roots(new_session, message)
    except DataError as e:
        return Failure(code=FailureType.DataError, message=e.message)
    except ActionCancelled as e:
        return Failure(code=FailureType.ActionCancelled, message=e.message)
    except NotInitialized as e:
        return Failure(code=FailureType.NotInitialized, message=e.message)
    # TODO handle other errors (`Exception`` when "Cardano icarus secret is already set!"
    # and `RuntimeError` when accessing storage for mnemonic.get_secret - it actually
    # happens for locked devices)

    new_session.set_session_state(SessionState.ALLOCATED)
    channel.sessions[new_session.session_id] = new_session
    loop.schedule(new_session.handle())
    new_session_id: int = new_session.session_id

    if __debug__:
        log.debug(
            __name__,
            "create_new_session - new session created. Passphrase: %s, Session id: %d\n%s",
            message.passphrase if message.passphrase is not None else "",
            new_session.session_id,
            str(channel.sessions),
        )

    return ThpNewSession(new_session_id=new_session_id)
