import ustruct
from typing import TYPE_CHECKING

from storage.cache_common import (
    CHANNEL_HANDSHAKE_HASH,
    CHANNEL_KEY_RECEIVE,
    CHANNEL_KEY_SEND,
    CHANNEL_NONCE_RECEIVE,
    CHANNEL_NONCE_SEND,
)
from storage.cache_thp import (
    KEY_LENGTH,
    SESSION_ID_LENGTH,
    TAG_LENGTH,
    update_session_last_used,
)
from trezor import config, loop, protobuf, utils
from trezor.enums import FailureType
from trezor.messages import Failure
from trezor.wire.thp import memory_manager

from .. import message_handler
from ..errors import DataError
from ..protocol_common import Message
from . import (
    ACK_MESSAGE,
    HANDSHAKE_COMP_RES,
    HANDSHAKE_INIT_RES,
    ChannelState,
    PacketHeader,
    SessionState,
    ThpDecryptionError,
    ThpDeviceLockedError,
    ThpError,
    ThpErrorType,
    ThpInvalidDataError,
    ThpUnallocatedChannelError,
    ThpUnallocatedSessionError,
)
from . import alternating_bit_protocol as ABP
from . import control_byte, get_encoded_device_properties, session_manager
from .checksum import CHECKSUM_LENGTH
from .crypto import PUBKEY_LENGTH, Handshake
from .session_context import SeedlessSessionContext
from .writer import MESSAGE_TYPE_LENGTH

if TYPE_CHECKING:
    from typing import Awaitable

    from trezor.messages import ThpHandshakeCompletionReqNoisePayload

    from .channel import Channel

if __debug__:
    from trezor import log
    from trezor.utils import hexlify_if_bytes

_TREZOR_STATE_UNPAIRED = b"\x00"
_TREZOR_STATE_PAIRED = b"\x01"
_TREZOR_STATE_PAIRED_AUTOCONNECT = b"\x02"


async def handle_received_message(ctx: Channel) -> None:
    """Handle a message received from the channel."""

    try:
        await _handle_message_to_app_or_channel(ctx)
    except ThpUnallocatedSessionError as e:
        error_message = Failure(code=FailureType.ThpUnallocatedSession)
        await ctx.write(error_message, e.session_id)
    except ThpUnallocatedChannelError:
        await ctx.write_error(ThpErrorType.UNALLOCATED_CHANNEL)
        ctx.clear()
    except ThpDecryptionError:
        await ctx.write_error(ThpErrorType.DECRYPTION_FAILED)
        ctx.clear()
    except ThpInvalidDataError:
        await ctx.write_error(ThpErrorType.INVALID_DATA)
        ctx.clear()
    except ThpDeviceLockedError:
        await ctx.write_error(ThpErrorType.DEVICE_LOCKED)

    if __debug__:
        log.debug(__name__, "handle_received_message - end", iface=ctx.iface)


def _send_ack(channel: Channel, ack_bit: int) -> Awaitable[None]:
    ctrl_byte = control_byte.add_ack_bit_to_ctrl_byte(ACK_MESSAGE, ack_bit)
    header = PacketHeader(ctrl_byte, channel.get_channel_id_int(), CHECKSUM_LENGTH)
    if __debug__:
        log.debug(
            __name__,
            "Writing ACK message to a channel with cid: %s, ack_bit: %d",
            hexlify_if_bytes(channel.channel_id),
            ack_bit,
            iface=channel.iface,
        )
    return channel.ctx.write_payload(header, b"")


def handle_ack(ctx: Channel, ack_bit: int) -> None:
    if not ABP.is_ack_valid(ctx.channel_cache, ack_bit):
        return
    # ACK is expected and it has correct sync bit
    if __debug__:
        log.debug(
            __name__,
            "Received ACK message with correct ack bit",
            iface=ctx.iface,
        )
    ABP.set_sending_allowed(ctx.channel_cache, True)


def _handle_message_to_app_or_channel(ctx: Channel) -> Awaitable[None]:
    state = ctx.get_channel_state()

    if state == ChannelState.ENCRYPTED_TRANSPORT:
        return _handle_state_ENCRYPTED_TRANSPORT(ctx)

    if state == ChannelState.TH1:
        return _handle_state_handshake(ctx)

    if _is_channel_state_pairing(state):
        return _handle_pairing(ctx)

    raise ThpError("Unimplemented channel state")


