//! Safe wrappers around the kernel's IPC subsystem (`sys/ipc/inc/sys/ipc.h`).
//!
//! [`IpcInbox`] registers a receive buffer with the kernel and polls it for
//! incoming messages; [`IpcMessage`] borrows from that buffer for as long as
//! it's alive. [`send`] fires a message at another task directly.

use core::ops::DerefMut;

use crate::ffi;

// Encodes/decodes the `fn_` field of `ipc_message_t`, which packs a 16-bit
// service ID and a 16-bit message ID into a single u32.
fn from_fn(fn_: u32) -> (u16, u16) {
    ((fn_ >> 16) as u16, (fn_ & 0xffff) as u16)
}

fn to_fn(service: u16, id: u16) -> u32 {
    (service as u32) << 16 | id as u32
}

/// Sends `data` to `remote` under `service`/`id`.
///
/// Non-blocking: returns `false` if the remote task has no buffer registered,
/// or has no room left in it.
pub fn send(remote: u8, service: u16, id: u16, data: &[u8]) -> bool {
    // SAFETY: `data` is valid for `data.len()` bytes for the duration of the call.
    unsafe {
        ffi::ipc_send(
            remote,
            to_fn(service, id),
            data.as_ptr() as *const _,
            data.len(),
        )
    }
}

/// A single incoming IPC message, borrowed from the [`IpcInbox`] that
/// received it.
///
/// Releases the kernel-owned receive buffer slot on drop.
pub struct IpcMessage<'a> {
    remote: u8,
    service: u16,
    id: u16,
    data: &'a [u8],
}

impl IpcMessage<'_> {
    /// The task that sent this message.
    pub fn remote(&self) -> u8 {
        self.remote
    }

    /// The service ID this message belongs to.
    pub fn service(&self) -> u16 {
        self.service
    }

    /// The message ID within its service.
    pub fn id(&self) -> u16 {
        self.id
    }

    /// The raw message payload.
    pub fn data(&self) -> &[u8] {
        self.data
    }
}

impl Drop for IpcMessage<'_> {
    fn drop(&mut self) {
        let mut msg = ffi::ipc_message_t {
            remote: self.remote,
            fn_: to_fn(self.service, self.id),
            data: self.data.as_ptr() as *const _,
            size: self.data.len(),
        };
        // SAFETY: `msg` is reconstructed field-for-field from the values
        // `try_receive` filled in from an equivalent `ipc_message_t`, and no
        // other reference to `self.data` can exist while dropping.
        unsafe { ffi::ipc_message_free(&mut msg) };
    }
}

/// An IPC receive inbox for a specific remote task.
///
/// Registers `buffer` with the kernel on construction, so the kernel can
/// write incoming messages into it, and unregisters it on drop. `buffer` is
/// generic over its backing storage (e.g. `&mut [usize]` or `Box<[usize]>`)
/// so the inbox can either borrow a caller-provided buffer for an exclusive
/// scope, or own a heap-allocated one for its entire lifetime.
///
/// `[usize]` (rather than `[u8]`) is used so the buffer is always aligned to
/// `size_of::<usize>()`, which the kernel requires.
pub struct IpcInbox<D: DerefMut<Target = [usize]>> {
    remote: u8,
    // Never read directly — the kernel writes into it via the raw pointer
    // passed to `ipc_register`. Its only job is to keep the backing storage
    // alive (and drop it) for exactly as long as `self` is registered.
    #[allow(dead_code)]
    buffer: D,
}

impl<D: DerefMut<Target = [usize]>> IpcInbox<D> {
    /// Creates a new inbox for `remote`, registering `buffer` with the kernel.
    ///
    /// Panics in debug builds if registration fails — this can only happen
    /// if the buffer is empty, since `D`'s bound already guarantees
    /// `usize` alignment and the kernel has no other rejection reason.
    pub fn new(remote: u8, mut buffer: D) -> Self {
        let ptr = buffer.as_mut_ptr() as *mut cty::c_void;
        let size = buffer.len() * core::mem::size_of::<usize>();
        // SAFETY: `buffer` is owned by `self` for as long as it stays
        // registered (unregistered on drop, below), and the kernel only
        // writes into it — it's never aliased by a live Rust reference.
        let ok = unsafe { ffi::ipc_register(remote, ptr, size) };
        debug_assert!(ok, "Failed to register IPC buffer");
        Self { remote, buffer }
    }

    /// Polls for an incoming message without blocking.
    ///
    /// The returned message borrows this inbox exclusively, so it must be
    /// dropped before the next call to `try_receive`.
    pub fn try_receive(&mut self) -> Option<IpcMessage<'_>> {
        let mut msg = ffi::ipc_message_t {
            // `remote` doubles as an input: `ipc_try_receive` reads it to
            // pick which origin's queue to check (see `ipc_try_receive` in
            // `sys/ipc/ipc.c`), then overwrites it with the same value.
            remote: self.remote,
            fn_: 0,
            data: core::ptr::null(),
            size: 0,
        };
        // SAFETY: `msg` is a valid in/out pointer for the duration of the call.
        let ok = unsafe { ffi::ipc_try_receive(&mut msg) };
        if !ok {
            return None;
        }
        let (service, id) = from_fn(msg.fn_);
        // SAFETY: the kernel just filled `msg` with a message addressed to
        // this inbox's registered buffer; `data`/`size` describe a slice
        // valid until `ipc_message_free` is called (in `IpcMessage::drop`),
        // and the `&mut self` borrow above prevents re-registering or
        // re-receiving into the same buffer while this message is alive.
        let data = unsafe { core::slice::from_raw_parts(msg.data as *const u8, msg.size) };
        Some(IpcMessage {
            remote: msg.remote,
            service,
            id,
            data,
        })
    }

    /// The remote task this inbox is registered for.
    pub fn remote(&self) -> u8 {
        self.remote
    }
}

impl<D: DerefMut<Target = [usize]>> Drop for IpcInbox<D> {
    fn drop(&mut self) {
        // SAFETY: unregistering before `buffer` is dropped/freed prevents
        // the kernel from writing into memory we no longer own.
        unsafe { ffi::ipc_unregister(self.remote) };
    }
}
