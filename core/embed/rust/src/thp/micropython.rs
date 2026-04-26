use heapless::LinearMap;
use spin::mutex::MutexGuard;

use crate::{
    error::Error,
    micropython::{
        buffer::{get_buffer, get_buffer_mut},
        list::List,
        macros::{attr_tuple, obj_fn_1, obj_fn_2, obj_fn_3, obj_fn_var, obj_module, obj_type},
        map::Map,
        module::Module,
        obj::Obj,
        qstr::Qstr,
        simple_type::SimpleTypeObj,
        typ::Type,
        util,
    },
};

use super::{
    InterfaceContext, TrezorInResult, CANNOT_UNLOCK, MAX_INTERFACES, THP_AUX, THP_INTERFACES,
};

fn get_iface<'a>(
    mg: &'a mut Option<MutexGuard<'static, LinearMap<u8, InterfaceContext, MAX_INTERFACES>>>,
    iface_num: u8,
) -> Result<&'a mut InterfaceContext, Error> {
    let interfaces = mg.as_mut().ok_or(CANNOT_UNLOCK)?;
    interfaces.get_mut(&iface_num).ok_or(Error::OutOfRange)
}

extern "C" fn thp_init(iface_num: Obj, device_properties: Obj) -> Obj {
    let block = || {
        let iface_num: u8 = iface_num.try_into()?;
        let device_properties = unsafe { get_buffer(device_properties)? };

        let mut interfaces = THP_INTERFACES.try_lock().ok_or(CANNOT_UNLOCK)?;
        if let Some(ifctx) = interfaces.get(&iface_num) {
            if log::log_enabled!(log::Level::Error) && ifctx.message_out_ready().is_some() {
                log::error!("Message ready from previous session but buffer is lost, waiting for retransmission.");
            }
            // Already initialized.
            return Ok(Obj::const_none());
        }

        let res = interfaces.insert(
            iface_num,
            InterfaceContext::new(iface_num, device_properties)?,
        );
        let res = unwrap!(res); // capacity check
        assert!(res.is_none()); // unique id check

        Ok(Obj::const_none())
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_packet_in(iface_num: Obj, buffer_view: Obj, credential_fn: Obj) -> Obj {
    let block = || {
        let iface_num: u8 = iface_num.try_into()?;
        let buffer = unsafe { get_buffer(buffer_view)? };

        let mut interfaces = THP_INTERFACES.try_lock().ok_or(CANNOT_UNLOCK)?;
        let ifctx = interfaces.get_mut(&iface_num).ok_or(Error::OutOfRange)?;
        let res = ifctx.packet_in(buffer, credential_fn)?;

        if matches!(res, TrezorInResult::ChannelAllocation) {
            InterfaceContext::packet_in_alloc(&mut interfaces, iface_num)?;
        }
        res.try_into()
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_packet_in_channel(n_args: usize, args: *const Obj) -> Obj {
    let block = |args: &[Obj], _kwargs: &Map| {
        if args.len() != 4 {
            return Err(Error::TypeError);
        }

        let iface_num: u8 = args[0].try_into()?;
        let channel_id: u16 = args[1].try_into()?;
        let packet_buffer = unsafe { get_buffer(args[2])? };
        let receive_buffer = unsafe { get_buffer_mut(args[3])? };

        let mut interfaces = THP_INTERFACES.try_lock();
        let ifctx = get_iface(&mut interfaces, iface_num)?;

        let res = ifctx.packet_in_channel(channel_id, packet_buffer, receive_buffer)?;
        res.try_into()
    };

    unsafe { util::try_with_args_and_kwargs(n_args, args, &Map::EMPTY, block) }
}

extern "C" fn thp_packet_out(n_args: usize, args: *const Obj) -> Obj {
    let block = |args: &[Obj], _kwargs: &Map| {
        if args.len() != 4 {
            return Err(Error::TypeError);
        }

        let iface_num: u8 = args[0].try_into()?;
        let channel_id: Option<u16> = args[1].try_into_option()?;
        let send_buffer = unsafe { get_buffer(args[2])? };
        let packet_buffer = unsafe { get_buffer_mut(args[3])? };

        let mut interfaces = THP_INTERFACES.try_lock();
        let ifctx = get_iface(&mut interfaces, iface_num)?;
        let written = match channel_id {
            Some(cid) => ifctx.packet_out_channel(cid, send_buffer, packet_buffer)?,
            None => ifctx.packet_out(packet_buffer)?,
        };
        Ok(written.into())
    };

    unsafe { util::try_with_args_and_kwargs(n_args, args, &Map::EMPTY, block) }
}

extern "C" fn thp_message_out(iface_num: Obj, channel_id: Obj, receive_buffer: Obj) -> Obj {
    let block = || {
        let iface_num: u8 = iface_num.try_into()?;
        let channel_id: u16 = channel_id.try_into()?;
        let receive_buffer = unsafe { get_buffer_mut(receive_buffer)? };

        let mut interfaces = THP_INTERFACES.try_lock();
        let ifctx = get_iface(&mut interfaces, iface_num)?;

        let (sid, message_type, message_bytes) = ifctx.message_out(channel_id, receive_buffer)?;
        (
            sid.into(),
            message_type.into(),
            message_bytes.len().try_into()?,
        )
            .try_into()
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_message_in(n_args: usize, args: *const Obj) -> Obj {
    let block = |args: &[Obj], _kwargs: &Map| {
        if args.len() != 4 {
            return Err(Error::TypeError);
        }
        let iface_num: u8 = args[0].try_into()?;
        let channel_id: u16 = args[1].try_into()?;
        let plaintext_len: usize = args[2].try_into()?;
        let send_buffer = unsafe { get_buffer_mut(args[3])? };

        let mut interfaces = THP_INTERFACES.try_lock();
        let ifctx = get_iface(&mut interfaces, iface_num)?;
        ifctx.message_in(channel_id, plaintext_len, send_buffer)?;
        Ok(Obj::const_none())
    };

    unsafe { util::try_with_args_and_kwargs(n_args, args, &Map::EMPTY, block) }
}

extern "C" fn thp_message_retransmit(iface_num: Obj, channel_id: Obj) -> Obj {
    let block = || {
        let iface_num: u8 = iface_num.try_into()?;
        let channel_id: u16 = channel_id.try_into()?;

        let mut interfaces = THP_INTERFACES.try_lock();
        let ifctx = get_iface(&mut interfaces, iface_num)?;

        let channel_ok = ifctx.message_retransmit(channel_id)?;
        Ok(channel_ok.into())
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_send_transport_busy(iface_num: Obj, channel_id: Obj) -> Obj {
    let block = || {
        let iface_num: u8 = iface_num.try_into()?;
        let channel_id: u16 = channel_id.try_into()?;

        let mut interfaces = THP_INTERFACES.try_lock();
        let ifctx = get_iface(&mut interfaces, iface_num)?;

        ifctx.send_transport_busy(channel_id)?;
        Ok(Obj::const_none())
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_channel_info(iface_num: Obj, channel_id: Obj) -> Obj {
    let block = || {
        let iface_num: u8 = iface_num.try_into()?;
        let channel_id: u16 = channel_id.try_into()?;

        let mut interfaces = THP_INTERFACES.try_lock();
        let ifctx = get_iface(&mut interfaces, iface_num)?;

        let (last_write_age_ms, pairing_state) = ifctx.channel_info(channel_id)?;
        let hash = ifctx.handshake_hash(channel_id)?;
        let remote_static_pubkey = ifctx.remote_static_pubkey(channel_id)?;

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

extern "C" fn thp_channel_paired(iface_num: Obj, channel_id: Obj) -> Obj {
    let block = || {
        let iface_num: u8 = iface_num.try_into()?;
        let channel_id: u16 = channel_id.try_into()?;

        let mut interfaces = THP_INTERFACES.try_lock();
        let ifctx = get_iface(&mut interfaces, iface_num)?;

        let replaced_channel_id = ifctx.channel_paired(channel_id)?;

        Ok(replaced_channel_id.into())
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_channel_close(iface_num: Obj, channel_id: Obj) -> Obj {
    let block = || {
        let iface_num: u8 = iface_num.try_into()?;
        let channel_id: u16 = channel_id.try_into()?;

        let mut interfaces = THP_INTERFACES.try_lock();
        let ifctx = get_iface(&mut interfaces, iface_num)?;
        ifctx.channel_close(channel_id);
        Ok(Obj::const_none())
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_channel_close_all(exclude_channel_id: Obj) -> Obj {
    let block = || {
        let exclude_channel_id: Option<u16> = exclude_channel_id.try_into_option()?;

        let mut interfaces = THP_INTERFACES.try_lock().ok_or(CANNOT_UNLOCK)?;
        for ifctx in interfaces.values_mut() {
            ifctx.channel_close_all(exclude_channel_id);
        }
        Ok(Obj::const_none())
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_channel_update_last_usage(channel_id: Obj) -> Obj {
    let block = || {
        let channel_id: u16 = channel_id.try_into()?;

        let mut interfaces = THP_INTERFACES.try_lock().ok_or(CANNOT_UNLOCK)?;
        for ifctx in interfaces.values_mut() {
            ifctx.channel_update_last_usage(channel_id);
        }

        Ok(Obj::const_none())
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_channel_get_closed(iface_num: Obj) -> Obj {
    let block = || {
        let iface_num: u8 = iface_num.try_into()?;
        let mut interfaces = THP_INTERFACES.try_lock();
        let ifctx = get_iface(&mut interfaces, iface_num)?;

        let closed = ifctx.channel_get_closed();
        if closed.is_empty() {
            return Ok(Obj::const_none());
        }
        let res = List::from_iter(closed.into_iter().map(Obj::from))?;
        Ok(res.leak().into())
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn thp_next_timeout(iface_num: Obj) -> Obj {
    let block = || {
        let iface_num: u8 = iface_num.try_into()?;

        let mut interfaces = THP_INTERFACES.try_lock();
        let ifctx = get_iface(&mut interfaces, iface_num)?;

        match ifctx.next_timeout()? {
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

        let mut interfaces = THP_INTERFACES.try_lock();
        let ifctx = get_iface(&mut interfaces, iface_num)?;

        if local_static_privkey == Obj::const_none() {
            ifctx.send_device_locked()?;
        } else {
            let key = unsafe { get_buffer(local_static_privkey)? };
            ifctx.handshake_static_key(key)?;
        }
        Ok(Obj::const_none())
    };

    unsafe { util::try_or_raise(block) }
}

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
            // Currently no need to expose to python.
            TrezorInResult::ChannelAllocation => Obj::const_none(),
        })
    }
}

#[no_mangle]
#[rustfmt::skip]
pub static mp_module_trezorthp: Module = obj_module! {
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorthp.to_obj(),

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

    /// def init(iface_num: int, device_properties: AnyBytes) -> None:
    ///     """
    ///     Initialize Trezor Host Protocol communication stack on a single interface.
    ///     - `iface_num` is an arbitrary numeric identifier between 0 and 255,
    ///     - `device_properties` is serialized ThpDeviceProperties protobuf message,
    ///     It is safe to call this function multiple times on the same interface.
    ///     """
    Qstr::MP_QSTR_init => obj_fn_2!(thp_init).as_obj(),

    /// def packet_in(iface_num: int, packet_buffer: AnyBytes, credential_verify_fn: Callable[[int, bytes, bytes], int]) -> object | int | None:
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
    ///       If such buffer cannot be obtained, `channel_close()` should be called.
    ///       If buffer is in use by another channel, `send_transport_busy()` should be called.
    ///     """
    Qstr::MP_QSTR_packet_in => obj_fn_3!(thp_packet_in).as_obj(),

    /// def packet_in_channel(iface_num: int, channel_id: int, packet_buffer: AnyBytes, receive_buffer: AnyBuffer) -> object | None:
    ///     """
    ///     Handle received packet that `packet_in` routed to given `channel_id`.
    ///     Returns:
    ///     - `None`: If no action is required from caller, e.g. continuation packet was received.
    ///     - `MESSAGE_READY`, `MESSAGE_READY_ACK`: If a message with valid checksum was received.
    ///       The event loop should call `message_out()` to obtain the message.
    ///     - `ACK`, `MESSAGE_READY_ACK`: If the last sent message was acknowledged received by peer,
    ///       it is now possible to send another using `message_in()`.
    ///     """
    Qstr::MP_QSTR_packet_in_channel => obj_fn_var!(4, 4, thp_packet_in_channel).as_obj(),

    /// def message_out(iface_num: int, channel_id: int, receive_buffer: AnyBytes) -> tuple[int, int, int]:
    ///     """
    ///     Decrypt an incoming message if one is ready for the given `channel_id`. Returns the triple
    ///     `(session_id, message_type, message_len)` - message is decrypted in-place in receive buffer
    ///     and can be read as `receive_buffer[3:message_len + 3]`.
    ///
    ///     After successfully calling this function an ACK will be sent by the next `packet_out` on
    ///     this channel.
    ///
    ///     Raises an exception if decryption failed - next call to `packet_out` will send an error
    ///     to the peer and close the channel.
    ///     """
    Qstr::MP_QSTR_message_out => obj_fn_3!(thp_message_out).as_obj(),

    /// def packet_out(iface_num: int, channel_id: int | None, send_buffer: AnyBytes, packet_buffer: AnyBuffer) -> bool:
    ///     """
    ///     Writes outgoing packet to `packet_buffer`. Use `channel_id` None for broadcast channel or
    ///     any channel that's in the handshake phase, in this case `send_buffer` is not used.
    ///     Returns false if there's no packet ready to be sent.
    ///     """
    Qstr::MP_QSTR_packet_out => obj_fn_var!(4, 4, thp_packet_out).as_obj(),

    /// def message_in(iface_num: int, channel_id: int, plaintext_len: int, send_buffer: AnyBuffer) -> None:
    ///     """
    ///     Encrypts and starts transmission of given message on a channel. Send buffer must contain
    ///     serialized message:
    ///     * session id: 1 byte
    ///     * message type: 2 bytes
    ///     * message: (plaintext_len - 3) bytes
    ///
    ///     Send buffer must be at least `plaintext_len + 16` long in order to accomodate AEAD tag.
    ///     """
    Qstr::MP_QSTR_message_in => obj_fn_var!(4, 4, thp_message_in).as_obj(),

    /// def message_retransmit(iface_num: int, channel_id: int) -> bool:
    ///     """
    ///     Starts message retransmission.
    ///     Returns False if this was the last attempt and the channel has been closed.
    ///     """
    Qstr::MP_QSTR_message_retransmit => obj_fn_2!(thp_message_retransmit).as_obj(),

    /// def send_transport_busy(iface_num: int, channel_id: int) -> None:
    ///     """
    ///     Sends TRANSPORT_BUSY transport error on a given channel.
    ///     """
    Qstr::MP_QSTR_send_transport_busy => obj_fn_2!(thp_send_transport_busy).as_obj(),

    /// class ThpChannelInfo:
    ///     """THP channel metadata."""
    ///     last_write: int | None
    ///     pairing_state: int | None
    ///     handshake_hash: bytes | None
    ///     host_static_public_key: bytes
    ///     credential: bytes | None
    ///
    /// mock:global

    /// def channel_info(iface_num: int, channel_id: int) -> ThpChannelInfo:
    ///     """
    ///     Returns information for given channel:
    ///     * last write timestamp
    ///     * pairing state for channels in the pairing phase, or None if already in encrypted transport phase
    ///     * handshake hash
    ///     * host static public key
    ///     * encoded credential provided during handshake - it is discarded at the end of pairing/credential phase
    ///     """
    Qstr::MP_QSTR_channel_info => obj_fn_2!(thp_channel_info).as_obj(),

    /// def channel_paired(iface_num: int, channel_id: int) -> int | None:
    ///     """
    ///     Mark channel as paired, i.e. transitioned to encrypted transport of application data.
    ///     If established channel with the same host public key exists, it is closed and its
    ///     channel id is returned.
    ///     """
    Qstr::MP_QSTR_channel_paired => obj_fn_2!(thp_channel_paired).as_obj(),

    /// def channel_close(iface_num: int, channel_id: int) -> None:
    ///     """
    ///     Closes a channel.
    ///     """
    Qstr::MP_QSTR_channel_close => obj_fn_2!(thp_channel_close).as_obj(),

    /// def channel_close_all(exclude_channel_id: int | None) -> None:
    ///     """
    ///     Closes all channels on all interfaces. If `exclude_channel_id` is not None, it
    ///     will be left as the only channel.
    ///     Please note the closed channels are not returned by `channel_get_closed()`.
    ///     Caller is responsible for deleting all relevant sessions manually.
    ///     """
    Qstr::MP_QSTR_channel_close_all => obj_fn_1!(thp_channel_close_all).as_obj(),

    /// def channel_update_last_usage(channel_id: int):
    ///     """
    ///     Update last usage timestamp of a channel. These are used when channel limit is reached
    ///     and the oldest one has to be closed.
    ///     TODO do not expose to python and do the update in message_out instead
    ///     """
    Qstr::MP_QSTR_channel_update_last_usage => obj_fn_1!(thp_channel_update_last_usage).as_obj(),

    /// def channel_get_closed(iface_num: int) -> list[int] | None:
    ///     """
    ///     Returns the list of channels that have been closed since calling this function last time.
    ///     Sessions belonging to these channels should be discarded.
    ///     """
    Qstr::MP_QSTR_channel_get_closed => obj_fn_1!(thp_channel_get_closed).as_obj(),

    /// def next_timeout(iface_num: int) -> tuple[int, int] | None:
    ///     """
    ///     Returns `(channel_id, timeout_ms)` of the earliest channel to time out waiting for ACK.
    ///     Event loop needs to call `message_retransmit(iface_num, channel_id)` after `timeout_ms`.
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
