//! Safe wrappers around the kernel's IPC subsystem (`sys/ipc/inc/sys/ipc.h`).
//!
//! [`IpcInbox`] registers a receive buffer with the kernel and polls it for
//! incoming messages; [`IpcMessage`] borrows from that buffer for as long as
//! it's alive. [`send`] fires a message at another task directly.

use rtl::unwrap;
use spin::Mutex;

use crate::buffer::{KernelBuffer, KernelBufferPtr};
use crate::task::TaskId;
use crate::time::Timeout;
use crate::{ffi, sysevent};

/// A lock for the set of IPC queues.
///
/// Ensures that no more than one inbox can be registered for a given remote.
///
/// The kernel only allows one inbox per remote, and registrations are
/// latest-wins. Meaning that only the last created `IpcInbox` correctly
/// receives messages. The earlier ones can call `try_receive` but will bind the
/// result to a wrong lifetime. Moreover, when dropping an earlier registration,
/// `ipc_unregister` will actually deregister the currently active inbox.
///
/// Inbox registrations have to go through [`IPC_QUEUE_LOCK`] and refuse to
/// register if the remote is already locked.
struct QueueLock(Mutex<[bool; TaskId::MAX]>);

impl QueueLock {
    /// Creates a new lock.
    const fn new() -> Self {
        Self(Mutex::new([false; TaskId::MAX]))
    }

    /// Tries to register an inbox for `remote`.
    ///
    /// Returns `Err(InboxAlreadyRegistered)` if the remote is already locked.
    fn try_register(&self, remote: TaskId) -> Result<(), InboxAlreadyRegistered> {
        let mut lock = unwrap!(self.0.try_lock());
        let idx = remote.into_index();
        if lock[idx] {
            return Err(InboxAlreadyRegistered);
        }
        lock[idx] = true;
        Ok(())
    }

    /// Unregisters an inbox for `remote`.
    fn unregister(&self, remote: TaskId) {
        let mut lock = unwrap!(self.0.try_lock());
        let idx = remote.into_index();
        lock[idx] = false;
    }
}

/// Global lock for the set of IPC queues.
static IPC_QUEUE_LOCK: QueueLock = QueueLock::new();

/// The message could not be sent because the remote task is not receiving.
pub struct SendFailed;

/// An inbox is already registered for this remote task.
pub struct InboxAlreadyRegistered;

/// Sends `data` to `remote` under `service`/`id`.
///
/// Non-blocking: returns an error if the remote task has no buffer registered,
/// or has no room left in it.
pub fn send(remote: TaskId, service: u16, id: u16, data: &[u8]) -> Result<(), SendFailed> {
    // SAFETY: `data` is valid for `data.len()` bytes for the duration of the call.
    if unsafe {
        ffi::ipc_send(
            remote.into(),
            service,
            id,
            data.as_ptr() as *const _,
            data.len(),
        )
    } {
        Ok(())
    } else {
        Err(SendFailed)
    }
}

/// A single incoming IPC message, borrowed from the [`IpcInbox`] that
/// received it.
///
/// Releases the kernel-owned receive buffer slot on drop.
pub struct Message<'a> {
    remote: TaskId,
    service: u16,
    id: u16,
    data: &'a [u8],
}

impl Message<'_> {
    /// The task that sent this message.
    pub fn remote(&self) -> TaskId {
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

impl Drop for Message<'_> {
    fn drop(&mut self) {
        let mut msg = ffi::ipc_message_t {
            remote: self.remote.into(),
            service: self.service,
            message_id: self.id,
            data: self.data.as_ptr() as *const _,
            size: self.data.len(),
        };
        // SAFETY: `msg` is reconstructed field-for-field from the values
        // `try_receive` filled in from an equivalent `ipc_message_t`, and no
        // other reference to `self.data` can exist while dropping.
        unsafe { ffi::ipc_message_free(&mut msg) };
    }
}

