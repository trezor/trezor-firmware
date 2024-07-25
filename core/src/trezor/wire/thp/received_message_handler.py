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
    update_channel_last_used,
    update_session_last_used,
)
from trezor import log, loop, utils
from trezor.enums import FailureType
from trezor.messages import Failure

from ..errors import DataError
from ..protocol_common import Message
from . import (
    ChannelState,
    SessionState,
    ThpDecryptionError,
    ThpError,
    ThpErrorType,
    ThpUnallocatedSessionError,
)
from . import alternating_bit_protocol as ABP
from . import checksum, control_byte, is_channel_state_pairing, thp_messages
from .checksum import CHECKSUM_LENGTH
from .crypto import PUBKEY_LENGTH, Handshake
from .thp_messages import (
    ACK_MESSAGE,
    HANDSHAKE_COMP_RES,
    HANDSHAKE_INIT_RES,
    PacketHeader,
)
from .writer import (
    INIT_HEADER_LENGTH,
    MESSAGE_TYPE_LENGTH,
    write_payload_to_wire_and_add_checksum,
)

if TYPE_CHECKING:
    from trezor.messages import ThpHandshakeCompletionReqNoisePayload

    from .channel import Channel

if __debug__:
    from ubinascii import hexlify

    from . import state_to_str


async def handle_received_message(
    ctx: Channel, message_buffer: utils.BufferType
) -> None:
    """Handle a message received from the channel."""

    if __debug__:
        log.debug(__name__, "handle_received_message")
    ctrl_byte, _, payload_length = ustruct.unpack(">BHH", message_buffer)
    message_length = payload_length + INIT_HEADER_LENGTH

    _check_checksum(message_length, message_buffer)

    # Synchronization process
    seq_bit = (ctrl_byte & 0x10) >> 4
    ack_bit = (ctrl_byte & 0x08) >> 3
    if __debug__:
        log.debug(
            __name__,
            "handle_completed_message - seq bit of message: %d, ack bit of message: %d",
            seq_bit,
            ack_bit,
        )
    # 0: Update "last-time used"
    update_channel_last_used(ctx.channel_id)

    # 1: Handle ACKs
    if control_byte.is_ack(ctrl_byte):
        await _handle_ack(ctx, ack_bit)
        return

    if _should_have_ctrl_byte_encrypted_transport(
        ctx
    ) and not control_byte.is_encrypted_transport(ctrl_byte):
        raise ThpError("Message is not encrypted. Ignoring")

    # 2: Handle message with unexpected sequential bit
    if seq_bit != ABP.get_expected_receive_seq_bit(ctx.channel_cache):
        if __debug__:
            log.debug(__name__, "Received message with an unexpected sequential bit")
        await _send_ack(ctx, ack_bit=seq_bit)
        raise ThpError("Received message with an unexpected sequential bit")

    # 3: Send ACK in response
    await _send_ack(ctx, ack_bit=seq_bit)

    ABP.set_expected_receive_seq_bit(ctx.channel_cache, 1 - seq_bit)

    try:
        await _handle_message_to_app_or_channel(
            ctx, payload_length, message_length, ctrl_byte
        )
    except ThpUnallocatedSessionError as e:
        error_message = Failure(code=FailureType.ThpUnallocatedSession)
        await ctx.write(error_message, e.session_id)
        print(e)
    except ThpDecryptionError as e:
        await ctx.write_error(ThpErrorType.DECRYPTION_FAILED)
        ctx.clear()
        print(e)
    if __debug__:
        log.debug(__name__, "handle_received_message - end")


async def _send_ack(ctx: Channel, ack_bit: int) -> None:
    ctrl_byte = control_byte.add_ack_bit_to_ctrl_byte(ACK_MESSAGE, ack_bit)
    header = PacketHeader(ctrl_byte, ctx.get_channel_id_int(), CHECKSUM_LENGTH)
    if __debug__:
        log.debug(
            __name__,
            "Writing ACK message to a channel with id: %d, ack_bit: %d",
            ctx.get_channel_id_int(),
            ack_bit,
        )
    await write_payload_to_wire_and_add_checksum(ctx.iface, header, b"")


