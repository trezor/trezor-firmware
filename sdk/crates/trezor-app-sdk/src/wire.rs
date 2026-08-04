//! Serializer-agnostic wire primitives used by the `wire_handler!` macro and
//! by [`wire_request`].
//!
//! This module has no dependency on any particular message encoding (e.g.
//! prost). Apps select their serializer by implementing [`WireDecode`] and
//! [`WireEncode`] for a codec marker type of their own, and declare each
//! request's response type and wire id once via the `wire_request_type!`
//! macro instead of repeating both at every call site.

use crate::alloc_types::Vec;
use crate::app_runtime::{Error, Result, ResultExt};
use crate::ipc::IpcMessage;
use crate::service::CoreIpcService;
use crate::util::Timeout;

/// Decodes a wire message body into `T` using the implementing codec.
pub trait WireDecode<T> {
    fn decode(data: &[u8]) -> Result<T>;
}

/// Encodes `T` into a wire message body using the implementing codec.
pub trait WireEncode<T> {
    fn encode(val: &T) -> Vec<u8>;
}

/// Sends a successful response over the wire.
pub fn wire_respond_raw(response_msg: i32, response_bytes: &[u8]) -> Result<()> {
    let message = IpcMessage::new(
        response_msg
            .try_into()
            .map_err(|_| Error::InvalidMessage)
            .c()?,
        response_bytes,
    );
    crate::core_services::services_or_die()
        .send(CoreIpcService::WireEnd, &message)
        .map_err(Into::into)
        .c()?;
    Ok(())
}

/// Sends an error response over the wire.
pub fn wire_error_raw(e: &Error) -> Result<()> {
    let message = IpcMessage::new(e.code(), e.message().as_bytes());
    crate::error!("{}", e);
    crate::core_services::services_or_die()
        .send(CoreIpcService::WireError, &message)
        .map_err(Into::into)
        .c()?;
    Ok(())
}

/// Sends a request to Core and returns the response's message id and raw bytes.
///
/// Encoding/decoding of `req`/the response is left to the caller, so this
/// primitive has no serializer dependency. Returning the id alongside the
/// bytes (rather than assuming a single fixed response type) lets a request
/// with more than one possible response dispatch on it — see e.g. Tron's
/// `request_contract`, which can get back any one of several contract
/// message types. Prefer [`wire_request`] for the common single-response
/// case; use this directly only when you need that dispatch, or need to
/// bypass [`WireRequest`]/[`WireEncode`]/[`WireDecode`] entirely.
pub fn wire_request_raw(req_bytes: &[u8], id: u16) -> Result<(u16, Vec<u8>)> {
    let message = IpcMessage::new(id, req_bytes);
    let result = crate::core_services::services_or_die().call(
        CoreIpcService::WireContinue,
        &message,
        Timeout::max(),
    )?;
    Ok((result.id(), result.data().to_vec()))
}

/// Associates a request type with its response type and wire id.
///
/// Implemented once per request type via the `wire_request_type!` macro, so
/// [`wire_request`] call sites don't need to repeat the response type
/// annotation and the message id in lockstep — a common source of copy-paste
/// mismatches when they're passed as two independent arguments/annotations.
pub trait WireRequest {
    type Response;
    const ID: u16;
}

/// Sends `req` to Core using `Codec` and decodes the response.
///
/// `Req`'s response type and wire id come from its [`WireRequest`] impl
/// rather than being repeated at the call site.
pub fn wire_request<Codec, Req>(req: &Req) -> Result<Req::Response>
where
    Req: WireRequest,
    Codec: WireEncode<Req> + WireDecode<Req::Response>,
{
    let req_bytes = Codec::encode(req);
    let (_id, resp_bytes) = wire_request_raw(&req_bytes, Req::ID)?;
    Codec::decode(&resp_bytes)
}

pub fn wire_receive_wire_start() -> Result<(u16, Vec<u8>)> {
    let message = crate::core_services::services_or_die()
        .receive(Timeout::max())
        .map_err(Into::into)
        .c()?;

    if message.service() != u16::from(CoreIpcService::WireStart) {
        return Err(Error::InvalidMessage);
    }

    Ok((message.id(), message.data().to_vec()))
}
