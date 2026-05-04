from typing import *
from buffer_types import *
ThpError: type[Exception]
MESSAGE_READY: object
MESSAGE_READY_ACK: object
ACK: object
KEY_REQUIRED: object
KEY_REQUIRED_UNLOCK: object
FAILED: object
MAX_CREDENTIAL_LEN: int
MAX_DEVICE_PROPERTIES_LEN: int
APP_HEADER_LEN: int
SEND_BUFFER_OVERHEAD: int


# rust/src/thp/micropython.rs
def init(iface_num: int, device_properties: AnyBytes) -> None:
    """
    Initialize Trezor Host Protocol communication stack on a single interface.
    - `iface_num` is an arbitrary numeric identifier between 0 and 255.
    - `device_properties` is a serialized `ThpDeviceProperties` protobuf message.
    It is safe to call this function multiple times on the same interface.
    """


# rust/src/thp/micropython.rs
def packet_in(iface_num: int, packet_buffer: AnyBytes, credential_verify_fn: Callable[[bytes, bytes], int]) -> object | int | None:
    """
    Handle received packet.
    - `credential_verify_fn` is a function that will be called to verify host credentials.
    Returns:
    - `None`: If no action is required from caller.
    - `KEY_REQUIRED`, `KEY_REQUIRED_UNLOCK`: If a channel handshake requires device static key.
      The event loop should call the `handshake_key()` function for this interface.
    - An integer: Lower 16 bits contain channel id, upper 16 bits contain buffer size hint in 8-byte blocks.
      The event loop should call the `packet_in_channel()` function for this interface and if
      the size hint is non-zero, then the receive buffer needs to be at least as large.
      If such buffer cannot be obtained, `channel_close()` should be called.
      If buffer is in use by another channel, `send_transport_busy()` should be called.
    """


# rust/src/thp/micropython.rs
def packet_in_channel(channel_id: int, packet_buffer: AnyBytes, receive_buffer: AnyBuffer) -> object | None:
    """
    Handle received packet that `packet_in` routed to given `channel_id`.
    Returns:
    - `None`: If no action is required from caller, e.g. continuation packet was received.
    - `MESSAGE_READY`, `MESSAGE_READY_ACK`: If a message with valid checksum was received.
      The event loop should call `message_out()` to obtain the message.
    - `ACK`, `MESSAGE_READY_ACK`: If the last sent message was acknowledged received by peer,
      it is now possible to send another using `message_in()`.
    """


# rust/src/thp/micropython.rs
def message_out(channel_id: int, receive_buffer: memoryview) -> tuple[int, int, memoryview]:
    """
    Decrypt an incoming message if one is ready for the given `channel_id`. Returns the triple
    `(session_id, message_type, plaintext)` - message is decrypted in-place in receive buffer
    and plaintext is a memoryview backed by that buffer.
    After successfully calling this function an ACK will be sent by the next `packet_out` on
    this channel.
    Raises an exception if decryption failed - next call to `packet_out` will send an error
    to the peer and close the channel.
    """


# rust/src/thp/micropython.rs
def packet_out(iface_num: int, packet_buffer: AnyBuffer) -> bool:
    """
    Writes outgoing packet to `packet_buffer`. This function is used for the broadcast
    channel or channels in opening/handshake phase that are associated with `iface_num`.
    Returns false if there's no packet ready to be sent.
    """


# rust/src/thp/micropython.rs
def packet_out_channel(channel_id: int, send_buffer: AnyBytes, packet_buffer: AnyBuffer) -> bool:
    """
    Writes outgoing packet to `packet_buffer` from channel in pairing or application data phase
    identified by `channel_id`. Returns false if there's no packet ready to be sent.
    """


# rust/src/thp/micropython.rs
def message_in(channel_id: int, plaintext_len: int, send_buffer: AnyBuffer) -> None:
    """
    Encrypts and starts transmission of given message on a channel. Send buffer must contain
    serialized message:
    * session id: 1 byte
    * message type: 2 bytes
    * message: (plaintext_len - 3) bytes
    Send buffer must be at least `plaintext_len + 16` long in order to accomodate AEAD tag.
    """


# rust/src/thp/micropython.rs
def message_retransmit(channel_id: int) -> bool:
    """
    Starts message retransmission.
    Returns False if this was the last attempt and the channel has been closed.
    """


# rust/src/thp/micropython.rs
def send_transport_busy(channel_id: int) -> None:
    """
    Sends `TRANSPORT_BUSY` transport error on a given channel.
    """


# rust/src/thp/micropython.rs
class ThpChannelInfo:
    """THP channel metadata."""
    last_write: int | None
    pairing_state: int | None
    handshake_hash: bytes | None
    host_static_public_key: bytes
    credential: bytes | None


# rust/src/thp/micropython.rs
def channel_info(channel_id: int) -> ThpChannelInfo:
    """
    Returns information for given channel:
    * last write timestamp
    * pairing state for channels in the pairing phase, or None if already in encrypted transport phase
    * handshake hash
    * host static public key
    * encoded credential provided during handshake - it is discarded at the end of pairing/credential phase
    """


# rust/src/thp/micropython.rs
def channel_paired(channel_id: int) -> int | None:
    """
    Mark channel as paired, i.e. transitioned to encrypted transport of application data.
    If established channel with the same host public key exists on the same interface,
    it is closed and its channel id is returned.
    """


# rust/src/thp/micropython.rs
def channel_close(channel_id: int) -> None:
    """
    Closes a channel identified by its `channel_id`. It is safe to close
    an already closed channel - the function won't raise an exception.
    """


# rust/src/thp/micropython.rs
def channel_close_all(*, exclude_channel_id: int | None = None) -> None:
    """
    Closes all channels on all interfaces. If `exclude_channel_id` is not None, it
    will be left as the only channel.
    Please note the closed channels are not returned by `channel_was_closed()`.
    Caller is responsible for deleting all relevant sessions manually.
    """


# rust/src/thp/micropython.rs
def channel_update_last_usage(channel_id: int):
    """
    Update last usage timestamp of a channel. These are used when channel limit is reached
    and the oldest one has to be closed.
    TODO do not expose to python and do the update in message_out instead
    """


# rust/src/thp/micropython.rs
def channel_was_closed() -> bool:
    """
    Returns true if any channel in encrypted transport state was closed since calling
    this function last time. Sessions belonging to these channels should be discarded.
    """


# rust/src/thp/micropython.rs
def channel_is_open(channel_id: int) -> bool:
    """
    Returns true if a channel with the given id exists in the encrypted transport state.
    """


# rust/src/thp/micropython.rs
def next_timeout(iface_num: int) -> tuple[int, int] | None:
    """
    Returns `(channel_id, timeout_ms)` of the earliest channel to time out waiting for ACK.
    Event loop needs to call `message_retransmit(iface_num, channel_id)` after `timeout_ms`.
    Returns None if there is no channel that's waiting for an ACK.
    """


# rust/src/thp/micropython.rs
def handshake_key(iface_num: int, trezor_static_private_key: AnyBytes | None) -> None:
    """
    Provide device static key in order to progress a handshake after `packet_in`
    returned `KEY_REQUIRED`. If the second argument is None, handshake is aborted
    and `DEVICE_LOCKED` sent to the peer.
    """
