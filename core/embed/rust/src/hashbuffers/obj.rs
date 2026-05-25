use micropython::{
    macros::{obj_fn_1, obj_fn_2, obj_fn_3, obj_module},
    module::Module,
};

use crate::{
    micropython::qstr::Qstr,
    protobuf::obj::{protobuf_type_for_name, protobuf_type_for_wire},
};

use super::decode::hashbuffers_decode;

#[no_mangle]
pub static mp_module_trezorhashbuffers: Module = obj_module! {
    /// from trezorproto import MessageType, T
    ///
    /// mock:global

    Qstr::MP_QSTR___name__ => Qstr::MP_QSTR_trezorhashbuffers.to_obj(),

    /// def type_for_name(name: str) -> type[MessageType]:
    ///     """Find the message definition for the given protobuf name."""
    Qstr::MP_QSTR_type_for_name => obj_fn_1!(protobuf_type_for_name).as_obj(),

    /// def type_for_wire(enum_name: str, wire_id: int) -> type[MessageType]:
    ///     """Find the message definition for the given wire enum name and
    ///     wire type (numeric identifier)."""
    Qstr::MP_QSTR_type_for_wire => obj_fn_2!(protobuf_type_for_wire).as_obj(),

    /// def decode(
    ///     buffer: AnyBytes,
    ///     msg_type: type[T],
    ///     enable_experimental: bool,
    /// ) -> T:
    ///     """Decode hashbuffer data in the buffer into the specified message type."""
    Qstr::MP_QSTR_decode => obj_fn_3!(hashbuffers_decode).as_obj()
};