def _check_checksum(message_length: int, message_buffer: utils.BufferType):
    if __debug__:
        log.debug(__name__, "check_checksum")
    if not checksum.is_valid(
        checksum=message_buffer[message_length - CHECKSUM_LENGTH : message_length],
        data=memoryview(message_buffer)[: message_length - CHECKSUM_LENGTH],
    ):
        if __debug__:
            log.debug(__name__, "Invalid checksum, ignoring message.")
        raise ThpError("Invalid checksum, ignoring message.")


async def _handle_ack(ctx: Channel, ack_bit: int):
    if not ABP.is_ack_valid(ctx.channel_cache, ack_bit):
        return
    # ACK is expected and it has correct sync bit
    if __debug__:
        log.debug(__name__, "Received ACK message with correct ack bit")
    if ctx.transmission_loop is not None:
        ctx.transmission_loop.stop_immediately()
        if __debug__:
            log.debug(__name__, "Stopped transmission loop")

    ABP.set_sending_allowed(ctx.channel_cache, True)

    if ctx.write_task_spawn is not None:
        if __debug__:
            log.debug(__name__, 'Control to "write_encrypted_payload_loop" task')
        await ctx.write_task_spawn
        # Note that no the write_task_spawn could result in loop.clear(),
        # which will result in termination of this function - any code after
        # this await might not be executed


async def _handle_message_to_app_or_channel(
    ctx: Channel,
    payload_length: int,
    message_length: int,
    ctrl_byte: int,
) -> None:
    state = ctx.get_channel_state()
    if __debug__:
        log.debug(__name__, "state: %s", state_to_str(state))

    if state is ChannelState.ENCRYPTED_TRANSPORT:
        await _handle_state_ENCRYPTED_TRANSPORT(ctx, message_length)
        return

    if state is ChannelState.TH1:
        await _handle_state_TH1(ctx, payload_length, message_length, ctrl_byte)
        return

    if state is ChannelState.TH2:
        await _handle_state_TH2(ctx, message_length, ctrl_byte)
        return

    if is_channel_state_pairing(state):
        await _handle_pairing(ctx, message_length)
        return

    raise ThpError("Unimplemented channel state")


async def _handle_state_TH1(
    ctx: Channel,
    payload_length: int,
    message_length: int,
    ctrl_byte: int,
) -> None:
    if __debug__:
        log.debug(__name__, "handle_state_TH1")
    if not control_byte.is_handshake_init_req(ctrl_byte):
        raise ThpError("Message received is not a handshake init request!")
    if not payload_length == PUBKEY_LENGTH + CHECKSUM_LENGTH:
        raise ThpError("Message received is not a valid handshake init request!")

    ctx.handshake = Handshake()

    host_ephemeral_pubkey = bytearray(
        ctx.buffer[INIT_HEADER_LENGTH : message_length - CHECKSUM_LENGTH]
    )
    trezor_ephemeral_pubkey, encrypted_trezor_static_pubkey, tag = (
        ctx.handshake.handle_th1_crypto(
            thp_messages.get_encoded_device_properties(), host_ephemeral_pubkey
        )
    )

    if __debug__:
        log.debug(
            __name__,
            "trezor ephemeral pubkey: %s",
            hexlify(trezor_ephemeral_pubkey).decode(),
        )
        log.debug(
            __name__,
            "trezor masked static pubkey: %s",
            hexlify(encrypted_trezor_static_pubkey).decode(),
        )
        log.debug(__name__, "tag: %s", hexlify(tag))

    payload = trezor_ephemeral_pubkey + encrypted_trezor_static_pubkey + tag

    # send handshake init response message
    await ctx.write_handshake_message(HANDSHAKE_INIT_RES, payload)
    ctx.set_channel_state(ChannelState.TH2)
    return


