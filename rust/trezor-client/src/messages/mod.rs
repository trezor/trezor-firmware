//! This module implements the `message_type` getter for all protobuf message types.

use crate::protos::{MessageType::*, *};

/// Extends the protobuf Message trait to also have a static getter for the message
/// type code.
pub trait TrezorMessage: protobuf::Message + std::fmt::Debug {
    const MESSAGE_TYPE: MessageType;

    #[inline]
    #[deprecated(note = "Use `MESSAGE_TYPE` instead")]
    fn message_type() -> MessageType {
        Self::MESSAGE_TYPE
    }
}

/// This macro provides the TrezorMessage trait for a protobuf message.
macro_rules! trezor_message_impl {
    ($($struct:ident => $mtype:expr),+ $(,)?) => {$(
        impl TrezorMessage for $struct {
            const MESSAGE_TYPE: MessageType = $mtype;
        }
    )+};
}

include!("./generated.rs");
