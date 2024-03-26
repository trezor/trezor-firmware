import ustruct  # pyright: ignore[reportMissingModuleSource]
from micropython import const  # pyright: ignore[reportMissingModuleSource]
from typing import TYPE_CHECKING  # pyright: ignore[reportShadowedImports]

from storage.cache_thp import BROADCAST_CHANNEL_ID, SessionThpCache
from trezor import io, log, loop, utils

from .protocol_common import MessageWithId
from .thp import ChannelState, ack_handler, checksum, thp_messages
from .thp import thp_session as THP
from .thp.channel_context import (
    _MAX_PAYLOAD_LEN,
    _REPORT_LENGTH,
    ChannelContext,
    load_cached_channels,
)
from .thp.checksum import CHECKSUM_LENGTH
from .thp.thp_messages import (
    CODEC_V1,
    CONTINUATION_PACKET,
    ENCRYPTED_TRANSPORT,
    CONT_DATA_OFFSET,
    INIT_DATA_OFFSET,
    InitHeader,
    InterruptingInitPacket,
)
from .thp.thp_session import SessionState, ThpError

if TYPE_CHECKING:
    from trezorio import WireInterface  # pyright: ignore[reportMissingImports]

_MAX_CID_REQ_PAYLOAD_LENGTH = const(12)  # TODO set to reasonable value
_CHANNEL_ALLOCATION_REQ = 0x40
_ACK_MESSAGE = 0x20
_PLAINTEXT = 0x01


_BUFFER: bytearray
_BUFFER_LOCK = None

_CHANNEL_CONTEXTS: dict[int, ChannelContext] = {}


async def read_message(iface: WireInterface, buffer: utils.BufferType) -> MessageWithId:
    msg = await read_message_or_init_packet(iface, buffer)
    while type(msg) is not MessageWithId:
        if isinstance(msg, InterruptingInitPacket):
            msg = await read_message_or_init_packet(iface, buffer, msg.initReport)
        else:
            raise ThpError("Unexpected output of read_message_or_init_packet:")
    return msg


def set_buffer(buffer):
    _BUFFER = buffer
    print(_BUFFER)  # TODO remove


async def thp_main_loop(iface: WireInterface, is_debug_session=False):
    global _CHANNEL_CONTEXTS
    _CHANNEL_CONTEXTS = load_cached_channels()

    read = loop.wait(iface.iface_num() | io.POLL_READ)

    while True:
        packet = await read
        ctrl_byte, cid = ustruct.unpack(">BH", packet)

        if ctrl_byte == CODEC_V1:
            pass
            # TODO add handling of (unsupported) codec_v1 packets
            # possibly ignore continuation packets, i.e. if the
            # following bytes are not "##"", do not respond

        if cid == BROADCAST_CHANNEL_ID:
            # TODO handle exceptions, try-catch?
            await _handle_broadcast(iface, ctrl_byte, packet)
            continue

        if cid in _CHANNEL_CONTEXTS:
            channel = _CHANNEL_CONTEXTS[cid]
            if channel is None:
                raise ThpError("Invalid state of a channel")
            if channel.iface is not iface:
                raise ThpError("Channel has different WireInterface")

            if channel.get_channel_state() != ChannelState.UNALLOCATED:
                await channel.receive_packet(packet)
                continue

        await _handle_unallocated(iface, cid)
        # TODO add cleaning sequence if no workflow/channel is active (or some condition like that)


async def read_message_or_init_packet(
    iface: WireInterface, buffer: utils.BufferType, firstReport: bytes | None = None
) -> MessageWithId | InterruptingInitPacket:
    report = firstReport
    while True:
        # Wait for an initial report
        if report is None:
            report = await _get_loop_wait_read(iface)
        if report is None:
            raise ThpError("Reading failed unexpectedly, report is None.")

        # Channel multiplexing
        ctrl_byte, cid = ustruct.unpack(">BH", report)

        if cid == BROADCAST_CHANNEL_ID:
            await _handle_broadcast(iface, ctrl_byte, report)
            report = None
            continue

        # We allow for only one message to be read simultaneously. We do not
        # support reading multiple messages with interleaven packets - with
        # the sole exception of cid_request which can be handled independently.
        if _is_ctrl_byte_continuation(ctrl_byte):
            # continuation packet is not expected - ignore
            if __debug__:
                log.debug(__name__, "Received unexpected continuation packet")
            report = None
            continue
        payload_length = ustruct.unpack(">H", report[3:])[0]
        payload = _get_buffer_for_payload(payload_length, buffer)
        header = InitHeader(ctrl_byte, cid, payload_length)

        # buffer the received data
        interruptingPacket = await _buffer_received_data(payload, header, iface, report)
        if interruptingPacket is not None:
            return interruptingPacket

        # Check CRC
        if not checksum.is_valid(payload[-4:], header.to_bytes() + payload[:-4]):
            # checksum is not valid -> ignore message
            report = None
            continue

        session = THP.get_session(iface, cid)
        session_state = THP.get_state(session)

        # Handle message on unallocated channel
        if session_state == SessionState.UNALLOCATED:
            message = await _handle_unallocated(iface, cid)
            # unallocated should not return regular message, TODO, but it might change
            if __debug__:
                log.debug(__name__, "Channel with id: %d in UNALLOCATED", cid)
            if message is not None:
                return message
            report = None
            continue

        if session is None:
            raise ThpError("Invalid session!")

        # Note: In the Host, the UNALLOCATED_CHANNEL error should be handled here

        # Synchronization process
        sync_bit = (ctrl_byte & 0x10) >> 4

        # 1: Handle ACKs
        if _is_ctrl_byte_ack(ctrl_byte):
            ack_handler.handle_received_ACK(session, sync_bit)
            report = None
            continue

        # 2: Handle message with unexpected synchronization bit
        if sync_bit != THP.sync_get_receive_expected_bit(session):
            message = await _handle_unexpected_sync_bit(iface, cid, sync_bit)
            # unsynchronized messages should not return regular message, TODO,
            # but it might change with the cancelation message
            if message is not None:
                return message
            report = None
            continue

        # 3: Send ACK in response
        if __debug__:
            log.debug(
                __name__,
                "Writing ACK message to a channel with id: %d, sync bit: %d",
                cid,
                sync_bit,
            )
        await _sendAck(iface, cid, sync_bit)
        THP.sync_set_receive_expected_bit(session, 1 - sync_bit)

        return await _handle_allocated(ctrl_byte, session, payload)


