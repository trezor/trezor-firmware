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
    TAG_LENGTH,
    update_channel_last_used,
    update_session_last_used,
)
from trezor import config, protobuf, utils
from trezor.enums import FailureType
from trezor.messages import Failure

from .. import message_handler
from ..errors import DataError
from . import (
    ACK_MESSAGE,
    HANDSHAKE_COMP_RES,
    HANDSHAKE_INIT_RES,
    ChannelState,
    PacketHeader,
    ThpDecryptionError,
    ThpDeviceLockedError,
    ThpError,
    ThpErrorType,
    ThpInvalidDataError,
    ThpUnallocatedChannelError,
    ThpUnallocatedSessionError,
)
from . import alternating_bit_protocol as ABP
from . import checksum, control_byte, get_encoded_device_properties, session_manager
from .checksum import CHECKSUM_LENGTH
from .crypto import PUBKEY_LENGTH, Handshake
from .session_context import SeedlessSessionContext
from .writer import INIT_HEADER_LENGTH, write_payload_to_wire_and_add_checksum

if TYPE_CHECKING:
    from typing import Awaitable

    from trezor.messages import ThpHandshakeCompletionReqNoisePayload

    from .channel import Channel
    from .thp_main import ThpContext

if __debug__:
    from trezor import log
    from trezor.utils import hexlify_if_bytes

_TREZOR_STATE_UNPAIRED = b"\x00"
_TREZOR_STATE_PAIRED = b"\x01"
_TREZOR_STATE_PAIRED_AUTOCONNECT = b"\x02"


async def handle_checksum_and_acks(ctx: Channel) -> bool:
    """Verify checksum, handle ACKs or return the message"""
    message_buffer = ctx.rx_buffer
    ctrl_byte, _, payload_length = ustruct.unpack(">BHH", message_buffer)
    message_length = payload_length + INIT_HEADER_LENGTH

    _check_checksum(message_length, message_buffer)

    # Synchronization process
    seq_bit = control_byte.get_seq_bit(ctrl_byte)
    ack_bit = control_byte.get_ack_bit(ctrl_byte)
    if __debug__:
        log.debug(
            __name__,
            "handle_completed_message - seq bit of message: %d, ack bit of message: %d",
            seq_bit,
            ack_bit,
            iface=ctx.iface,
        )
    # 0: Update "last-time used"
    update_channel_last_used(ctx.channel_id)

    # 1: Handle ACKs
    if control_byte.is_ack(ctrl_byte):
        await handle_ack(ctx, ack_bit)
        return False  # no data is received

    if _should_have_ctrl_byte_encrypted_transport(
        ctx
    ) and not control_byte.is_encrypted_transport(ctrl_byte):
        raise ThpError("Message is not encrypted. Ignoring")

    # 2: Handle message with unexpected sequential bit
    if seq_bit != ABP.get_expected_receive_seq_bit(ctx.channel_cache):
        if __debug__:
            log.debug(
                __name__,
                "Received message with an unexpected sequential bit",
                iface=ctx.iface,
            )
        await _send_ack(ctx, ack_bit=seq_bit)
        raise ThpError("Received message with an unexpected sequential bit")

    # 3: Send ACK in response
    await _send_ack(ctx, ack_bit=seq_bit)

    ABP.set_expected_receive_seq_bit(ctx.channel_cache, 1 - seq_bit)
    return True  # a message was received and ACKed


async def handle_received_message(ctx: ThpContext) -> None:
    """Handle a message received from the channel."""

    try:
        await _handle_message_to_app_or_channel(ctx)
    except ThpUnallocatedSessionError as e:
        error_message = Failure(code=FailureType.ThpUnallocatedSession)
        await ctx.channel.write(error_message, e.session_id)
    except ThpUnallocatedChannelError:
        await ctx.channel.write_error(ThpErrorType.UNALLOCATED_CHANNEL)
        ctx.channel.clear()
    except ThpDecryptionError:
        await ctx.channel.write_error(ThpErrorType.DECRYPTION_FAILED)
        ctx.channel.clear()
    except ThpInvalidDataError:
        await ctx.channel.write_error(ThpErrorType.INVALID_DATA)
        ctx.channel.clear()
    except ThpDeviceLockedError:
        await ctx.channel.write_error(ThpErrorType.DEVICE_LOCKED)


