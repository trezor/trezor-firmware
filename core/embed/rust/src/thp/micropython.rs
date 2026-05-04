use trezor_thp::channel::{
    Phase, APP_HEADER_LEN, MAX_CREDENTIAL_LEN, MAX_DEVICE_PROPERTIES_LEN, SEND_BUFFER_OVERHEAD,
};

use crate::{
    error::Error,
    micropython::{
        buffer::{get_buffer, get_buffer_mut},
        exception,
        macros::{
            attr_tuple, obj_fn_0, obj_fn_1, obj_fn_2, obj_fn_3, obj_fn_kw, obj_module, obj_type,
        },
        map::Map,
        module::Module,
        obj::Obj,
        qstr::Qstr,
        simple_type::SimpleTypeObj,
        typ::Type,
        util,
    },
};

use super::{TrezorInResult, CANNOT_UNLOCK, THP_AUX, THP_CONTEXT};

extern "C" fn thp_init(iface_num: Obj, device_properties: Obj) -> Obj {
    let block = || {
        let iface_num: u8 = iface_num.try_into()?;
        // SAFETY: reference is discarded at the end of this block.
        let device_properties = unsafe { get_buffer(device_properties)? };

        let mut thp = THP_CONTEXT.try_lock().ok_or(CANNOT_UNLOCK)?;
        thp.add_interface(iface_num, device_properties)?;

        #[cfg(feature = "debug")]
        if thp.message_out_ready(iface_num).is_some() {
            log::error!("Message ready from previous event loop session but buffer is lost, waiting for retransmission.");
        }

        Ok(Obj::const_none())
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_packet_in(iface_num: Obj, buffer_view: Obj, credential_fn: Obj) -> Obj {
    let block = || {
        let iface_num: u8 = iface_num.try_into()?;
        // SAFETY: reference is discarded at the end of this block.
        let buffer = unsafe { get_buffer(buffer_view)? };

        let mut thp = THP_CONTEXT.try_lock().ok_or(CANNOT_UNLOCK)?;
        let res = thp.packet_in(iface_num, buffer, credential_fn)?;
        res.try_into()
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_packet_in_channel(
    channel_id: Obj,
    packet_buffer: Obj,
    receive_buffer: Obj,
) -> Obj {
    let block = || {
        let channel_id: u16 = channel_id.try_into()?;
        // SAFETY: reference is discarded at the end of this block.
        let packet_buffer = unsafe { get_buffer(packet_buffer)? };
        // SAFETY: reference is discarded at the end of this block.
        let receive_buffer = unsafe { get_buffer_mut(receive_buffer)? };

        let mut thp = THP_CONTEXT.try_lock().ok_or(CANNOT_UNLOCK)?;
        let res = thp.packet_in_channel(channel_id, packet_buffer, receive_buffer)?;
        res.try_into()
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_packet_out(iface_num: Obj, packet_buffer: Obj) -> Obj {
    let block = || {
        let iface_num: u8 = iface_num.try_into()?;
        // SAFETY: reference is discarded at the end of this block.
        let packet_buffer = unsafe { get_buffer_mut(packet_buffer)? };

        let mut thp = THP_CONTEXT.try_lock().ok_or(CANNOT_UNLOCK)?;
        let written = thp.packet_out(iface_num, packet_buffer)?;
        Ok(written.into())
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_packet_out_channel(channel_id: Obj, send_buffer: Obj, packet_buffer: Obj) -> Obj {
    let block = || {
        let channel_id: u16 = channel_id.try_into()?;
        // SAFETY: reference is discarded at the end of this block.
        let send_buffer = unsafe { get_buffer(send_buffer)? };
        // SAFETY: reference is discarded at the end of this block.
        let packet_buffer = unsafe { get_buffer_mut(packet_buffer)? };

        let mut thp = THP_CONTEXT.try_lock().ok_or(CANNOT_UNLOCK)?;
        let written = thp.packet_out_channel(channel_id, send_buffer, packet_buffer)?;
        Ok(written.into())
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_message_out(channel_id: Obj, receive_buffer_obj: Obj) -> Obj {
    let block = || {
        let channel_id: u16 = channel_id.try_into()?;

        let (sid, message_type, message_len) = {
            // SAFETY: reference is discarded at the end of this block.
            let receive_buffer = unsafe { get_buffer_mut(receive_buffer_obj)? };
            let mut thp = THP_CONTEXT.try_lock().ok_or(CANNOT_UNLOCK)?;
            thp.message_out(channel_id, receive_buffer)?
        };
        // Something is very wrong if message is longer than 64k, OK to panic.
        let message_len = unwrap!(u16::try_from(message_len));
        (
            sid.into(),
            message_type.into(),
            util::get_slice(receive_buffer_obj, APP_HEADER_LEN as u16, message_len)?,
        )
            .try_into()
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_message_in(channel_id: Obj, plaintext_len: Obj, send_buffer: Obj) -> Obj {
    let block = || {
        let channel_id: u16 = channel_id.try_into()?;
        let plaintext_len: usize = plaintext_len.try_into()?;
        // SAFETY: reference is discarded at the end of this block.
        let send_buffer = unsafe { get_buffer_mut(send_buffer)? };

        let mut thp = THP_CONTEXT.try_lock().ok_or(CANNOT_UNLOCK)?;
        thp.message_in(channel_id, plaintext_len, send_buffer)?;
        Ok(Obj::const_none())
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_message_retransmit(channel_id: Obj) -> Obj {
    let block = || {
        let channel_id: u16 = channel_id.try_into()?;

        let mut thp = THP_CONTEXT.try_lock().ok_or(CANNOT_UNLOCK)?;
        let channel_ok = thp.message_retransmit(channel_id)?;
        Ok(channel_ok.into())
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_send_transport_busy(channel_id: Obj) -> Obj {
    let block = || {
        let channel_id: u16 = channel_id.try_into()?;

        let mut thp = THP_CONTEXT.try_lock().ok_or(CANNOT_UNLOCK)?;
        thp.send_transport_busy(channel_id)?;
        Ok(Obj::const_none())
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_channel_info(channel_id: Obj) -> Obj {
    let block = || {
        let channel_id: u16 = channel_id.try_into()?;

        let thp = THP_CONTEXT.try_lock().ok_or(CANNOT_UNLOCK)?;

        let (last_write_age_ms, phase) = thp.channel_info(channel_id)?;
        let hash = thp.handshake_hash(channel_id)?;
        let remote_static_pubkey = thp.remote_static_pubkey(channel_id)?;
        let pairing_state: Option<u8> = match phase {
            Phase::PairingCredential {
                handshake_pairing_state,
            } => Some(handshake_pairing_state.into()),
            Phase::EncryptedTransport => None,
        };

        let credential = {
            let aux = THP_AUX.try_lock().ok_or(CANNOT_UNLOCK)?;
            Obj::from_option(aux.get_credential(channel_id))?
        };

        attr_tuple! {
            Qstr::MP_QSTR_last_write => Obj::from_option(last_write_age_ms)?,
            Qstr::MP_QSTR_pairing_state => pairing_state.into(),
            Qstr::MP_QSTR_handshake_hash => hash.try_into()?,
            Qstr::MP_QSTR_host_static_public_key => remote_static_pubkey.try_into()?,
            Qstr::MP_QSTR_credential => credential,
        }
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_channel_paired(channel_id: Obj) -> Obj {
    let block = || {
        let channel_id: u16 = channel_id.try_into()?;

        let mut thp = THP_CONTEXT.try_lock().ok_or(CANNOT_UNLOCK)?;
        let replaced_channel_id = thp.channel_paired(channel_id)?;
        Ok(replaced_channel_id.into())
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_channel_close(channel_id: Obj) -> Obj {
    let block = || {
        let channel_id: u16 = channel_id.try_into()?;

        let mut thp = THP_CONTEXT.try_lock().ok_or(CANNOT_UNLOCK)?;
        thp.channel_close(channel_id);
        Ok(Obj::const_none())
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_channel_close_all(n_args: usize, args: *const Obj, kwargs: *mut Map) -> Obj {
    let block = |_args: &[Obj], kwargs: &Map| {
        let exclude_channel_id: Option<u16> = kwargs
            .get(Qstr::MP_QSTR_exclude_channel_id)
            .unwrap_or_else(|_| Obj::const_none())
            .try_into_option()?;

        let mut thp = THP_CONTEXT.try_lock().ok_or(CANNOT_UNLOCK)?;
        thp.channel_close_all(exclude_channel_id);
        Ok(Obj::const_none())
    };

    unsafe { util::try_with_args_and_kwargs(n_args, args, kwargs, block) }
}

extern "C" fn thp_channel_update_last_usage(channel_id: Obj) -> Obj {
    let block = || {
        let channel_id: u16 = channel_id.try_into()?;

        let mut thp = THP_CONTEXT.try_lock().ok_or(CANNOT_UNLOCK)?;
        thp.channel_update_last_usage(channel_id);
        Ok(Obj::const_none())
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_channel_was_closed() -> Obj {
    let block = || {
        let mut thp = THP_CONTEXT.try_lock().ok_or(CANNOT_UNLOCK)?;
        let closed = thp.channel_was_closed();
        Ok(closed.into())
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_channel_is_open(channel_id: Obj) -> Obj {
    let block = || {
        let channel_id: u16 = channel_id.try_into()?;

        let thp = THP_CONTEXT.try_lock().ok_or(CANNOT_UNLOCK)?;
        let ok = thp.channel_is_open(channel_id);
        Ok(ok.into())
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_next_timeout(iface_num: Obj) -> Obj {
    let block = || {
        let iface_num: u8 = iface_num.try_into()?;

        let thp = THP_CONTEXT.try_lock().ok_or(CANNOT_UNLOCK)?;
        match thp.next_timeout(iface_num)? {
            None => Ok(Obj::const_none()),
            Some((channel_id, timeout_ms)) => {
                (channel_id.into(), timeout_ms.try_into()?).try_into()
            }
        }
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_handshake_key(iface_num: Obj, local_static_privkey: Obj) -> Obj {
    let block = || {
        let iface_num: u8 = iface_num.try_into()?;

        let mut thp = THP_CONTEXT.try_lock().ok_or(CANNOT_UNLOCK)?;
        if local_static_privkey == Obj::const_none() {
            thp.send_device_locked(iface_num)?;
        } else {
            // SAFETY: reference is discarded at the end of this block.
            let key = unsafe { get_buffer(local_static_privkey)? };
            thp.handshake_static_key(iface_num, key)?;
        }
        Ok(Obj::const_none())
    };

    unsafe { util::try_or_raise(block) }
}

#[allow(non_upper_case_globals)]
pub static ThpError: Type =
    exception::define_exception(Qstr::MP_QSTR_ThpError, exception::Exception);

static FAILED_TYPE: Type = obj_type! { name: Qstr::MP_QSTR_FAILED, };
static KEY_REQUIRED_TYPE: Type = obj_type! { name: Qstr::MP_QSTR_KEY_REQUIRED, };
static KEY_REQUIRED_UNLOCK_TYPE: Type = obj_type! { name: Qstr::MP_QSTR_KEY_REQUIRED_UNLOCK, };
static MESSAGE_READY_TYPE: Type = obj_type! { name: Qstr::MP_QSTR_MESSAGE_READY, };
static ACK_TYPE: Type = obj_type! { name: Qstr::MP_QSTR_ACK, };
static MESSAGE_READY_ACK_TYPE: Type = obj_type! { name: Qstr::MP_QSTR_MESSAGE_READY_ACK, };

pub static FAILED_OBJ: SimpleTypeObj = SimpleTypeObj::new(&FAILED_TYPE);
pub static KEY_REQUIRED_OBJ: SimpleTypeObj = SimpleTypeObj::new(&KEY_REQUIRED_TYPE);
pub static KEY_REQUIRED_UNLOCK_OBJ: SimpleTypeObj = SimpleTypeObj::new(&KEY_REQUIRED_UNLOCK_TYPE);
pub static MESSAGE_READY_OBJ: SimpleTypeObj = SimpleTypeObj::new(&MESSAGE_READY_TYPE);
pub static ACK_OBJ: SimpleTypeObj = SimpleTypeObj::new(&ACK_TYPE);
pub static MESSAGE_READY_ACK_OBJ: SimpleTypeObj = SimpleTypeObj::new(&MESSAGE_READY_ACK_TYPE);

impl TryFrom<TrezorInResult> for Obj {
    type Error = Error;

    fn try_from(val: TrezorInResult) -> Result<Obj, Error> {
        Ok(match val {
            TrezorInResult::None => Obj::const_none(),
            TrezorInResult::Route {
                channel_id,
                buffer_size: None,
            } => Obj::small_int(channel_id),
            TrezorInResult::Route {
                channel_id,
                buffer_size: Some(s),
            } => {
                // Encode channel and size as 000SSSSSSSSSSSSSCCCCCCCCCCCCCCCC which
                // should fit a micropython smallint. Size is in 8-byte blocks.
                let val: u32 = s.get().into();
                let val = val.next_multiple_of(8) >> 3;
                let val = val << 16 | u32::from(channel_id);
                val.try_into()?
            }
            TrezorInResult::Failed => FAILED_OBJ.as_obj(),
            TrezorInResult::KeyRequired {
                try_to_unlock: true,
            } => KEY_REQUIRED_UNLOCK_OBJ.as_obj(),
            TrezorInResult::KeyRequired { .. } => KEY_REQUIRED_OBJ.as_obj(),
            TrezorInResult::MessageReady => MESSAGE_READY_OBJ.as_obj(),
            TrezorInResult::MessageReadyAck => MESSAGE_READY_ACK_OBJ.as_obj(),
            TrezorInResult::Ack => ACK_OBJ.as_obj(),
        })
    }
}

#[no_mangle]
#[rustfmt::skip]
pub static mp_module_trezorthp: Module = obj_module! {
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorthp.to_obj(),

    /// ThpError: type[Exception]
    Qstr::MP_QSTR_ThpError => ThpError.as_obj(),

    /// MESSAGE_READY: object
    Qstr::MP_QSTR_MESSAGE_READY => MESSAGE_READY_OBJ.as_obj(),

    /// MESSAGE_READY_ACK: object
    Qstr::MP_QSTR_MESSAGE_READY_ACK => MESSAGE_READY_ACK_OBJ.as_obj(),

    /// ACK: object
    Qstr::MP_QSTR_ACK => ACK_OBJ.as_obj(),

    /// KEY_REQUIRED: object
    Qstr::MP_QSTR_KEY_REQUIRED => KEY_REQUIRED_OBJ.as_obj(),

    /// KEY_REQUIRED_UNLOCK: object
    Qstr::MP_QSTR_KEY_REQUIRED_UNLOCK => KEY_REQUIRED_UNLOCK_OBJ.as_obj(),

    /// FAILED: object
    Qstr::MP_QSTR_FAILED => FAILED_OBJ.as_obj(),

    /// MAX_CREDENTIAL_LEN: int
    Qstr::MP_QSTR_MAX_CREDENTIAL_LEN => Obj::small_int(MAX_CREDENTIAL_LEN as u16),

    /// MAX_DEVICE_PROPERTIES_LEN: int
    Qstr::MP_QSTR_MAX_DEVICE_PROPERTIES_LEN => Obj::small_int(MAX_DEVICE_PROPERTIES_LEN as u16),

    /// APP_HEADER_LEN: int
    Qstr::MP_QSTR_APP_HEADER_LEN => Obj::small_int(APP_HEADER_LEN as u16),

    /// SEND_BUFFER_OVERHEAD: int
    Qstr::MP_QSTR_SEND_BUFFER_OVERHEAD => Obj::small_int(SEND_BUFFER_OVERHEAD as u16),

    /// def init(iface_num: int, device_properties: AnyBytes) -> None:
    ///     """
    ///     Initialize Trezor Host Protocol communication stack on a single interface.
    ///     - `iface_num` is an arbitrary numeric identifier between 0 and 255.
    ///     - `device_properties` is a serialized `ThpDeviceProperties` protobuf message.
    ///     It is safe to call this function multiple times on the same interface.
    ///     """
    Qstr::MP_QSTR_init => obj_fn_2!(thp_init).as_obj(),

    /// def packet_in(iface_num: int, packet_buffer: AnyBytes, credential_verify_fn: Callable[[bytes, bytes], int]) -> object | int | None:
    ///     """
    ///     Handle received packet.
    ///     - `credential_verify_fn` is a function that will be called to verify host credentials.
    ///     Returns:
    ///     - `None`: If no action is required from caller.
    ///     - `KEY_REQUIRED`, `KEY_REQUIRED_UNLOCK`: If a channel handshake requires device static key.
    ///       The event loop should call the `handshake_key()` function for this interface.
    ///     - An integer: Lower 16 bits contain channel id, upper 16 bits contain buffer size hint in 8-byte blocks.
    ///       The event loop should call the `packet_in_channel()` function for this interface and if
    ///       the size hint is non-zero, then the receive buffer needs to be at least as large.
    ///       If buffer is in use by another channel, `send_transport_busy()` should be called.
    ///     """
    Qstr::MP_QSTR_packet_in => obj_fn_3!(thp_packet_in).as_obj(),

    /// def packet_in_channel(channel_id: int, packet_buffer: AnyBytes, receive_buffer: AnyBuffer) -> object | None:
    ///     """
    ///     Handle received packet that `packet_in` routed to given `channel_id`.
    ///     Returns:
    ///     - `None`: If no action is required from caller, e.g. continuation packet was received.
    ///     - `MESSAGE_READY`, `MESSAGE_READY_ACK`: If a message with valid checksum was received.
    ///       The event loop should call `message_out()` to obtain the message.
    ///     - `ACK`, `MESSAGE_READY_ACK`: If the last sent message was acknowledged received by peer,
    ///       it is now possible to send another using `message_in()`.
    ///     """
    Qstr::MP_QSTR_packet_in_channel => obj_fn_3!(thp_packet_in_channel).as_obj(),

    /// def message_out(channel_id: int, receive_buffer: memoryview) -> tuple[int, int, memoryview]:
    ///     """
    ///     Decrypt an incoming message if one is ready for the given `channel_id`. Returns the triple
    ///     `(session_id, message_type, plaintext)` - message is decrypted in-place in receive buffer
    ///     and plaintext is a memoryview backed by that buffer.
    ///
    ///     After successfully calling this function an ACK will be sent by the next `packet_out` on
    ///     this channel.
    ///
    ///     Raises an exception if decryption failed - next call to `packet_out` will send an error
    ///     to the peer and close the channel.
    ///     """
    Qstr::MP_QSTR_message_out => obj_fn_2!(thp_message_out).as_obj(),

    /// def packet_out(iface_num: int, packet_buffer: AnyBuffer) -> bool:
    ///     """
    ///     Writes outgoing packet to `packet_buffer`. This function is used for the broadcast
    ///     channel or channels in opening/handshake phase that are associated with `iface_num`.
    ///     Returns false if there's no packet ready to be sent.
    ///     """
    Qstr::MP_QSTR_packet_out => obj_fn_2!(thp_packet_out).as_obj(),

    /// def packet_out_channel(channel_id: int, send_buffer: AnyBytes, packet_buffer: AnyBuffer) -> bool:
    ///     """
    ///     Writes outgoing packet to `packet_buffer` from channel in pairing or application data phase
    ///     identified by `channel_id`. Returns false if there's no packet ready to be sent.
    ///     """
    Qstr::MP_QSTR_packet_out_channel => obj_fn_3!(thp_packet_out_channel).as_obj(),

    /// def message_in(channel_id: int, plaintext_len: int, send_buffer: AnyBuffer) -> None:
    ///     """
    ///     Encrypts and starts transmission of given message on a channel. Send buffer must contain
    ///     serialized message:
    ///     * session id: 1 byte
    ///     * message type: 2 bytes
    ///     * message: (plaintext_len - 3) bytes
    ///
    ///     Send buffer must be at least `plaintext_len + 16` long in order to accommodate AEAD tag.
    ///     """
    Qstr::MP_QSTR_message_in => obj_fn_3!(thp_message_in).as_obj(),

    /// def message_retransmit(channel_id: int) -> bool:
    ///     """
    ///     Starts message retransmission.
    ///     Returns False if this was the last attempt and the channel has been closed.
    ///     """
    Qstr::MP_QSTR_message_retransmit => obj_fn_1!(thp_message_retransmit).as_obj(),

    /// def send_transport_busy(channel_id: int) -> None:
    ///     """
    ///     Sends `TRANSPORT_BUSY` transport error on a given channel.
    ///     """
    Qstr::MP_QSTR_send_transport_busy => obj_fn_1!(thp_send_transport_busy).as_obj(),

    /// class ThpChannelInfo:
    ///     """THP channel metadata."""
    ///     last_write: int | None
    ///     pairing_state: int | None
    ///     handshake_hash: bytes | None
    ///     host_static_public_key: bytes
    ///     credential: bytes | None
    ///
    /// mock:global

    /// def channel_info(channel_id: int) -> ThpChannelInfo:
    ///     """
    ///     Returns information for given channel:
    ///     * last write timestamp
    ///     * pairing state for channels in the pairing phase, or None if already in encrypted transport phase
    ///     * handshake hash
    ///     * host static public key
    ///     * encoded credential provided during handshake - it is discarded at the end of pairing/credential phase
    ///     """
    Qstr::MP_QSTR_channel_info => obj_fn_1!(thp_channel_info).as_obj(),

    /// def channel_paired(channel_id: int) -> int | None:
    ///     """
    ///     Mark channel as paired, i.e. transitioned to encrypted transport of application data.
    ///     If established channel with the same host public key exists on the same interface,
    ///     it is closed and its channel id is returned.
    ///     """
    Qstr::MP_QSTR_channel_paired => obj_fn_1!(thp_channel_paired).as_obj(),

    /// def channel_close(channel_id: int) -> None:
    ///     """
    ///     Closes a channel identified by its `channel_id`. It is safe to close
    ///     an already closed channel - the function won't raise an exception.
    ///     """
    Qstr::MP_QSTR_channel_close => obj_fn_1!(thp_channel_close).as_obj(),

    /// def channel_close_all(*, exclude_channel_id: int | None = None) -> None:
    ///     """
    ///     Closes all channels on all interfaces. If `exclude_channel_id` is not None, it
    ///     will be left as the only channel.
    ///     Please note the closed channels are not returned by `channel_was_closed()`.
    ///     Caller is responsible for deleting all relevant sessions manually.
    ///     """
    Qstr::MP_QSTR_channel_close_all => obj_fn_kw!(0, thp_channel_close_all).as_obj(),

    /// def channel_update_last_usage(channel_id: int):
    ///     """
    ///     Update last usage timestamp of a channel. These are used when channel limit is reached
    ///     and the oldest one has to be closed.
    ///     TODO do not expose to python and do the update in message_out instead
    ///     """
    Qstr::MP_QSTR_channel_update_last_usage => obj_fn_1!(thp_channel_update_last_usage).as_obj(),

    /// def channel_was_closed() -> bool:
    ///     """
    ///     Returns true if any channel in encrypted transport state was closed since calling
    ///     this function last time. Sessions belonging to these channels should be discarded.
    ///     """
    Qstr::MP_QSTR_channel_was_closed => obj_fn_0!(thp_channel_was_closed).as_obj(),

    /// def channel_is_open(channel_id: int) -> bool:
    ///     """
    ///     Returns true if a channel with the given id exists in the encrypted transport state.
    ///     """
    Qstr::MP_QSTR_channel_is_open => obj_fn_1!(thp_channel_is_open).as_obj(),

    /// def next_timeout(iface_num: int) -> tuple[int, int] | None:
    ///     """
    ///     Returns `(channel_id, timeout_ms)` of the earliest channel to time out waiting for ACK.
    ///     Event loop needs to call `message_retransmit(channel_id)` after `timeout_ms`.
    ///     Returns None if there is no channel that's waiting for an ACK.
    ///     """
    Qstr::MP_QSTR_next_timeout => obj_fn_1!(thp_next_timeout).as_obj(),

    /// def handshake_key(iface_num: int, trezor_static_private_key: AnyBytes | None) -> None:
    ///     """
    ///     Provide device static key in order to progress a handshake after `packet_in`
    ///     returned `KEY_REQUIRED`. If the second argument is None, handshake is aborted
    ///     and `DEVICE_LOCKED` sent to the peer.
    ///     """
    Qstr::MP_QSTR_handshake_key => obj_fn_2!(thp_handshake_key).as_obj(),
};