def _get_loop_wait_read(iface: WireInterface):
    return loop.wait(iface.iface_num() | io.POLL_READ)


def _get_buffer_for_payload(
    payload_length: int, existing_buffer: utils.BufferType, max_length=_MAX_PAYLOAD_LEN
) -> utils.BufferType:
    if payload_length > max_length:
        raise ThpError("Message too large")
    if payload_length > len(existing_buffer):
        # allocate a new buffer to fit the message
        try:
            payload: utils.BufferType = bytearray(payload_length)
        except MemoryError:
            payload = bytearray(_REPORT_LENGTH)
            raise ThpError("Message too large")
        return payload

    # reuse a part of the supplied buffer
    return memoryview(existing_buffer)[:payload_length]


async def _buffer_received_data(
    payload: utils.BufferType, header: InitHeader, iface, report
) -> None | InterruptingInitPacket:
    # buffer the initial data
    nread = utils.memcpy(payload, 0, report, INIT_DATA_OFFSET)
    while nread < header.length:
        # wait for continuation report
        report = await _get_loop_wait_read(iface)

        # channel multiplexing
        cont_ctrl_byte, cont_cid = ustruct.unpack(">BH", report)

        # handle broadcast - allows the reading process
        # to survive interruption by broadcast
        if cont_cid == BROADCAST_CHANNEL_ID:
            await _handle_broadcast(iface, cont_ctrl_byte, report)
            continue

        # handle unexpected initiation packet
        if not _is_ctrl_byte_continuation(cont_ctrl_byte):
            # TODO possibly add timeout - allow interruption only after a long time
            return InterruptingInitPacket(report)

        # ignore continuation packets on different channels
        if cont_cid != header.cid:
            continue

        # buffer the continuation data
        nread += utils.memcpy(payload, nread, report, CONT_DATA_OFFSET)


async def write_message_with_sync_control(
    iface: WireInterface, message: MessageWithId, is_retransmission: bool = False
) -> None:
    session = THP.get_session_from_id(message.session_id)
    if session is None:
        raise ThpError("Invalid session")
    if (not THP.sync_can_send_message(session)) and (not is_retransmission):
        raise ThpError("Cannot send another message before ACK is received.")
    await write_message(iface, message, is_retransmission)


async def write_message(
    iface: WireInterface, message: MessageWithId, is_retransmission: bool = False
) -> None:
    session = THP.get_session_from_id(message.session_id)
    if session is None:
        raise ThpError("Invalid session")

    cid = THP.get_cid(session)
    payload = message.type.to_bytes(2, "big") + message.data
    payload_length = len(payload)

    if THP.get_state(session) == SessionState.INITIALIZED:
        # write message in plaintext, TODO check if it is allowed
        ctrl_byte = _PLAINTEXT
    elif THP.get_state(session) == SessionState.APP_TRAFFIC:
        ctrl_byte = ENCRYPTED_TRANSPORT
    else:
        raise ThpError("Session in not implemented state" + str(THP.get_state(session)))

    if not is_retransmission:
        ctrl_byte = _add_sync_bit_to_ctrl_byte(
            ctrl_byte, THP.sync_get_send_bit(session)
        )
        THP.sync_set_send_bit_to_opposite(session)
    else:
        # retransmission must have the same sync bit as the previously sent message
        ctrl_byte = _add_sync_bit_to_ctrl_byte(
            ctrl_byte, 1 - THP.sync_get_send_bit(session)
        )

    header = InitHeader(ctrl_byte, cid, payload_length + CHECKSUM_LENGTH)
    chksum = checksum.compute(header.to_bytes() + payload)
    if __debug__ and message.session_id is not None:
        log.debug(
            __name__,
            "Writing message with type %d to a session %d",
            message.type,
            int.from_bytes(message.session_id, "big"),
        )
    await write_to_wire(iface, header, payload + chksum)
    # TODO set timeout for retransmission