async def _handle_state_TH2(ctx: Channel, message_length: int, ctrl_byte: int) -> None:
    from apps.thp.credential_manager import validate_credential

    if __debug__:
        log.debug(__name__, "handle_state_TH2")
    if not control_byte.is_handshake_comp_req(ctrl_byte):
        raise ThpError("Message received is not a handshake completion request!")
    if ctx.handshake is None:
        raise Exception("Handshake object is not prepared. Retry handshake.")

    host_encrypted_static_pubkey = memoryview(ctx.buffer)[
        INIT_HEADER_LENGTH : INIT_HEADER_LENGTH + KEY_LENGTH + TAG_LENGTH
    ]
    handshake_completion_request_noise_payload = memoryview(ctx.buffer)[
        INIT_HEADER_LENGTH + KEY_LENGTH + TAG_LENGTH : message_length - CHECKSUM_LENGTH
    ]

    ctx.handshake.handle_th2_crypto(
        host_encrypted_static_pubkey, handshake_completion_request_noise_payload
    )

    ctx.channel_cache.set(CHANNEL_KEY_RECEIVE, ctx.handshake.key_receive)
    ctx.channel_cache.set(CHANNEL_KEY_SEND, ctx.handshake.key_send)
    ctx.channel_cache.set(CHANNEL_HANDSHAKE_HASH, ctx.handshake.h)
    ctx.channel_cache.set_int(CHANNEL_NONCE_RECEIVE, 0)
    ctx.channel_cache.set_int(CHANNEL_NONCE_SEND, 1)

    noise_payload = thp_messages.decode_message(
        ctx.buffer[
            INIT_HEADER_LENGTH
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
    for i in noise_payload.pairing_methods:
        if i not in ctx.selected_pairing_methods:
            ctx.selected_pairing_methods.append(i)
    if __debug__:
        log.debug(
            __name__,
            "host static pubkey: %s, noise payload: %s",
            utils.get_bytes_as_str(host_encrypted_static_pubkey),
            utils.get_bytes_as_str(handshake_completion_request_noise_payload),
        )

    # key is decoded in handshake._handle_th2_crypto
    host_static_pubkey = host_encrypted_static_pubkey[:PUBKEY_LENGTH]

    paired: bool = False

    if noise_payload.host_pairing_credential is not None:
        try:  # TODO change try-except for something better
            paired = validate_credential(
                noise_payload.host_pairing_credential,
                host_static_pubkey,
            )
        except DataError as e:
            if __debug__:
                log.exception(__name__, e)
            pass

    trezor_state = thp_messages.TREZOR_STATE_UNPAIRED
    if paired:
        trezor_state = thp_messages.TREZOR_STATE_PAIRED
    # send hanshake completion response
    await ctx.write_handshake_message(
        HANDSHAKE_COMP_RES,
        ctx.handshake.get_handshake_completion_response(trezor_state),
    )

    ctx.handshake = None

    if paired:
        ctx.set_channel_state(ChannelState.ENCRYPTED_TRANSPORT)
    else:
        ctx.set_channel_state(ChannelState.TP1)


async def _handle_state_ENCRYPTED_TRANSPORT(ctx: Channel, message_length: int) -> None:
    if __debug__:
        log.debug(__name__, "handle_state_ENCRYPTED_TRANSPORT")

    ctx.decrypt_buffer(message_length)
    session_id, message_type = ustruct.unpack(
        ">BH", memoryview(ctx.buffer)[INIT_HEADER_LENGTH:]
    )
    if session_id not in ctx.sessions:
        raise ThpUnallocatedSessionError(session_id)

    session_state = ctx.sessions[session_id].get_session_state()
    if session_state is SessionState.UNALLOCATED:
        raise ThpUnallocatedSessionError(session_id)
    update_session_last_used(ctx.channel_id, session_id)
    ctx.sessions[session_id].incoming_message.publish(
        Message(
            message_type,
            ctx.buffer[
                INIT_HEADER_LENGTH
                + MESSAGE_TYPE_LENGTH
                + SESSION_ID_LENGTH : message_length
                - CHECKSUM_LENGTH
                - TAG_LENGTH
            ],
        )
    )


async def _handle_pairing(ctx: Channel, message_length: int) -> None:
    from .pairing_context import PairingContext

    if ctx.connection_context is None:
        ctx.connection_context = PairingContext(ctx)
        loop.schedule(ctx.connection_context.handle())

    ctx.decrypt_buffer(message_length)
    message_type = ustruct.unpack(
        ">H", ctx.buffer[INIT_HEADER_LENGTH + SESSION_ID_LENGTH :]
    )[0]

    ctx.connection_context.incoming_message.publish(
        Message(
            message_type,
            ctx.buffer[
                INIT_HEADER_LENGTH
                + MESSAGE_TYPE_LENGTH
                + SESSION_ID_LENGTH : message_length
                - CHECKSUM_LENGTH
                - TAG_LENGTH
            ],
        )
    )


def _should_have_ctrl_byte_encrypted_transport(ctx: Channel) -> bool:
    if ctx.get_channel_state() in [
        ChannelState.UNALLOCATED,
        ChannelState.TH1,
        ChannelState.TH2,
    ]:
        return False
    return True
