//! Talking to the host through Core: receive, send, call and error. The
//! message encoding on top lives in [`crate::codec`].

use crate::app_runtime::get_wire_or_die;
use crate::traits::wire::WireV1Dyn as _;
use crate::util::{Bytes, Timeout};
use crate::{Error, IntoAppResult, Result, ResultExt, debug};

/// Waits for the next message from the host and returns its id and raw bytes.
pub fn wire_receive() -> Result<(u16, impl AsRef<[u8]>)> {
    debug!("Waiting for wire message");
    let message = get_wire_or_die()
        .wire_receive(Timeout::max().as_ms())
        .into_app_result()
        .c()?;
    debug!("Received wire message: id={}", message.id);

    Ok((message.id, Bytes(message.data)))
}

/// Sends a message to the host. On its own this is how a flow ends; mid-flow
/// use [`wire_call`].
pub fn wire_send(bytes: &[u8], id: u16) -> Result<()> {
    get_wire_or_die()
        .wire_send(id, bytes.into())
        .into_app_result()
        .c()
}

/// Sends an error to the host.
pub fn wire_error(e: &Error) -> Result<()> {
    crate::error!("{}", e);
    get_wire_or_die()
        .wire_error(e.kind(), e.message().into())
        .into_app_result()
        .c()
}

/// Sends a request to the host and returns the response's message id and raw
/// bytes.
///
/// Encoding/decoding of `req`/the response is left to the caller, so this
/// primitive has no serializer dependency. Returning the id alongside the
/// bytes (rather than assuming a single fixed response type) lets a request
/// with more than one possible response dispatch on it — see e.g. Tron's
/// `request_contract`, which can get back any one of several contract
/// message types. Prefer [`wire_request`](crate::wire_request) for the common single-response
/// case; use this directly only when you need that dispatch, or need to
/// bypass [`WireRequest`](crate::WireRequest)/[`WireEncode`](crate::WireEncode)/
/// [`WireDecode`](crate::WireDecode) entirely.
pub fn wire_call(req_bytes: &[u8], id: u16) -> Result<(u16, impl AsRef<[u8]> + use<>)> {
    wire_send(req_bytes, id)?;
    wire_receive()
}
