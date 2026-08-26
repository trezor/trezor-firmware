//! Implements [`trezor_app_sdk::traits::service`]'s `IpcRemote`/`Message` on
//! top of [`sys::ipc`], exposed to apps via `TrezorApiV1Struct::ipc`. This is
//! the transport underneath every app-facing protocol built on top of it —
//! `trezor_app_sdk::wire`'s host-facing wire messages, as well as
//! `crypto`/`ui`'s Core-internal calls all move over this same channel.
//!
//! There is currently a single remote endpoint apps talk to: Core (the
//! `CoreApp` system task).

use spin::Mutex;
use stabby::slice::{Slice, SliceMut};
use sys::ipc::IpcInbox;
use sys::sysevent::{self, SysEvents};
use sys::syslog::{self, LogLevel};
use trezor_app_sdk::traits::service::{
    IpcError, IpcRemote, Message, MessageDyn as _, MessageRef, RemoteSysTask,
};
use trezor_app_sdk::traits::util::FastResult;

fn coreapp() -> u8 {
    RemoteSysTask::CoreApp.into()
}

// Borrows the app-provided buffer handed to `register_inbox`, rather than
// owning a `Box<[usize]>` — Core never allocates memory of its own for IPC;
// the app allocates (out of its own heap) and Core just registers the
// pointer with the kernel.
static INBOX: Mutex<Option<IpcInbox<&'static mut [usize]>>> = Mutex::new(None);

/// A view of the most recently received message, borrowing its payload
/// straight out of the app's own IPC inbox buffer — Core never allocates or
/// copies. Valid only until the next `receive`/`call` overwrites
/// [`CURRENT_MESSAGE`]; callers must fully consume one message (deserialize
/// it, copy out whatever they need) before requesting the next.
struct MessageView {
    service: u16,
    id: u16,
    data: &'static [u8],
}

impl Message for MessageView {
    extern "C" fn service(&self) -> u16 {
        self.service
    }

    extern "C" fn id(&self) -> u16 {
        self.id
    }

    extern "C" fn data<'a>(&'a self) -> Slice<'a, u8> {
        self.data.into()
    }
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
fn receive_until(deadline: u32) -> Option<MessageRef<'static>> {
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
            let view = store_current_message(MessageView { service, id, data });
            return Some(MessageRef::from(view));
        }
        if sys::time::ticks_ms() >= deadline {
            return None;
        }
        let handle = sysevent::ipc_handle(coreapp());
        sysevent::poll(SysEvents::empty().with_read(&[handle]), deadline);
    }
}

pub struct IpcRemoteImpl;

impl IpcRemote for IpcRemoteImpl {
    extern "C" fn register_inbox<'remote, 'local>(&'remote self, buffer: SliceMut<'local, usize>) {
        let buffer: &'local mut [usize] = buffer.into();
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

    extern "C" fn receive<'remote>(
        &'remote self,
        timeout_ms: u32,
    ) -> FastResult<MessageRef<'remote>, IpcError<'remote>> {
        let deadline = sys::time::ticks_ms().wrapping_add(timeout_ms);
        match receive_until(deadline) {
            Some(msg) => Ok(msg).into(),
            None => Err(IpcError::Timeout).into(),
        }
    }

    extern "C" fn send<'remote, 'local>(
        &'remote self,
        service: u16,
        id: u16,
        message: Slice<'local, u8>,
    ) -> FastResult<(), IpcError<'remote>> {
        if sys::ipc::send(coreapp(), service, id, message.as_slice()) {
            Ok(()).into()
        } else {
            Err(IpcError::FailedToSend).into()
        }
    }

    extern "C" fn call<'remote, 'local>(
        &'remote self,
        service: u16,
        id: u16,
        message: Slice<'local, u8>,
        timeout_ms: u32,
    ) -> FastResult<MessageRef<'remote>, IpcError<'remote>> {
        if !sys::ipc::send(coreapp(), service, id, message.as_slice()) {
            return Err(IpcError::FailedToSend).into();
        }

        let deadline = sys::time::ticks_ms().wrapping_add(timeout_ms);
        match receive_until(deadline) {
            Some(msg) if msg.service() == service => Ok(msg).into(),
            Some(msg) => Err(IpcError::UnexpectedService(msg)).into(),
            None => Err(IpcError::Timeout).into(),
        }
    }
}
