#![cfg_attr(not(test), no_std)]
#![cfg_attr(not(test), no_main)]
#![allow(clippy::too_many_arguments)]
#![allow(clippy::type_complexity)]
#![allow(dead_code)]

#[cfg(not(test))]
extern crate alloc;

use prost::Message;
use trezor_app_sdk::{
    CORE_SERVICE, Error, IpcMessage, Result, ResultExt, crypto, error,
    service::{self, CoreIpcService},
    util::Timeout,
};

// Include generated code
pub(crate) mod proto;

#[macro_use]
pub(crate) mod translations;

pub(crate) mod alloc_types;
mod common;
mod consts;
mod get_address;
mod helpers;
mod layout;
mod paths;
mod sc_constants;
mod sign_tx;
mod strutil;

use proto::{
    messages::MessageType,
    tron::{GetAddress, SignTx},
};

/// Macro to generate handler functions
macro_rules! wire_handler {
    ($handler_name:ident, $request_type:ty, $response_msg:expr, $handler_fn:path) => {
        #[inline(never)]
        fn $handler_name(request_data: &[u8]) -> Result<()> {
            let request =
                <$request_type>::decode(request_data).map_err(|_| Error::InvalidMessage)?;

            let response = $handler_fn(request);

            match response {
                Ok(resp) => {
                    let response_bytes = resp.encode_to_vec();
                    let message = IpcMessage::new(
                        ($response_msg as i32)
                            .try_into()
                            .map_err(|_| Error::InvalidMessage)?,
                        &response_bytes,
                    );
                    message.send(service::CORE_SERVICE_REMOTE, CoreIpcService::WireEnd.into())?;
                }
                Err(e) => {
                    let message = IpcMessage::new(e.code(), e.message().as_bytes());
                    trezor_app_sdk::error!("{}", e);

                    message.send(
                        service::CORE_SERVICE_REMOTE,
                        CoreIpcService::WireError.into(),
                    )?;
                }
            }

            Ok(())
        }
    };
}

pub(crate) fn wire_request<Req, Resp>(
    req: &Req,
    req_id: MessageType,
    resp_ids: &[MessageType],
) -> Result<Resp>
where
    Req: Message,
    Resp: Message + Default,
{
    let req_bytes = req.encode_to_vec();
    let message = IpcMessage::new(req_id as u16, &req_bytes);
    let result = CORE_SERVICE.call(CoreIpcService::WireContinue, &message, Timeout::max())?;
    if result.id() as i32 != resp_ids[0] as i32 {
        return Err(Error::InvalidMessage);
    } else {
        Resp::decode(result.data()).map_err(|_| Error::InvalidMessage)
    }
}

// Generate all handler functions
wire_handler!(
    handle_get_address,
    GetAddress,
    MessageType::Address,
    get_address::get_address
);
wire_handler!(
    handle_sign_tx,
    SignTx,
    MessageType::SignTx,
    sign_tx::sign_tx
);

// Application entry point - receives raw bytes, returns raw bytes
#[unsafe(no_mangle)]
pub fn app() -> Result<()> {
    error!("Application started, waiting for metadata message from core service");
    let message = CORE_SERVICE
        .receive(Timeout::max())
        .map_err(Into::into)
        .c()?;
    match message.service().into() {
        CoreIpcService::MetaData => {
            crypto::send_metadata(
                common::CURVE,
                common::SLIP44_ID,
                paths::PATTERNS_ADDRESS.as_slice(),
            )
            .c()?;
        }
        _ => {
            error!("Invalid service received {}", message.service());
            error!(
                "Invalid service invoked: {:?}, message id {:?}, data {:?}",
                message.service(),
                message.id(),
                message.data()
            );
            return Err(Error::InvalidFunction);
        }
    };
    loop {
        let message = CORE_SERVICE.receive(Timeout::max())?;
        match message.service().into() {
            CoreIpcService::WireStart => handle_wire_message(&message)?,
            _ => {
                error!(
                    "Invalid service invoked: {:?}, message id {:?}, data {:?}",
                    message.service(),
                    message.id(),
                    message.data()
                );
                return Err(Error::InvalidFunction)?;
            }
        };
    }
}

/// Entry point for handling protobuf function calls
/// fn_id: function identifier
/// data: serialized protobuf request
/// Returns: serialized protobuf response
pub fn handle_wire_message(message: &IpcMessage) -> Result<()> {
    match (message.id() as i32).try_into() {
        Ok(MessageType::GetAddress) => handle_get_address(message.data()),
        Ok(MessageType::SignTx) => handle_sign_tx(message.data()),
        Ok(_) => {
            error!("Invalid function: {:?}", message.id());
            Err(Error::InvalidFunction)?
        }
        Err(_) => {
            error!("Non existing message type: {:?}", message.id());
            Err(Error::InvalidFunction)?
        }
    }
}

#[cfg(test)]
pub(crate) mod test_init {
    use std::sync::Once;
    use trezor_app_sdk::mock::{dummy_trezor_api_getter_t, sdk_init};
    pub static INIT: Once = Once::new();

    pub fn init_sdk() {
        INIT.call_once(|| unsafe {
            sdk_init(Some(dummy_trezor_api_getter_t));
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn test_init_sdk() {
        test_init::init_sdk();
    }

    #[test]
    #[cfg(feature = "model_t3w1")]
    fn test_model_t3w1() {
        assert!(cfg!(feature = "model_t3w1"));
        assert!(!cfg!(feature = "model_t3t1"));
    }

    #[test]
    #[cfg(feature = "model_t3t1")]
    fn test_model_t3t1() {
        assert!(cfg!(feature = "model_t3t1"));
        assert!(!cfg!(feature = "model_t3w1"));
    }
}
