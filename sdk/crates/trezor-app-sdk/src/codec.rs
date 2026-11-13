//! Serializer-agnostic message encoding on top of the [`crate::wire`]
//! transport: [`WireDecode`]/[`WireEncode`], [`wire_request`] and the
//! `wire_handler!`/`wire_request_type!` macros.
//!
//! This module has no dependency on any particular message encoding (e.g.
//! prost). Apps select their serializer by implementing [`WireDecode`] and
//! [`WireEncode`] for a codec marker type of their own, and declare each
//! request's response type and wire id once via the `wire_request_type!`
//! macro instead of repeating both at every call site.

use alloc::vec::Vec;

use crate::Result;
use crate::wire::wire_call;

/// Decodes a wire message body into `T` using the implementing codec.
pub trait WireDecode<T> {
    fn decode(data: &[u8]) -> Result<T>;
}

/// Encodes `T` into a wire message body using the implementing codec.
pub trait WireEncode<T> {
    fn encode(val: &T) -> Vec<u8>;
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

/// Sends `req` to the host using `Codec` and decodes the response.
///
/// `Req`'s response type and wire id come from its [`WireRequest`] impl
/// rather than being repeated at the call site.
pub fn wire_request<Codec, Req>(req: &Req) -> Result<Req::Response>
where
    Req: WireRequest,
    Codec: WireEncode<Req> + WireDecode<Req::Response>,
{
    let req_bytes = Codec::encode(req);
    let (_id, resp_bytes) = wire_call(Req::ID, &req_bytes)?;
    Codec::decode(resp_bytes.as_ref())
}

/// Macro to generate handler functions.
///
/// `$codec` selects the wire serializer: a type implementing
/// [`WireDecode<$request_type>`](crate::WireDecode) and `WireEncode` for
/// whatever the handler returns. Apps own this type, so the SDK itself has
/// no dependency on any particular serializer.
#[macro_export]
macro_rules! wire_handler {
    ($handler_name:ident, $codec:ty, $request_type:ty, $response_msg:expr, $handler_fn:path) => {
        #[inline(never)]
        fn $handler_name(request_data: &[u8]) -> $crate::Result<()> {
            // a malformed request is the host's error, the app keeps running
            let decoded = <$codec as $crate::WireDecode<$request_type>>::decode(request_data);
            let request = match $crate::ResultExt::c(decoded) {
                Ok(request) => request,
                Err(e) => return $crate::wire_error(&e),
            };

            match $handler_fn(request) {
                Ok(resp) => {
                    let response_bytes = <$codec as $crate::WireEncode<_>>::encode(&resp);
                    $crate::wire_send($response_msg as u16, &response_bytes)
                }
                Err(e) => $crate::wire_error(&e),
            }
        }
    };
}

/// Declares `$req`'s response type and wire id for [`$crate::wire_request`],
/// so callers don't have to repeat both at every call site.
#[macro_export]
macro_rules! wire_request_type {
    ($req:ty => $resp:ty, $id:expr) => {
        impl $crate::WireRequest for $req {
            type Response = $resp;
            const ID: u16 = $id as u16;
        }
    };
}
