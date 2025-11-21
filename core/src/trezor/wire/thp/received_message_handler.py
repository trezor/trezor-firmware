from typing import TYPE_CHECKING

from storage.cache_common import (
    CHANNEL_HANDSHAKE_HASH,
    CHANNEL_KEY_RECEIVE,
    CHANNEL_KEY_SEND,
    CHANNEL_NONCE_RECEIVE,
    CHANNEL_NONCE_SEND,
)
from storage.cache_thp import KEY_LENGTH, TAG_LENGTH, update_session_last_used
from trezor import config, protobuf, utils
from trezor.enums import FailureType
from trezor.messages import Failure

from .. import message_handler
from ..errors import DataError
from . import (
    HANDSHAKE_COMP_RES,
    HANDSHAKE_INIT_RES,
    ChannelState,
    SessionState,
    ThpDecryptionError,
    ThpDeviceLockedError,
    ThpErrorType,
    ThpUnallocatedSessionError,
)
from . import alternating_bit_protocol as ABP
from . import control_byte, get_encoded_device_properties, session_manager
from .crypto import PUBKEY_LENGTH, Handshake
from .session_context import SeedlessSessionContext

if TYPE_CHECKING:
    from buffer_types import AnyBytes

    from trezor.messages import ThpHandshakeCompletionReqNoisePayload

    from .channel import Channel

if __debug__:
    from trezor import log
    from trezor.utils import hexlify_if_bytes

_TREZOR_STATE_UNPAIRED = b"\x00"
_TREZOR_STATE_PAIRED = b"\x01"
_TREZOR_STATE_PAIRED_AUTOCONNECT = b"\x02"


async def handle_received_message(channel: Channel) -> bool:
    """
    Handle a message received from the channel.

    Returns False if we can restart the event loop.
    """
    try:
        state = channel.get_channel_state()
        if state is ChannelState.ENCRYPTED_TRANSPORT:
            await _handle_state_ENCRYPTED_TRANSPORT(channel)
            return False
        elif _is_channel_state_pairing(state):
            await _handle_pairing(channel)
            return False
        elif state is ChannelState.TH1:
            await _handle_state_handshake(channel)
            return channel.get_channel_state() == ChannelState.TC1
        if __debug__:
            channel._log("Invalid channel state", logger=log.error)
    except ThpUnallocatedSessionError as e:
        error_message = Failure(code=FailureType.ThpUnallocatedSession)
        await channel.write(error_message, e.session_id)
    except ThpDecryptionError:
        await channel.iface_ctx.write_error(
            channel.get_channel_id_int(), ThpErrorType.DECRYPTION_FAILED
        )
        channel.clear()
    except ThpDeviceLockedError:
        await channel.iface_ctx.write_error(
            channel.get_channel_id_int(), ThpErrorType.DEVICE_LOCKED
        )
        channel.clear()
    return False


async def _handle_thp_during_unlock(channel: Channel) -> None:
    """
    Keep handling THP messages while waiting for unlock.
    It allows preemption and ping/pong handling if the device is soft-locked.
    """
    while True:
        # may raise ChannelPreemptedException if another channel preempts this one
        msg = await channel._get_reassembled_message()
        if __debug__:
            # we don't expect messages from this channel since the handshake is not over
            channel._log(
                "drop unexpected message",
                utils.hexlify_if_bytes(msg),
                logger=log.warning,
            )


