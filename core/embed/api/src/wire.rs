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
use stabby::slice::{Slice, SliceMut};
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
static INBOX: Mutex<Option<IpcInbox<&'static mut [usize]>>> = Mutex::new(None);

/// A view of the most recently received message, borrowing its payload
/// straight out of the app's own IPC inbox buffer — Core never allocates or
/// copies. Valid only until the next receive overwrites [`CURRENT_MESSAGE`];
/// callers must fully consume one message (copy out whatever they need)
/// before requesting the next.
struct MessageView {
    service: u16,
    id: u16,
    data: &'static [u8],
}

// SAFETY (of the `static mut` accesses below): only ever touched
// synchronously from within `receive_until`, which itself only ever runs on
// the single task currently executing this app's own code — the same
// single-writer discipline already relied on elsewhere in this crate (e.g.
// `allocator.rs`'s heap statics).
static mut CURRENT_MESSAGE: Option<MessageView> = None;

/// Overwrites [`CURRENT_MESSAGE`] and returns a `'static` reference to it.
fn store_current_message(view: MessageView) -> &'static MessageView {
    unsafe {
        let slot = &raw mut CURRENT_MESSAGE;
        *slot = Some(view);
        (*slot).as_ref().unwrap()
    }
}

/// Polls for a message until one arrives or `deadline` (an absolute
/// [`sys::time`] tick count) passes.
fn receive_until(deadline: u32) -> Option<&'static MessageView> {
    loop {
        if let Some(msg) = INBOX
            .lock()
            .as_mut()
            .expect("ipc not initialized")
            .try_receive()
        {
            let service = msg.service();
            let id = msg.id();
            // SAFETY: `data` borrows directly from the app-provided inbox
            // buffer registered via `register_inbox` (itself already treated
            // as 'static there), not from `msg` or the `INBOX` guard — so
            // extending it here is sound. Dropping `msg` right after just
            // releases the kernel's ring-buffer bookkeeping for this slot;
            // it doesn't touch the bytes themselves.
            let data: &'static [u8] = unsafe { core::mem::transmute(msg.data()) };
            return Some(store_current_message(MessageView { service, id, data }));
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
) -> Result<(u16, &'static [u8]), WireError> {
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

pub struct WireV1Impl;

impl WireV1 for WireV1Impl {
    extern "C" fn register_inbox<'a>(&self, buffer: SliceMut<'a, usize>) {
        let buffer: &'a mut [usize] = buffer.into();
        // SAFETY: the caller (the app currently executing this shared code)
        // guarantees `buffer` stays valid for as long as it keeps calling
        // into this API, i.e. its own lifetime — which this crate treats as
        // 'static throughout, same as every other field of `TrezorApiV1Struct`.
        let buffer: &'static mut [usize] = unsafe { core::mem::transmute(buffer) };
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

    extern "C" fn wire_receive_start(&self, timeout_ms: u32) -> FastResult<WireMessage, WireError> {
        let deadline = sys::time::ticks_ms().wrapping_add(timeout_ms);
        match receive_until(deadline) {
            Some(msg) => Ok(WireMessage {
                id: msg.id,
                data: BoxedSlice::from(msg.data),
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
            Ok((id, data)) => Ok(WireMessage {
                id,
                data: BoxedSlice::from(data),
            })
            .into(),
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
