use super::{super::model, *};
use crate::{
    error::Error,
    micropython::{
        buffer::{get_buffer, get_buffer_mut, StrBuffer},
        list::List,
        macros::*,
        map::Map,
        module::Module,
        obj::Obj,
        qstr::Qstr,
        simple_type::SimpleTypeObj,
        typ::Type,
        util,
    },
};

extern "C" fn py_erase_bonds() -> Obj {
    let block = || {
        erase_bonds()?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn py_unpair(obj: Obj) -> Obj {
    // Accepts: None OR a 6-byte MAC address (bytes-like)
    let addr_bytes_opt = if obj == Obj::const_none() {
        None
    } else {
        let bytes: [u8; 6] = unwrap!(util::iter_into_array(obj));
        Some(bytes)
    };

    let block = || {
        if let Some(bytes) = addr_bytes_opt {
            // Scan bonds, unpair on match, and stop.
            get_bonds(|bonds| -> Result<(), Error> {
                for b in bonds {
                    if b.addr == bytes {
                        return unpair(Some(b));
                    }
                }
                Err(Error::ValueError(c"Address not found among bonds"))
            })?;
        } else {
            // Unpair current connection
            unpair(None)?;
        }

        Ok(Obj::const_none())
    };

    unsafe { util::try_or_raise(block) }
}

extern "C" fn py_start_comm() -> Obj {
    start_comm();
    Obj::const_none()
}

extern "C" fn py_start_advertising(whitelist: Obj, name: Obj) -> Obj {
    let block = || {
        let whitelist: bool = whitelist.try_into()?;
        let name = name.try_into_option::<StrBuffer>()?;
        let name = name.as_deref().unwrap_or(model::FULL_NAME);

        if whitelist {
            switch_on(name)?;
        } else {
            pairing_mode(name)?;
        };
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn py_set_name(name: Obj) -> Obj {
    let block = || {
        let name = name.try_into_option::<StrBuffer>()?;
        let name = name.as_deref().unwrap_or(model::FULL_NAME);

        set_name(name);

        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn py_set_high_speed(enable: Obj) -> Obj {
    let block = || {
        let enable: bool = enable.try_into()?;

        set_high_speed(enable);

        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn py_switch_off() -> Obj {
    let block = || {
        switch_off()?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn py_disconnect() -> Obj {
    let block = || {
        disconnect()?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn py_allow_pairing(code: Obj) -> Obj {
    let block = || {
        let code: u32 = code.try_into()?;
        allow_pairing(code)?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn py_reject_pairing() -> Obj {
    let block = || {
        reject_pairing()?;
        Ok(Obj::const_none())
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn py_peer_count() -> Obj {
    peer_count().into()
}

extern "C" fn py_is_connected() -> Obj {
    is_connected().into()
}

extern "C" fn py_is_connectable() -> Obj {
    is_connectable().into()
}

extern "C" fn py_is_pairing() -> Obj {
    is_pairing().into()
}

extern "C" fn py_is_pairing_requested() -> Obj {
    is_pairing_requested().into()
}

extern "C" fn py_is_started() -> Obj {
    is_started().into()
}

extern "C" fn py_connection_flags() -> Obj {
    let block = || {
        let mut result = List::with_capacity(4)?;
        let s = state();
        if !s.state_known {
            result.append(c"unknown".try_into()?)?;
            return Ok(result.leak().into());
        }
        if s.connectable {
            result.append(c"connectable".try_into()?)?;
        }
        if s.connected {
            result.append(c"connected".try_into()?)?;
        }
        if s.pairing {
            result.append(c"pairing".try_into()?)?;
        }
        if s.pairing_requested {
            result.append(c"pairing_requested".try_into()?)?;
        }
        Ok(result.leak().into())
    };
    unsafe { util::try_or_raise(block) }
}

// Return addr_bytes if connected, otherwise None.
// addr_bytes: bytes of length 6
extern "C" fn py_connected_addr() -> Obj {
    let block = || {
        if !is_connected() {
            return Ok(Obj::const_none());
        }
        let a = connected_addr();
        Obj::try_from(&a.addr[..])
    };

    unsafe { util::try_or_raise(block) }
}

// Returns a list of addr_bytes, representing the current bonds.
// addr_bytes: bytes of length 6
extern "C" fn py_get_bonds() -> Obj {
    let block = || {
        get_bonds(|bonds| {
            let mut result = List::with_capacity(bonds.len())?;
            for bond in bonds {
                result.append(Obj::try_from(&bond.addr[..])?)?;
            }
            Ok(result.leak().into())
        })
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn py_iface_num(_self: Obj) -> Obj {
    Obj::small_int(unwrap!(ffi::syshandle_t_SYSHANDLE_BLE_IFACE_0.try_into()))
}

extern "C" fn py_iface_write(_self: Obj, msg: Obj) -> Obj {
    let block = || {
        // SAFETY: reference is discarded at the end of the block
        let buf = unsafe { get_buffer(msg)? };
        if write(buf).is_ok() {
            Ok(buf.len().try_into()?)
        } else {
            Ok((-1).try_into()?)
        }
    };
    unsafe { util::try_or_raise(block) }
}

extern "C" fn py_iface_read(n_args: usize, args: *const Obj) -> Obj {
    let block = |args: &[Obj], _kwargs: &Map| {
        // SAFETY: reference is discarded at the end of the block
        let mut buf = unsafe { get_buffer_mut(args[1]) }?;

        if args.len() > 2 {
            let offset: usize = args[2].try_into()?;
            buf = buf
                .get_mut(offset..)
                .ok_or(Error::ValueError(c"Offset out of bounds"))?;
        }
        if buf.len() < RX_PACKET_SIZE {
            return Err(Error::ValueError(c"Buffer too small"));
        }
        let read_len = read(buf, RX_PACKET_SIZE)?;
        if read_len != RX_PACKET_SIZE {
            return Err(Error::ValueError(c"Unexpected read length"));
        }
        read_len.try_into()
    };
    unsafe { util::try_with_args_and_kwargs(n_args, args, &Map::EMPTY, block) }
}

static BLE_INTERFACE_TYPE: Type = obj_type! {
    name: Qstr::MP_QSTR_BLEIF,
    locals: &obj_dict!(obj_map! {
        Qstr::MP_QSTR_iface_num => obj_fn_1!(py_iface_num).as_obj(),
        Qstr::MP_QSTR_write => obj_fn_2!(py_iface_write).as_obj(),
        Qstr::MP_QSTR_read => obj_fn_var!(2, 3, py_iface_read).as_obj(),
        Qstr::MP_QSTR_RX_PACKET_LEN => Obj::small_int(RX_PACKET_SIZE as u16),
        Qstr::MP_QSTR_TX_PACKET_LEN => Obj::small_int(TX_PACKET_SIZE as u16),
    }),
};

static BLE_INTERFACE_OBJ: SimpleTypeObj = SimpleTypeObj::new(&BLE_INTERFACE_TYPE);

#[no_mangle]
#[rustfmt::skip]
pub static mp_module_trezorble: Module = obj_module! {
    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorble.to_obj(),

    /// class BLEIF:
    ///     """
    ///     BLE interface wrapper.
    ///     """
    ///
    ///     RX_PACKET_LEN: int
    ///     """Length of one BLE RX packet."""
    ///
    ///     TX_PACKET_LEN: int
    ///     """Length of one BLE TX packet."""
    ///
    /// def iface_num(self) -> int:
    ///     """
    ///     Returns the configured number of this interface.
    ///     """
    ///
    /// def write(self, msg: bytes) -> int:
    ///     """
    ///     Sends message over BLE
    ///     """
    ///
    /// def read(self, buf: bytearray, offset: int = 0) -> int:
    ///     """
    ///     Reads message using BLE (device).
    ///     """
    ///
    /// mock:global
    ///
    /// interface: BLEIF
    /// """BLE interface instance."""
    Qstr::MP_QSTR_interface => BLE_INTERFACE_OBJ.as_obj(),

    /// mock:global

    /// def erase_bonds():
    ///     """
    ///     Erases all BLE bonds.
    ///     Raises exception if BLE reports an error.
    ///     """
    Qstr::MP_QSTR_erase_bonds => obj_fn_0!(py_erase_bonds).as_obj(),

    /// def unpair(addr: bytes | None):
    ///     """
    ///     Erases the bond for the given address or for current connection if addr is None.
    ///     Raises exception if BLE driver reports an error.
    ///     """
    Qstr::MP_QSTR_unpair => obj_fn_1!(py_unpair).as_obj(),

    /// def start_comm():
    ///     """
    ///     Start communication with BLE chip.
    ///     """
    Qstr::MP_QSTR_start_comm => obj_fn_0!(py_start_comm).as_obj(),

    /// def start_advertising(whitelist: bool, name: str | None):
    ///     """
    ///     Start advertising.
    ///     Raises exception if BLE driver reports an error.
    ///     """
    Qstr::MP_QSTR_start_advertising => obj_fn_2!(py_start_advertising).as_obj(),

    /// def set_name(name: str | None):
    ///     """
    ///     Set advertising name.
    ///     """
    Qstr::MP_QSTR_set_name => obj_fn_1!(py_set_name).as_obj(),

    /// def set_high_speed(enable: bool):
    ///     """
    ///     Set high speed connection.
    ///     """
    Qstr::MP_QSTR_set_high_speed => obj_fn_1!(py_set_high_speed).as_obj(),

    /// def switch_off():
    ///     """
    ///     Stop advertising and disconnect any connected devices.
    ///     Raises exception if BLE driver reports an error.
    ///     """
    Qstr::MP_QSTR_switch_off => obj_fn_0!(py_switch_off).as_obj(),

    /// def disconnect():
    ///     """
    ///     Disconnect BLE.
    ///     Raises exception if BLE driver reports an error.
    ///     """
    Qstr::MP_QSTR_disconnect => obj_fn_0!(py_disconnect).as_obj(),

    /// def peer_count() -> int:
    ///     """
    ///     Get peer count (number of bonded devices).
    ///     """
    Qstr::MP_QSTR_peer_count => obj_fn_0!(py_peer_count).as_obj(),

    /// def is_connected() -> bool:
    ///     """
    ///     True if a host is connected to us. May or may not be paired.
    ///     """
    Qstr::MP_QSTR_is_connected => obj_fn_0!(py_is_connected).as_obj(),

    /// def is_connectable() -> bool:
    ///     """
    ///     True if a central/host can connect.
    ///     """
    Qstr::MP_QSTR_is_connectable => obj_fn_0!(py_is_connectable).as_obj(),

    /// def is_pairing() -> bool:
    ///     """
    ///     True if BLE is in pairing mode, waiting for a pairing request.
    ///     """
    Qstr::MP_QSTR_is_pairing => obj_fn_0!(py_is_pairing).as_obj(),

    /// def is_pairing_requested() -> bool:
    ///     """
    ///     True if BLE pairing request was received.
    ///     """
    Qstr::MP_QSTR_is_pairing_requested => obj_fn_0!(py_is_pairing_requested).as_obj(),

    /// def is_started() -> bool:
    ///     """
    ///     True if BLE subsystem is started.
    ///     """
    Qstr::MP_QSTR_is_started => obj_fn_0!(py_is_started).as_obj(),

    /// def connection_flags() -> list[str]:
    ///     """
    ///     Returns current connection state as a list of string flags.
    ///     """
    Qstr::MP_QSTR_connection_flags => obj_fn_0!(py_connection_flags).as_obj(),

    /// def get_bonds() -> list[bytes]:
    ///     """
    ///     Returns a list of addr_bytes, representing the current bonds.
    ///     addr_bytes: bytes of length 6
    ///     """
    Qstr::MP_QSTR_get_bonds => obj_fn_0!(py_get_bonds).as_obj(),

    /// def connected_addr() -> bytes | None:
    ///     """
    ///     If connected, returns addr_bytes, otherwise None.
    ///     addr_bytes: bytes of length 6
    ///     """
    Qstr::MP_QSTR_connected_addr => obj_fn_0!(py_connected_addr).as_obj(),

    /// def allow_pairing(code: int):
    ///     """
    ///     Accept BLE pairing request. Code must match the one received with
    ///     BLE_PAIRING_REQUEST event.
    ///     Raises exception if BLE driver reports an error.
    ///     """
    Qstr::MP_QSTR_allow_pairing => obj_fn_1!(py_allow_pairing).as_obj(),

    /// def reject_pairing():
    ///     """
    ///     Reject BLE pairing request.
    ///     Raises exception if BLE driver reports an error.
    ///     """
    Qstr::MP_QSTR_reject_pairing => obj_fn_0!(py_reject_pairing).as_obj(),
};