def _send_ack(ctx: Channel, ack_bit: int) -> Awaitable[None]:
    ctrl_byte = control_byte.add_ack_bit_to_ctrl_byte(ACK_MESSAGE, ack_bit)
    header = PacketHeader(ctrl_byte, ctx.get_channel_id_int(), CHECKSUM_LENGTH)
    if __debug__:
        log.debug(
            __name__,
            "Writing ACK message to a channel with cid: %s, ack_bit: %d",
            hexlify_if_bytes(ctx.channel_id),
            ack_bit,
            iface=ctx.iface,
        )
    return write_payload_to_wire_and_add_checksum(ctx.iface, header, b"")


def _check_checksum(message_length: int, message_buffer: utils.BufferType) -> None:
    if __debug__:
        log.debug(__name__, "check_checksum")
    if not checksum.is_valid(
        checksum=message_buffer[message_length - CHECKSUM_LENGTH : message_length],
        data=memoryview(message_buffer)[: message_length - CHECKSUM_LENGTH],
    ):
        if __debug__:
            log.debug(__name__, "Invalid checksum, ignoring message.")
        raise ThpError("Invalid checksum, ignoring message.")


async def handle_ack(ctx: Channel, ack_bit: int) -> None:
    if not ABP.is_ack_valid(ctx.channel_cache, ack_bit):
        return
    # ACK is expected and it has correct sync bit
    if __debug__:
        log.debug(
            __name__,
            "Received ACK message with correct ack bit",
            iface=ctx.iface,
        )
    if ctx.transmission_loop is not None:
        ctx.transmission_loop.stop_immediately()
        if __debug__:
            log.debug(__name__, "Stopped transmission loop", iface=ctx.iface)

    ABP.set_sending_allowed(ctx.channel_cache, True)
    ABP.set_send_seq_bit_to_opposite(ctx.channel_cache)

    if ctx.write_task_spawn is not None:
        if __debug__:
            log.debug(
                __name__,
                'Control to "write_encrypted_payload_loop" task',
                iface=ctx.iface,
            )
        await ctx.write_task_spawn


async def _handle_message_to_app_or_channel(ctx: ThpContext) -> None:
    if ctx.channel.get_channel_state() == ChannelState.ENCRYPTED_TRANSPORT:
        await _handle_state_ENCRYPTED_TRANSPORT(ctx)
    else:
        assert ctx.channel.get_channel_state() == ChannelState.TH1
        await _handle_state_TH1(ctx)

        assert ctx.channel.get_channel_state() == ChannelState.TH2
        await _handle_state_TH2(ctx)

        assert _is_channel_state_pairing(ctx.channel.get_channel_state())
        await _handle_pairing(ctx)


async def _handle_state_TH1(ctx: ThpContext) -> None:
    if __debug__:
        log.debug(__name__, "handle_state_TH1", iface=ctx.channel.iface)
    message = await ctx.read()  # & ACK received message
    if not control_byte.is_handshake_init_req(message[0]):
        raise ThpError("Message received is not a handshake init request!")
    if len(message) != INIT_HEADER_LENGTH + PUBKEY_LENGTH + CHECKSUM_LENGTH:
        raise ThpError("Message received is not a valid handshake init request!")

    if not config.is_unlocked():
        raise ThpDeviceLockedError

    ctx.channel.handshake = Handshake()

    host_ephemeral_public_key = bytes(
        message[INIT_HEADER_LENGTH : len(message) - CHECKSUM_LENGTH]
    )
    trezor_ephemeral_public_key, encrypted_trezor_static_public_key, tag = (
        ctx.channel.handshake.handle_th1_crypto(
            get_encoded_device_properties(ctx.channel.iface), host_ephemeral_public_key
        )
    )

    if __debug__:
        log.debug(
            __name__,
            "trezor ephemeral public key: %s",
            hexlify_if_bytes(trezor_ephemeral_public_key),
            iface=ctx.channel.iface,
        )
        log.debug(
            __name__,
            "encrypted trezor masked static public key: %s",
            hexlify_if_bytes(encrypted_trezor_static_public_key),
            iface=ctx.channel.iface,
        )
        log.debug(__name__, "tag: %s", hexlify_if_bytes(tag), iface=ctx.channel.iface)

    payload = trezor_ephemeral_public_key + encrypted_trezor_static_public_key + tag

    # send handshake init response message
    # TODO: ACK+retry
    await ctx.channel.send_payload(HANDSHAKE_INIT_RES, payload)
    await ctx.wait_for_ack()
    ctx.channel.set_channel_state(ChannelState.TH2)
    return


