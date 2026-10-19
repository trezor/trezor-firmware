//! Implements [`trezor_app_sdk::traits::wire`]'s `WireV1` on top of
//! [`sys::ipc`], exposed to apps via `TrezorApiV1Struct::wire`. This is the
//! transport underneath every app-facing protocol built on top of it —
//! `trezor_app_sdk::wire`'s host-facing wire messages, as well as this
//! crate's own `crypto`/`ui` implementations, all move over this same
//! channel via [`ipc_call`].
//!
//! There is currently a single remote endpoint apps talk to: Core (the
//! `CoreApp` system task).

use rkyv::Serialize;
use rkyv::api::high::{HighSerializer, to_bytes_in_with_alloc};
use rkyv::rancor::Failure;
use rkyv::ser::allocator::{Arena, ArenaHandle};
use rkyv::util::AlignedVec;
use rtl::unwrap;
use stabby::boxed::BoxedSlice;
use stabby::slice::Slice;
use stabby::str::Str;
use sys::ipc::IpcInbox;
use sys::sysevent::{self, SysEvents};
use sys::task::TaskId;
use sys::time::{Instant, Timeout};
use trezor_app_sdk::traits::util::{FastResult, TIMEOUT_MAX};
use trezor_app_sdk::traits::wire::{WireError, WireMessage, WireV1};

use crate::app_state;

fn coreapp() -> TaskId {
    TaskId::from(RemoteSysTask::CoreApp as u8)
}

/// Converts an app-provided timeout in milliseconds to a [`Timeout`],
/// clamping it to the SDK's [`TIMEOUT_MAX`] (which is below the kernel's
/// limit, so the conversion cannot fail).
pub(crate) fn timeout(timeout_ms: u32) -> Timeout {
    unwrap!(Timeout::from_millis(timeout_ms.min(TIMEOUT_MAX)))
}

/// Identifies the remote system task that sent or will receive an IPC message.
#[derive(Copy, Clone)]
#[repr(u8)]
enum RemoteSysTask {
    #[allow(dead_code)]
    Kernel = 0,
    CoreApp = 1,
}

/// Identifies the IPC services provided by the Core application. Only ever
/// constructed from a known variant here — apps never need to parse an
/// arbitrary numeric service id back into this enum.
#[derive(Copy, Clone, PartialEq, Eq)]
#[repr(u16)]
pub(crate) enum CoreIpcService {
    // Only Core sends it, to start a request; apps receive it.
    #[allow(dead_code)]
    WireStart = 0,
    WireContinue = 1,
    WireEnd = 2,
    WireError = 3,
    Ui = 4,
    Progress = 5,
    Crypto = 6,
}

impl From<CoreIpcService> for u16 {
    fn from(service: CoreIpcService) -> Self {
        service as u16
    }
}

/// A received message, owning a heap-allocated copy of its payload rather
/// than borrowing from the IPC inbox — so it can freely outlive the
/// `IpcMessage` it was copied out of, with no `'static` lifetime tricks.
struct ReceivedMessage {
    service: u16,
    id: u16,
    data: BoxedSlice<u8>,
}

/// Polls for a message until one arrives or `timeout` expires.
fn receive_until(timeout: Timeout) -> Option<ReceivedMessage> {
    let deadline = timeout.to_deadline();
    loop {
        if let Some(msg) = app_state::get()
            .inbox
            .get()
            .expect("ipc not initialized")
            .try_receive_nonblocking()
        {
            let service = msg.service();
            let id = msg.id();
            // Copies out of the inbox buffer while `msg` (and so the buffer
            // slot it borrows) is still alive; `msg` is released right after,
            // via its `Drop` impl, once the copy is safely in `data`.
            let data = BoxedSlice::from(msg.data());
            return Some(ReceivedMessage { service, id, data });
        }
        if Instant::now() >= deadline {
            return None;
        }
        let handle = sysevent::ipc_handle(coreapp());
        sysevent::poll(SysEvents::empty().with_read(&[handle]), deadline);
    }
}

