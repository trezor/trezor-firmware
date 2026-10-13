//! A test-only app that exposes every modui block to the host.
//!
//! Each wire request names one block and carries its parameters; the app
//! calls the block and answers with the reply exactly as the library returned
//! it. Nothing is signed or derived. Meant for manual testing of the UI on
//! every model; dev-signed only, and it must never ship.

#![cfg_attr(not(test), no_std)]
#![cfg_attr(not(test), no_main)]

#[cfg(not(test))]
extern crate alloc;

use prost::Message;
use trezor_app_sdk::{
    Error, Result, ResultExt, WireDecode, WireEncode, error, wire_handler, wire_receive_wire_start,
};

pub(crate) mod alloc_types;
mod blocks;
pub(crate) mod proto;

use proto::messages::MessageType;
use proto::testapp::{
    ConfirmAction, ConfirmData, ConfirmProperties, ConfirmSummary, ConfirmValue, ShowNotice,
    ShowProgress,
};

/// Wire codec for [`wire_handler!`] — encodes/decodes messages via [`prost`].
pub(crate) struct ProstCodec;

impl<T: Message + Default> WireDecode<T> for ProstCodec {
    fn decode(data: &[u8]) -> Result<T> {
        T::decode(data).map_err(|_| Error::InvalidMessage)
    }
}

impl<T: Message> WireEncode<T> for ProstCodec {
    fn encode(val: &T) -> crate::alloc_types::Vec<u8> {
        val.encode_to_vec()
    }
}

wire_handler!(
    handle_confirm_action,
    ProstCodec,
    ConfirmAction,
    MessageType::UiResult,
    blocks::confirm_action
);
wire_handler!(
    handle_confirm_value,
    ProstCodec,
    ConfirmValue,
    MessageType::UiResult,
    blocks::confirm_value
);
wire_handler!(
    handle_confirm_data,
    ProstCodec,
    ConfirmData,
    MessageType::UiResult,
    blocks::confirm_data
);
wire_handler!(
    handle_confirm_properties,
    ProstCodec,
    ConfirmProperties,
    MessageType::UiResult,
    blocks::confirm_properties
);
wire_handler!(
    handle_confirm_summary,
    ProstCodec,
    ConfirmSummary,
    MessageType::UiResult,
    blocks::confirm_summary
);
wire_handler!(
    handle_show_notice,
    ProstCodec,
    ShowNotice,
    MessageType::UiResult,
    blocks::show_notice
);
wire_handler!(
    handle_show_progress,
    ProstCodec,
    ShowProgress,
    MessageType::UiResult,
    blocks::show_progress
);

// Application entry point - receives raw bytes, returns raw bytes
#[unsafe(no_mangle)]
pub fn app() -> Result<()> {
    loop {
        let (id, data) = wire_receive_wire_start().c()?;
        handle_wire_message(id as i32, &data).c()?;
    }
}

/// Dispatches one wire request to its block.
pub fn handle_wire_message(id: i32, data: &[u8]) -> Result<()> {
    match id.try_into() {
        Ok(MessageType::ConfirmAction) => handle_confirm_action(data),
        Ok(MessageType::ConfirmValue) => handle_confirm_value(data),
        Ok(MessageType::ConfirmData) => handle_confirm_data(data),
        Ok(MessageType::ConfirmProperties) => handle_confirm_properties(data),
        Ok(MessageType::ConfirmSummary) => handle_confirm_summary(data),
        Ok(MessageType::ShowNotice) => handle_show_notice(data),
        Ok(MessageType::ShowProgress) => handle_show_progress(data),
        Ok(_) => {
            error!("Invalid function: {:?}", id);
            Err(Error::InvalidFunction)
        }
        Err(_) => {
            error!("Non existing message type: {:?}", id);
            Err(Error::InvalidFunction)
        }
    }
}