/// Polls for an incoming message.
///
/// Wrapper around `ffi::ipc_try_receive`, converting `ffi::ipc_message_t` to
/// `Message`. Returns a `Message` if there is a pending message, or `None` if
/// there isn't.
///
/// This is a generic-less common implementation of
/// [`IpcInbox::try_receive_nonblocking`], to avoid monomorphizing this code.
///
/// # Safety
///
/// Returned `Message` has an unbound lifetime. The caller must bind it to the
/// currently registered inbox.
unsafe fn try_receive_nonblocking<'a>(remote: TaskId) -> Option<Message<'a>> {
    let mut msg = ffi::ipc_message_t {
        // `remote` doubles as an input: `ipc_try_receive` reads it to
        // pick which origin's queue to check (see `ipc_try_receive` in
        // `sys/ipc/ipc.c`), then overwrites it with the same value.
        remote: remote.into(),
        service: 0,
        message_id: 0,
        data: core::ptr::null(),
        size: 0,
    };
    // SAFETY: `msg` is a valid in/out pointer for the duration of the call.
    let ok = unsafe { ffi::ipc_try_receive(&mut msg) };
    if !ok {
        return None;
    }
    // SAFETY: the kernel just filled `msg` with a message addressed to an
    // inbox's registered buffer; `data`/`size` describe a slice valid until:
    // (a) `ipc_message_free` is called (in `IpcMessage::drop`), or
    // (b) the inbox is unregistered and its buffer freed.
    // Caller is responsible for bounding the lifetime of the returned `Message`
    // to the appropriate inbox's buffer.
    let data = unsafe { core::slice::from_raw_parts(msg.data as *const u8, msg.size) };
    Some(Message {
        remote: msg.remote.into(),
        service: msg.service,
        id: msg.message_id,
        data,
    })
}

/// Polls for an incoming message with a timeout.
///
/// Uses [`sysevent::poll`] to ask the kernel to wake us up when a message is
/// available, then receives it via [`try_receive_nonblocking`].
///
/// Returns a `Message` if a message is received (or was pending) before
/// `timeout` expires. Returns `None` if the timeout expires without receiving a
/// message.
///
/// This is a generic-less common implementation of [`IpcInbox::try_receive`],
/// to avoid monomorphizing this code.
///
/// # Safety
///
/// Returned `Message` has an unbound lifetime. The caller must bind it to the
/// currently registered inbox.
unsafe fn try_receive<'a>(remote: TaskId, timeout: Timeout) -> Option<Message<'a>> {
    let deadline = timeout.to_deadline();
    let handle = sysevent::ipc_handle(remote);
    let events = sysevent::poll(sysevent::SysEvents::reading(&[handle]), deadline);
    if events.read.contains(handle) {
        return unsafe { try_receive_nonblocking(remote) };
    }
    None
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
pub struct IpcInbox<P: KernelBufferPtr> {
    remote: TaskId,
    _buffer: KernelBuffer<P>,
}

impl<P: KernelBufferPtr<Align = usize>> IpcInbox<P> {
    /// Creates a new inbox for `remote`, registering `buffer` with the kernel.
    ///
    /// Panics in debug builds if registration fails — this can only happen
    /// if the buffer is empty, since `P`'s bound already guarantees
    /// `usize` alignment and the kernel has no other rejection reason.
    pub fn new(remote: TaskId, buffer: P) -> Result<Self, InboxAlreadyRegistered> {
        IPC_QUEUE_LOCK.try_register(remote)?;

        let buffer = KernelBuffer::new(buffer);
        // SAFETY: memory managed by `buffer` is valid until deregistration on
        // drop, and no Rust references to it can be created.
        let ok = unsafe { ffi::ipc_register(remote.into(), buffer.ptr() as _, buffer.byte_size()) };
        debug_assert!(ok, "Failed to register IPC buffer");
        Ok(Self {
            remote,
            _buffer: buffer,
        })
    }

    /// Polls for an incoming message without blocking.
    pub fn try_receive_nonblocking(&self) -> Option<Message<'_>> {
        // SAFETY: returned Message's lifetime is bound to &self
        unsafe { try_receive_nonblocking(self.remote) }
    }

    /// Polls for an incoming message with a timeout.
    pub fn try_receive(&self, timeout: Timeout) -> Option<Message<'_>> {
        // SAFETY: returned Message's lifetime is bound to &self
        unsafe { try_receive(self.remote, timeout) }
    }

    /// The remote task this inbox is registered for.
    pub fn remote(&self) -> TaskId {
        self.remote
    }
}

impl<P: KernelBufferPtr> Drop for IpcInbox<P> {
    fn drop(&mut self) {
        // SAFETY: unregistering before `buffer` is dropped/freed prevents
        // the kernel from writing into memory we no longer own.
        unsafe { ffi::ipc_unregister(self.remote.into()) };
        IPC_QUEUE_LOCK.unregister(self.remote);
    }
}