/// Serializes `value` for [`ipc_call`], with a scratch arena local to this
/// call. `rkyv::to_bytes` would instead cache its arena in a global static,
/// i.e. in Core's memory, which the app's task can't access and which would
/// outlive the app.
pub(crate) fn to_bytes<T>(value: &T) -> Result<AlignedVec, Failure>
where
    T: for<'a> Serialize<HighSerializer<AlignedVec, ArenaHandle<'a>, Failure>>,
{
    let mut arena = Arena::new();
    to_bytes_in_with_alloc(value, AlignedVec::new(), arena.acquire())
}

/// Sends `data` tagged `service`/`id` to Core and waits (up to `timeout_ms`)
/// for a reply on the same service. The single low-level call primitive
/// shared by [`WireV1Impl::wire_request`] and this crate's `crypto`/`ui`
/// implementations — the one place the wire protocol is actually spoken.
pub(crate) fn ipc_call(
    service: u16,
    id: u16,
    data: &[u8],
    timeout_ms: u32,
) -> Result<(u16, BoxedSlice<u8>), WireError> {
    if sys::ipc::send(coreapp(), service, id, data).is_err() {
        return Err(WireError::FailedToSend);
    }

    match receive_until(timeout(timeout_ms)) {
        Some(msg) if msg.service == service => Ok((msg.id, msg.data)),
        Some(_) => Err(WireError::UnexpectedService),
        None => Err(WireError::Timeout),
    }
}

/// Allocates this app's IPC inbox out of its own heap and registers it with
/// Core's [`sys::ipc`] layer, in the app's [`app_state::AppState`].
///
/// The size comes from the app's manifest (`ipc-buffer-size`) via its header,
/// so each app gets an inbox matched to the messages it actually receives
/// rather than one hardcoded size for everyone. Called once per launch by
/// [`crate::coreapp_app_entry`], before any app code runs — Core never
/// allocates memory of its own for IPC, it only ever borrows a buffer carved
/// out of the app's own heap. The inbox owns the buffer and frees it when the
/// app's state is dropped (see [`app_state::AppState`]).
///
/// The byte size is a power of two of at least 8 (enforced at header
/// verification), so it always divides evenly into `usize` words on both the
/// 32-bit target and the 64-bit emulator.
pub(crate) fn register_inbox() {
    let inbox_words = io::get_ipc_buffer_size() / core::mem::size_of::<usize>();
    let buffer = alloc::boxed::Box::<[usize]>::new_zeroed_slice(inbox_words);
    // SAFETY: an all-zero `usize` is a valid `usize`.
    let buffer = unsafe { buffer.assume_init() };
    app_state::get().inbox.call_once(|| {
        unwrap!(
            IpcInbox::new(coreapp(), buffer),
            "IPC inbox already registered"
        )
    });
}

pub struct WireV1Impl;

impl WireV1 for WireV1Impl {
    extern "C" fn wire_receive_start(&self, timeout_ms: u32) -> FastResult<WireMessage, WireError> {
        match receive_until(timeout(timeout_ms)) {
            Some(msg) => Ok(WireMessage {
                id: msg.id,
                data: msg.data,
            })
            .into(),
            None => Err(WireError::Timeout).into(),
        }
    }

    extern "C" fn wire_request<'a>(
        &self,
        id: u16,
        data: Slice<'a, u8>,
        timeout_ms: u32,
    ) -> FastResult<WireMessage, WireError> {
        match ipc_call(
            CoreIpcService::WireContinue.into(),
            id,
            data.as_slice(),
            timeout_ms,
        ) {
            Ok((id, data)) => Ok(WireMessage { id, data }).into(),
            Err(e) => Err(e).into(),
        }
    }

    extern "C" fn wire_respond<'a>(
        &self,
        response_id: u16,
        data: Slice<'a, u8>,
    ) -> FastResult<(), WireError> {
        if sys::ipc::send(
            coreapp(),
            CoreIpcService::WireEnd.into(),
            response_id,
            data.as_slice(),
        )
        .is_ok()
        {
            Ok(()).into()
        } else {
            Err(WireError::FailedToSend).into()
        }
    }

    extern "C" fn wire_error<'a>(&self, code: u16, message: Str<'a>) -> FastResult<(), WireError> {
        if sys::ipc::send(
            coreapp(),
            CoreIpcService::WireError.into(),
            code,
            message.as_str().as_bytes(),
        )
        .is_ok()
        {
            Ok(()).into()
        } else {
            Err(WireError::FailedToSend).into()
        }
    }
}