async def write_to_wire(
    iface: WireInterface, header: InitHeader, payload: bytes
) -> None:
    loop_write = loop.wait(iface.iface_num() | io.POLL_WRITE)

    payload_length = len(payload)

    # prepare the report buffer with header data
    report = bytearray(_REPORT_LENGTH)
    header.pack_to_buffer(report)

    # write initial report
    nwritten = utils.memcpy(report, INIT_DATA_OFFSET, payload, 0)
    await _write_report(loop_write, iface, report)

    # if we have more data to write, use continuation reports for it
    if nwritten < payload_length:
        header.pack_to_cont_buffer(report)

    while nwritten < payload_length:
        nwritten += utils.memcpy(report, CONT_DATA_OFFSET, payload, nwritten)
        await _write_report(loop_write, iface, report)


async def _write_report(write, iface: WireInterface, report: bytearray) -> None:
    while True:
        await write
        n = iface.write(report)
        if n == len(report):
            return


async def _handle_broadcast(
    iface: WireInterface, ctrl_byte, packet
) -> MessageWithId | None:
    if ctrl_byte != _CHANNEL_ALLOCATION_REQ:
        raise ThpError("Unexpected ctrl_byte in broadcast channel packet")
    if __debug__:
        log.debug(__name__, "Received valid message on broadcast channel ")

    length, nonce = ustruct.unpack(">H8s", packet[3:])
    header = InitHeader(ctrl_byte, BROADCAST_CHANNEL_ID, length)
    payload = _get_buffer_for_payload(length, packet[5:], _MAX_CID_REQ_PAYLOAD_LENGTH)

    if not checksum.is_valid(payload[-4:], header.to_bytes() + payload[:-4]):
        raise ThpError("Checksum is not valid")

    new_context: ChannelContext = ChannelContext.create_new_channel(iface)
    cid = int.from_bytes(new_context.channel_id, "big")
    _CHANNEL_CONTEXTS[cid] = new_context

    response_data = thp_messages.get_channel_allocation_response(
        nonce, new_context.channel_id
    )
    response_header = InitHeader.get_channel_allocation_response_header(
        len(response_data) + CHECKSUM_LENGTH,
    )
    chksum = checksum.compute(response_header.to_bytes() + response_data)
    if __debug__:
        log.debug(__name__, "New channel allocated with id %d", cid)

    await write_to_wire(iface, response_header, response_data + chksum)


async def _handle_allocated(
    ctrl_byte, session: SessionThpCache, payload
) -> MessageWithId:
    # Parameters session and ctrl_byte will be used to determine if the
    # communication should be encrypted or not

    message_type = ustruct.unpack(">H", payload)[0]

    # trim message type and checksum from payload
    message_data = payload[2:-CHECKSUM_LENGTH]
    if __debug__:
        log.debug(__name__, "Received valid message with type %d", message_type)
    return MessageWithId(message_type, message_data, session.session_id)


async def _handle_unallocated(iface, cid) -> MessageWithId | None:
    data = thp_messages.get_error_unallocated_channel()
    header = InitHeader.get_error_header(cid, len(data) + CHECKSUM_LENGTH)
    chksum = checksum.compute(header.to_bytes() + data)
    await write_to_wire(iface, header, data + chksum)


async def _sendAck(iface: WireInterface, cid: int, ack_bit: int) -> None:
    ctrl_byte = _add_sync_bit_to_ctrl_byte(_ACK_MESSAGE, ack_bit)
    header = InitHeader(ctrl_byte, cid, CHECKSUM_LENGTH)
    chksum = checksum.compute(header.to_bytes())
    await write_to_wire(iface, header, chksum)


async def _handle_unexpected_sync_bit(
    iface: WireInterface, cid: int, sync_bit: int
) -> MessageWithId | None:
    if __debug__:
        log.debug(__name__, "Received message has unexpected synchronization bit")
    await _sendAck(iface, cid, sync_bit)

    # TODO handle cancelation messages and messages on allocated channels without synchronization
    # (some such messages might be handled in the classical "allocated" way, if the sync bit is right)


def _is_ctrl_byte_continuation(ctrl_byte) -> bool:
    return ctrl_byte & 0x80 == CONTINUATION_PACKET


def _is_ctrl_byte_ack(ctrl_byte) -> bool:
    return ctrl_byte & 0x20 == _ACK_MESSAGE


def _add_sync_bit_to_ctrl_byte(ctrl_byte, sync_bit):
    if sync_bit == 0:
        return ctrl_byte & 0xEF
    if sync_bit == 1:
        return ctrl_byte | 0x10
    raise ThpError("Unexpected synchronization bit")