async def _handle_state_handshake(
    ctx: Channel,
) -> None:
    if __debug__:
        log.debug(__name__, "handle_state_TH1", iface=ctx.iface)
    msg = await ctx.recv_message()
    message_length = len(msg)
    ctrl_byte, _, payload_length = ustruct.unpack(">BHH", msg)

    if not control_byte.is_handshake_init_req(ctrl_byte):
        raise ThpError("Message received is not a handshake init request!")

    if not payload_length == PUBKEY_LENGTH + CHECKSUM_LENGTH:
        raise ThpError("Message received is not a valid handshake init request!")

    if not config.is_unlocked():
        raise ThpDeviceLockedError

    ctx.handshake = Handshake()

    buffer = memory_manager.get_existing_read_buffer(ctx.get_channel_id_int())
    # if buffer is BufferError:
    # pass  # TODO buffer is gone :/

    host_ephemeral_public_key = bytearray(
        buffer[PacketHeader.INIT_LENGTH : message_length - CHECKSUM_LENGTH]
    )
    trezor_ephemeral_public_key, encrypted_trezor_static_public_key, tag = (
        ctx.handshake.handle_th1_crypto(
            get_encoded_device_properties(ctx.iface), host_ephemeral_public_key
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
    await ctx.write_handshake_message(HANDSHAKE_INIT_RES, payload)

    msg = await ctx.recv_message()
    message_length = len(msg)
    ctrl_byte, _, payload_length = ustruct.unpack(">BHH", msg)

    if not control_byte.is_handshake_comp_req(ctrl_byte):
        raise ThpError("Message received is not a handshake completion request!")

    if ctx.handshake is None:
        raise ThpUnallocatedChannelError(
            "Handshake object is not prepared. Create new channel."
        )

    if not config.is_unlocked():
        raise ThpDeviceLockedError

    buffer = memory_manager.get_existing_read_buffer(ctx.get_channel_id_int())
    # if buffer is BufferError:
    # pass  # TODO handle
    host_encrypted_static_public_key = buffer[
        PacketHeader.INIT_LENGTH : PacketHeader.INIT_LENGTH + KEY_LENGTH + TAG_LENGTH
    ]
    handshake_completion_request_noise_payload = buffer[
        PacketHeader.INIT_LENGTH
        + KEY_LENGTH
        + TAG_LENGTH : message_length
        - CHECKSUM_LENGTH
    ]

    ctx.handshake.handle_th2_crypto(
        host_encrypted_static_public_key, handshake_completion_request_noise_payload
    )

    ctx.channel_cache.set(CHANNEL_KEY_RECEIVE, ctx.handshake.key_receive)
    ctx.channel_cache.set(CHANNEL_KEY_SEND, ctx.handshake.key_send)
    ctx.channel_cache.set(CHANNEL_HANDSHAKE_HASH, ctx.handshake.h)
    ctx.channel_cache.set_int(CHANNEL_NONCE_RECEIVE, 0)
    ctx.channel_cache.set_int(CHANNEL_NONCE_SEND, 1)

    noise_payload = _decode_message(
        buffer[
            PacketHeader.INIT_LENGTH
            + KEY_LENGTH
            + TAG_LENGTH : message_length
            - CHECKSUM_LENGTH
            - TAG_LENGTH
        ],
        0,
        "ThpHandshakeCompletionReqNoisePayload",
    )
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
    ctx.channel_cache.set_host_static_public_key(bytearray(host_static_public_key))

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
                trezor_state = _TREZOR_STATE_PAIRED
                ctx.credential = credential
            else:
                ctx.credential = None
        except DataError as e:
            if __debug__:
                log.exception(__name__, e, iface=ctx.iface)
            pass

    # send hanshake completion response
    await ctx.write_handshake_message(
        HANDSHAKE_COMP_RES,
        ctx.handshake.get_handshake_completion_response(trezor_state),
    )

    ctx.handshake = None

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


def _should_have_ctrl_byte_encrypted_transport(ctx: Channel) -> bool:
    return ctx.get_channel_state() not in (
        ChannelState.UNALLOCATED,
        ChannelState.TH1,
        ChannelState.TH2,
    )


def _decode_message(
    buffer: bytes,
    msg_type: int,
    message_name: str | None = None,
    wire_enum: str = "ThpMessageType",
) -> protobuf.MessageType:
    if __debug__:
        log.debug(__name__, "decode message")
    if message_name is not None:
        expected_type = protobuf.type_for_name(message_name)
    else:
        expected_type = protobuf.type_for_wire(wire_enum, msg_type)
    return message_handler.wrap_protobuf_load(buffer, expected_type)


def _is_channel_state_pairing(state: int) -> bool:
    return state in (
        ChannelState.TP0,
        ChannelState.TP1,
        ChannelState.TP2,
        ChannelState.TP3,
        ChannelState.TP4,
        ChannelState.TC1,
    )
