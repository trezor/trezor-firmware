//! Implements [`trezor_app_sdk::traits::wire`]'s `WireV1` on top of
//! [`sys::ipc`], exposed to apps via `TrezorApiV1Struct::wire`. This is the
//! transport underneath every app-facing protocol built on top of it —
//! `trezor_app_sdk::wire`'s host-facing wire messages, as well as this
//! crate's own `crypto`/`ui` implementations, all move over this same
//! channel via [`ipc_call`].
//!
//! There is currently a single remote endpoint apps talk to: Core (the
//! `CoreApp` system task).

use spin::Mutex;
use stabby::boxed::BoxedSlice;
use stabby::slice::Slice;
use stabby::str::Str;
use sys::ipc::IpcInbox;
use sys::sysevent::{self, SysEvents};
use trezor_app_sdk::traits::util::FastResult;
use trezor_app_sdk::traits::wire::{WireError, WireMessage, WireV1};

fn coreapp() -> u8 {
    RemoteSysTask::CoreApp as u8
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

// Borrows the app-provided buffer handed to `register_inbox`, rather than
// owning a `Box<[usize]>` — Core never allocates memory of its own for IPC;
// the app allocates (out of its own heap) and Core just registers the
// pointer with the kernel.
//
// The `Mutex` isn't for cross-task synchronization — `INBOX` is only ever
// touched synchronously from the single task executing this app's own code
// (`register_inbox` once at launch, `receive_until` on every poll), the same
// single-writer discipline `allocator.rs`'s heap static relies on. It's here
// because `IpcInbox<&'static mut [usize]>` is `!Sync` (it holds a `&'static
// mut`) and a plain `static` requires `Sync`; `Mutex` is the safe way to get
// mutable, `!Sync` state into a `static` without resorting to `static mut`.
static INBOX: Mutex<Option<IpcInbox<&'static mut [usize]>>> = Mutex::new(None);

/// A received message, owning a heap-allocated copy of its payload rather
/// than borrowing from the IPC inbox — so it can freely outlive the
/// `IpcMessage` it was copied out of, with no `'static` lifetime tricks.
struct ReceivedMessage {
    service: u16,
    id: u16,
    data: BoxedSlice<u8>,
}

/// Polls for a message until one arrives or `deadline` (an absolute
/// [`sys::time`] tick count) passes.
fn receive_until(deadline: u32) -> Option<ReceivedMessage> {
    loop {
        if let Some(msg) = INBOX
            .lock()
            .as_mut()
            .expect("ipc not initialized")
            .try_receive()
        {
            let service = msg.service();
            let id = msg.id();
            // Copies out of the inbox buffer while `msg` (and so the buffer
            // slot it borrows) is still alive; `msg` is released right after,
            // via its `Drop` impl, once the copy is safely in `data`.
            let data = BoxedSlice::from(msg.data());
            return Some(ReceivedMessage { service, id, data });
        }
        if sys::time::ticks_ms() >= deadline {
            return None;
        }
        let handle = sysevent::ipc_handle(coreapp());
        sysevent::poll(SysEvents::empty().with_read(&[handle]), deadline);
    }
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
    if !sys::ipc::send(coreapp(), service, id, data) {
        return Err(WireError::FailedToSend);
    }

    let deadline = sys::time::ticks_ms().wrapping_add(timeout_ms);
    match receive_until(deadline) {
        Some(msg) if msg.service == service => Ok((msg.id, msg.data)),
        Some(_) => Err(WireError::UnexpectedService),
        None => Err(WireError::Timeout),
    }
}

/// Allocates this app's IPC inbox out of its own heap and registers it with
/// Core's [`sys::ipc`] layer.
///
/// The size comes from the app's manifest (`ipc-buffer-size`) via its header,
/// so each app gets an inbox matched to the messages it actually receives
/// rather than one hardcoded size for everyone. Called once per launch by
/// [`crate::coreapp_app_entry`], right after [`crate::allocator::init`] makes
/// the app's heap available and before any app code runs — Core never
/// allocates memory of its own for IPC, it only ever borrows a buffer carved
/// out of the app's own heap.
///
/// The byte size is a power of two of at least 8 (enforced at header
/// verification), so it always divides evenly into `usize` words on both the
/// 32-bit target and the 64-bit emulator.
pub(crate) fn register_inbox() {
    let inbox_words = io::get_ipc_buffer_size() / core::mem::size_of::<usize>();
    let buffer: &'static mut [usize] =
        alloc::boxed::Box::leak(alloc::vec![0usize; inbox_words].into_boxed_slice());
    let mut guard = INBOX.lock();
    // Drop any previous registration *before* creating the new one:
    // `IpcInbox::new` registers first, and only then does assigning
    // `Some(new)` drop the old value — if that happened the other way
    // around, the old value's `Drop` (`ipc_unregister`) would zero the
    // slot the new registration just wrote, since both share the same
    // `remote` and therefore the same kernel queue slot.
    *guard = None;
    *guard = Some(IpcInbox::new(coreapp(), buffer));
}

pub struct WireV1Impl;

impl WireV1 for WireV1Impl {
    extern "C" fn wire_receive_start(&self, timeout_ms: u32) -> FastResult<WireMessage, WireError> {
        let deadline = sys::time::ticks_ms().wrapping_add(timeout_ms);
        match receive_until(deadline) {
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
        ) {
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
        ) {
            Ok(()).into()
        } else {
            Err(WireError::FailedToSend).into()
        }
    }
}