async def _handle_state_TH2(ctx: ThpContext) -> None:
    from apps.thp.credential_manager import decode_credential, validate_credential

    if __debug__:
        log.debug(__name__, "handle_state_TH2", iface=ctx.channel.iface)
    message = await ctx.read()  # & ACK received message
    if not control_byte.is_handshake_comp_req(message[0]):
        raise ThpError("Message received is not a handshake completion request!")

    if ctx.channel.handshake is None:
        raise ThpUnallocatedChannelError(
            "Handshake object is not prepared. Create new channel."
        )

    if not config.is_unlocked():
        raise ThpDeviceLockedError

    host_encrypted_static_public_key = message[
        INIT_HEADER_LENGTH : INIT_HEADER_LENGTH + KEY_LENGTH + TAG_LENGTH
    ]
    handshake_completion_request_noise_payload = message[
        INIT_HEADER_LENGTH + KEY_LENGTH + TAG_LENGTH : len(message) - CHECKSUM_LENGTH
    ]

    ctx.channel.handshake.handle_th2_crypto(
        host_encrypted_static_public_key, handshake_completion_request_noise_payload
    )

    ctx.channel.channel_cache.set(
        CHANNEL_KEY_RECEIVE, ctx.channel.handshake.key_receive
    )
    ctx.channel.channel_cache.set(CHANNEL_KEY_SEND, ctx.channel.handshake.key_send)
    ctx.channel.channel_cache.set(CHANNEL_HANDSHAKE_HASH, ctx.channel.handshake.h)
    ctx.channel.channel_cache.set_int(CHANNEL_NONCE_RECEIVE, 0)
    ctx.channel.channel_cache.set_int(CHANNEL_NONCE_SEND, 1)

    noise_payload = _decode_message(
        message[
            INIT_HEADER_LENGTH
            + KEY_LENGTH
            + TAG_LENGTH : len(message)
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
            iface=ctx.channel.iface,
        )

    # key is decoded in handshake._handle_th2_crypto
    host_static_public_key = host_encrypted_static_public_key[:PUBKEY_LENGTH]
    ctx.channel.channel_cache.set_host_static_public_key(
        bytearray(host_static_public_key)
    )

    paired: bool = False
    trezor_state = _TREZOR_STATE_UNPAIRED

    if noise_payload.host_pairing_credential is not None:
        try:  # TODO change try-except for something better
            credential = decode_credential(noise_payload.host_pairing_credential)
            paired = validate_credential(
                credential,
                host_static_public_key,
            )
            if paired:
                trezor_state = _TREZOR_STATE_PAIRED
                ctx.channel.credential = credential
            else:
                ctx.channel.credential = None
        except DataError as e:
            if __debug__:
                log.exception(__name__, e, iface=ctx.channel.iface)
            pass

    # send hanshake completion response
    # TODO: ACK+retry
    await ctx.channel.send_payload(
        HANDSHAKE_COMP_RES,
        ctx.channel.handshake.get_handshake_completion_response(trezor_state),
    )
    await ctx.wait_for_ack()

    ctx.channel.handshake = None

    if paired:
        ctx.channel.set_channel_state(ChannelState.TC1)
    else:
        ctx.channel.set_channel_state(ChannelState.TP0)


async def _handle_state_ENCRYPTED_TRANSPORT(ctx: ThpContext) -> None:
    if __debug__:
        log.debug(__name__, "handle_state_ENCRYPTED_TRANSPORT", iface=ctx.channel.iface)

    session_id, message = await ctx.decrypt()

    s = session_manager.get_session_from_cache(ctx, session_id)
    if s is None:
        s = SeedlessSessionContext(ctx, session_id)

    update_session_last_used(s.channel_id, (s.session_id).to_bytes(1, "big"))
    await s.handle(message)


async def _handle_pairing(ctx: ThpContext) -> None:
    from .pairing_context import PairingContext

    channel = ctx.channel
    channel.connection_context = PairingContext(channel, ctx)
    await channel.connection_context.handle()  # will read and write message on its own


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
