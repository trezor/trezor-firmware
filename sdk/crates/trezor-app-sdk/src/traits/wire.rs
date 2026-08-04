use stabby::boxed::BoxedSlice;
use stabby::slice::Slice;
use stabby::str::Str;

use super::util::ServiceResult;

/// An owned wire message: a numeric id paired with its body bytes.
#[stabby::stabby]
pub struct WireMessage {
    pub id: u16,
    pub data: BoxedSlice<u8>,
}

/// Failure types an app may report; Core maps them to `FailureType` by
/// position, keep the order in sync with `_APP_FAILURE_CODES`.
#[stabby::stabby]
#[repr(u8)]
#[derive(Clone, Copy, PartialEq, Eq)]
#[cfg_attr(test, derive(Debug))]
pub enum FailureKind {
    UnexpectedMessage,
    DataError,
    ActionCancelled,
    ProcessError,
}

/// Talks to the host through Core.
///
/// Apps never see raw IPC primitives — this trait *is* the transport, hiding
/// how bytes actually move between the app and Core.
#[stabby::stabby(checked)]
pub trait WireV1: Send + Sync {
    /// Waits for the next message from the host.
    extern "C" fn wire_receive(&self, timeout_ms: u32) -> ServiceResult<WireMessage>;

    /// Sends `data` tagged `id` to the host.
    extern "C" fn wire_send<'a>(&self, id: u16, data: Slice<'a, u8>) -> ServiceResult<()>;

    /// Sends an error to the host, ending the app's run.
    extern "C" fn wire_error<'a>(&self, kind: FailureKind, message: Str<'a>) -> ServiceResult<()>;
}

pub type WireV1Vtable = stabby::vtable!(WireV1 + Send + Sync);
pub type WireV1Ref<'a> = stabby::DynRef<'a, WireV1Vtable>;
pub type StaticWireV1 = WireV1Ref<'static>;
