use stabby::boxed::BoxedSlice;
use stabby::slice::{Slice, SliceMut};
use stabby::str::Str;

use super::util::FastResult;

/// Errors that can occur while talking to Core over the wire.
#[stabby::stabby]
#[repr(u8)]
pub enum WireError {
    /// The operation timed out while waiting for a response.
    Timeout,
    /// The message could not be sent to Core.
    FailedToSend,
    /// A response was received from an unexpected service.
    UnexpectedService,
    /// A response with an unexpected format or content was received.
    UnexpectedResponse,
    /// The response could not be decoded.
    DecodeError,
}

impl WireError {
    /// Returns a static human-readable description of the error.
    pub fn message(&self) -> &'static str {
        match self {
            Self::Timeout => "timeout while waiting for response",
            Self::FailedToSend => "failed to send message",
            Self::UnexpectedService => "received message from unexpected service",
            Self::UnexpectedResponse => "received unexpected response message",
            Self::DecodeError => "failed to decode response",
        }
    }
}

/// An owned wire message: a numeric id paired with its body bytes.
#[stabby::stabby]
pub struct WireMessage {
    pub id: u16,
    pub data: BoxedSlice<u8>,
}

/// Talks to Core over the wire transaction protocol (WireStart/Continue/End/Error).
///
/// Apps never see raw IPC primitives — this trait *is* the transport, hiding
/// how bytes actually move between the app and Core.
#[stabby::stabby(checked)]
pub trait WireV1: Send + Sync {
    /// Registers `buffer` as this app's own inbox for messages from Core.
    ///
    /// Must be called exactly once, before any other method. Core never
    /// allocates memory of its own for the wire — `buffer` must be allocated
    /// by the app (out of its own heap) and stay valid for as long as the
    /// app is running; Core only ever holds a reference into it, never a
    /// copy.
    extern "C" fn register_inbox<'a>(&self, buffer: SliceMut<'a, usize>);

    /// Waits for the message that starts a new wire transaction — Core
    /// pushes this, the app never sends it.
    extern "C" fn wire_receive_start(&self, timeout_ms: u32) -> FastResult<WireMessage, WireError>;

    /// Sends `data` tagged `id` and waits for Core's reply, for use mid-transaction
    /// when the app needs more input from the host.
    extern "C" fn wire_request<'a>(
        &self,
        id: u16,
        data: Slice<'a, u8>,
        timeout_ms: u32,
    ) -> FastResult<WireMessage, WireError>;

    /// Sends the final, successful response, ending the transaction.
    extern "C" fn wire_respond<'a>(
        &self,
        response_id: u16,
        data: Slice<'a, u8>,
    ) -> FastResult<(), WireError>;

    /// Sends an error response, ending the transaction.
    extern "C" fn wire_error<'a>(&self, code: u16, message: Str<'a>) -> FastResult<(), WireError>;
}

pub type WireV1Vtable = stabby::vtable!(WireV1 + Send + Sync);
pub type WireV1Ref<'a> = stabby::DynRef<'a, WireV1Vtable>;
pub type StaticWireV1 = WireV1Ref<'static>;