async def _handle_state_handshake(
    ctx: Channel,
) -> None:
    if __debug__:
        log.debug(__name__, "handle_state_handshake", iface=ctx.iface)

    def is_handshake_init_req(ctrl_byte: int) -> bool:
        success = control_byte.is_handshake_init_req(ctrl_byte)

        if success and control_byte.get_ack_bit(ctrl_byte):
            # Newer Suite versions will send `handshake_init_req` with a non-zero ACK bit.
            # The device should not use ACK piggybacking with older Suite versions.
            ABP.allow_ack_piggybacking(ctx.channel_cache)

        if __debug__:
            ctx._log(
                "THP ACK piggybacking = ",
                str(ABP.is_ack_piggybacking_allowed(ctx.channel_cache)),
            )

        return success

    payload = await ctx.recv_payload(is_handshake_init_req)

    if len(payload) != PUBKEY_LENGTH + 1:
        if __debug__:
            log.error(
                __name__,
                "Message received is not a valid handshake init request: %d bytes",
                len(payload),
            )
        return

    host_ephemeral_public_key = payload[:PUBKEY_LENGTH]
    # show the PIN keyboard to allow the user to unlock the device
    try_to_unlock = payload[PUBKEY_LENGTH] & 0x01 == 1

    async def _check_unlocked() -> None:
        if config.is_unlocked():
            return

        if try_to_unlock:
            from trezor import loop, workflow

            from apps.common.lock_manager import unlock_device

            # Register the unlock prompt with the workflow management system
            # (in order to avoid immediately respawning the lockscreen task)
            try:
                unlock = workflow.spawn(unlock_device())
                handle = _handle_thp_during_unlock(channel=ctx)
                return await loop.race(unlock, handle)
            except Exception as e:
                if __debug__:
                    log.exception(__name__, e)

        # Fail pairing if still locked
        raise ThpDeviceLockedError

    await _check_unlocked()

    handshake = Handshake()

    trezor_ephemeral_public_key, encrypted_trezor_static_public_key, tag = (
        handshake.handle_th1_crypto(
            get_encoded_device_properties(ctx.iface),
            host_ephemeral_public_key=host_ephemeral_public_key,
            payload=payload[PUBKEY_LENGTH:],
        )
    )

    if __debug__:
        log.debug(
            __name__,
            "trezor ephemeral public key: %s",
            hexlify_if_bytes(trezor_ephemeral_public_key),
            iface=ctx.iface,
        )
        log.debug(
            __name__,
            "encrypted trezor masked static public key: %s",
            hexlify_if_bytes(encrypted_trezor_static_public_key),
            iface=ctx.iface,
        )
        log.debug(__name__, "tag: %s", hexlify_if_bytes(tag), iface=ctx.iface)

    payload = trezor_ephemeral_public_key + encrypted_trezor_static_public_key + tag

    # send handshake init response message
    await ctx.write_encrypted_payload(HANDSHAKE_INIT_RES, payload)

    payload = await ctx.recv_payload(control_byte.is_handshake_comp_req)

    # will be `None` on USB interface, to be ignored by `cache_host_info()`
    mac_addr: AnyBytes | None = ctx.iface_ctx.connected_addr()

    await _check_unlocked()

    host_encrypted_static_public_key = payload[: KEY_LENGTH + TAG_LENGTH]
    handshake_completion_request_noise_payload = payload[KEY_LENGTH + TAG_LENGTH :]

    handshake.handle_th2_crypto(
        host_encrypted_static_public_key, handshake_completion_request_noise_payload
    )

    ctx.channel_cache.set(CHANNEL_KEY_RECEIVE, handshake.key_receive)
    ctx.channel_cache.set(CHANNEL_KEY_SEND, handshake.key_send)
    ctx.channel_cache.set(CHANNEL_HANDSHAKE_HASH, handshake.h)
    ctx.channel_cache.set_int(CHANNEL_NONCE_RECEIVE, 0)
    ctx.channel_cache.set_int(CHANNEL_NONCE_SEND, 1)

    buffer = payload[KEY_LENGTH + TAG_LENGTH : -TAG_LENGTH]

    payload_type = protobuf.type_for_name("ThpHandshakeCompletionReqNoisePayload")
    noise_payload = message_handler.wrap_protobuf_load(buffer, payload_type)

    if TYPE_CHECKING:
        assert ThpHandshakeCompletionReqNoisePayload.is_type_of(noise_payload)

    if __debug__:
        log.debug(
            __name__,
            "host static public key: %s, noise payload: %s",
            utils.hexlify_if_bytes(host_encrypted_static_public_key),
            utils.hexlify_if_bytes(handshake_completion_request_noise_payload),
            iface=ctx.iface,
        )

    # key is decoded in handshake._handle_th2_crypto
    host_static_public_key = host_encrypted_static_public_key[:PUBKEY_LENGTH]
    ctx.channel_cache.set_host_static_public_key(host_static_public_key)

    paired: bool = False
    trezor_state = _TREZOR_STATE_UNPAIRED

    if noise_payload.host_pairing_credential is not None:
        from apps.thp.credential_manager import decode_credential, validate_credential

        try:  # TODO change try-except for something better
            credential = decode_credential(noise_payload.host_pairing_credential)
            paired = validate_credential(
                credential,
                host_static_public_key,
            )
            if paired:
                from trezor.wire.thp.paired_cache import cache_host_info

                cache_host_info(
                    mac_addr=mac_addr,
                    host_name=credential.cred_metadata.host_name,
                    app_name=credential.cred_metadata.app_name,
                )
                trezor_state = _TREZOR_STATE_PAIRED
                ctx.credential = credential
                if ctx.is_channel_to_replace():
                    # When replacing existing channel, user confirmation is not needed
                    trezor_state = _TREZOR_STATE_PAIRED_AUTOCONNECT
            else:
                ctx.credential = None
        except DataError as e:
            if __debug__:
                log.exception(__name__, e, iface=ctx.iface)
            pass

    # send hanshake completion response
    response = handshake.get_handshake_completion_response(trezor_state)
    await ctx.write_encrypted_payload(HANDSHAKE_COMP_RES, response)

    if paired:
        ctx.set_channel_state(ChannelState.TC1)
    else:
        ctx.set_channel_state(ChannelState.TP0)


async def _handle_state_ENCRYPTED_TRANSPORT(ctx: Channel) -> None:
    if __debug__:
        log.debug(__name__, "handle_state_ENCRYPTED_TRANSPORT", iface=ctx.iface)

    session_id, message = await ctx.decrypt_message()
    if session_id not in ctx.sessions:

        s = session_manager.get_session_from_cache(ctx, session_id)

        if s is None:
            s = SeedlessSessionContext(ctx, session_id)

        ctx.sessions[session_id] = s

    elif ctx.sessions[session_id].get_session_state() is SessionState.UNALLOCATED:
        raise ThpUnallocatedSessionError(session_id)

    s = ctx.sessions[session_id]
    update_session_last_used(s.channel_id, (s.session_id).to_bytes(1, "big"))
    await s.handle(message)


async def _handle_pairing(ctx: Channel) -> None:
    from .pairing_context import PairingContext

    ctx.connection_context = PairingContext(ctx)

    _session_id, message = await ctx.decrypt_message()
    await ctx.connection_context.handle(message)


def _is_channel_state_pairing(state: int) -> bool:
    return state in (
        ChannelState.TP0,
        ChannelState.TP1,
        ChannelState.TP2,
        ChannelState.TP3,
        ChannelState.TP4,
        ChannelState.TC1,
    )
