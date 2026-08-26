//! Serializer-agnostic wire primitives used by the `wire_handler!` macro and
//! by [`wire_request`].
//!
//! This module has no dependency on any particular message encoding (e.g.
//! prost). Apps select their serializer by implementing [`WireDecode`] and
//! [`WireEncode`] for a codec marker type of their own, and declare each
//! request's response type and wire id once via the `wire_request_type!`
//! macro instead of repeating both at every call site.

use crate::alloc_types::Vec;
use crate::app_runtime2::get_ipc_or_die;
use crate::traits::service::{CoreIpcService, IpcRemoteDyn as _, MessageDyn as _};
use crate::util::Timeout;
use crate::{Error, IntoAppResult, Result, ResultExt, debug};

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
    let id: u16 = response_msg
        .try_into()
        .map_err(|_| Error::InvalidMessage)
        .c()?;
    get_ipc_or_die()
        .send(CoreIpcService::WireEnd.into(), id, response_bytes.into())
        .into_app_result()
        .c()?;
    Ok(())
}

/// Sends an error response over the wire.
pub fn wire_error_raw(e: &Error) -> Result<()> {
    crate::error!("{}", e);
    get_ipc_or_die()
        .send(
            CoreIpcService::WireError.into(),
            e.code(),
            e.message().as_bytes().into(),
        )
        .into_app_result()
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
    let result = get_ipc_or_die()
        .call(
            CoreIpcService::WireContinue.into(),
            id,
            req_bytes.into(),
            Timeout::max().as_ms(),
        )
        .into_app_result()
        .c()?;
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
    debug!("Waiting for wire start IPC message");
    let message = get_ipc_or_die()
        .receive(Timeout::max().as_ms())
        .into_app_result()
        .c()?;
    debug!(
        "Received wire start IPC message: service={}, id={}",
        message.service(),
        message.id()
    );

    if message.service() != u16::from(CoreIpcService::WireStart) {
        debug!(
            "Received unexpected IPC message: service={}, id={}",
            message.service(),
            message.id()
        );
        return Err(Error::InvalidMessage);
    }

    Ok((message.id(), message.data().to_vec()))
}
