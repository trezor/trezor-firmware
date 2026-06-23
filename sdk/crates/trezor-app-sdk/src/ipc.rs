//! IPC primitives for communicating between the app task and other system tasks.
//!
//! The two main types are:
//! - [`IpcInbox`] — registers a receive buffer with the kernel and polls it for incoming messages.
//! - [`IpcMessage`] — a single IPC message, either constructed for sending or received from an inbox.

use core::marker::PhantomData;

use ufmt::derive::uDebug;

use crate::low_level_api::{self, ApiError, ffi};

// Encodes/decodes the `fn_` field of `ipc_message_t`, which packs a 16-bit
// service ID and a 16-bit message ID into a single u32.
struct Fn {
    service: u16,
    message_id: u16,
}

impl Fn {
    // Splits a packed `fn_` value into its service and message_id components.
    pub fn from_fn(fn_: u32) -> Self {
        Self {
            service: (fn_ >> 16) as u16,
            message_id: (fn_ & 0xffff) as u16,
        }
    }

    // Packs a service ID and message ID into a single `fn_` value.
    pub fn to_fn(service: u16, message_id: u16) -> u32 {
        (service as u32) << 16 | message_id as u32
    }
}

/// Identifies the remote system task that sent or will receive an IPC message.
#[repr(u8)]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, num_enum::FromPrimitive, num_enum::IntoPrimitive)]
pub enum RemoteSysTask {
    Kernel = 0,
    CoreApp = 1,
    #[num_enum(catch_all)]
    Unknown(u8),
}

// Tracks who owns the underlying data buffer of an IpcMessage.
// This determines whether the buffer needs to be freed via `ipc_message_free` on drop.
#[derive(uDebug, Copy, Clone, PartialEq, Eq)]
enum DataOwnership {
    /// Data is a slice owned by the app; no cleanup required on drop.
    App,
    /// Data points into an IPC receive buffer owned by the kernel;
    /// must be released via `ipc_message_free` on drop.
    IpcBuffer,
}

/// A single IPC message, either outgoing (constructed with [`new`](IpcMessage::new))
/// or incoming (received from an [`IpcInbox`]).
///
/// All fields are private. Use the accessor methods to read them.
///
/// Dropping a message received from an [`IpcInbox`] automatically frees
/// the kernel-owned receive buffer.
#[derive(uDebug, PartialEq, Eq)]
pub struct IpcMessage<'a> {
    remote: RemoteSysTask,
    service: u16,
    id: u16,
    data: &'a [u8],
    data_ownership: DataOwnership,
}

impl IpcMessage<'_> {
    /// Returns the service ID this message belongs to.
    pub fn service(&self) -> u16 {
        self.service
    }

    /// Returns the message ID within its service.
    pub fn id(&self) -> u16 {
        self.id
    }

    /// Returns the raw message payload.
    pub fn data(&self) -> &[u8] {
        self.data
    }

    /// Returns the remote task this message was received from or will be sent to.
    pub fn remote(&self) -> RemoteSysTask {
        self.remote
    }
}

impl<'a> IpcMessage<'a> {
    /// Constructs an outgoing `IpcMessage` with the given message ID and payload.
    ///
    /// The `remote` task and `service` are supplied later at [`send`](IpcMessage::send) time.
    pub fn new(id: u16, data: &'a [u8]) -> Self {
        Self {
            remote: RemoteSysTask::Unknown(0xff),
            service: 0,
            id: id.into(),
            data,
            data_ownership: DataOwnership::App,
        }
    }

    /// Constructs an `IpcMessage` from a low-level `ipc_message_t` received from the kernel.
    ///
    /// Returns `None` if the remote task ID is unrecognised.
    ///
    /// # Safety
    ///
    /// `lowlevel_message` must be a valid `ipc_message_t` returned by `ipc_try_receive`.
    /// The returned `IpcMessage` borrows the kernel-owned IPC buffer with an unbounded
    /// lifetime — the caller must constrain it to the lifetime of the corresponding [`IpcInbox`].
    unsafe fn from_lowlevel(lowlevel_message: ffi::ipc_message_t) -> Option<Self> {
        let remote = RemoteSysTask::try_from(lowlevel_message.remote).ok()?;
        let fn_ = Fn::from_fn(lowlevel_message.fn_);
        // SAFETY: The data pointer is valid for the lifetime of the IPC buffer.
        // Constructing a slice with an unbounded lifetime is safe because the caller
        // is required to constrain it to the inbox lifetime.
        let data = unsafe {
            core::slice::from_raw_parts(lowlevel_message.data as *const u8, lowlevel_message.size)
        };
        Some(Self {
            remote,
            service: fn_.service,
            id: fn_.message_id,
            data,
            data_ownership: DataOwnership::IpcBuffer,
        })
    }

    /// Sends this message to `remote` using the given `service` ID.
    ///
    /// Returns `Err` if the underlying `ipc_send` call fails.
    pub fn send(&self, remote: RemoteSysTask, service: u16) -> Result<(), ApiError> {
        let fn_ = Fn::to_fn(service, self.id);
        low_level_api::ipc_send(remote.into(), fn_, self.data)
    }
}

impl Drop for IpcMessage<'_> {
    fn drop(&mut self) {
        if matches!(self.data_ownership, DataOwnership::App) {
            // App-owned data is a plain slice reference — nothing to free.
            return;
        }
        // Reconstruct the original `ipc_message_t` so the kernel can reclaim
        // the receive buffer. The fields must match exactly what was received.
        let lowlevel_message = ffi::ipc_message_t {
            remote: self.remote.into(),
            fn_: Fn::to_fn(self.service as u16, self.id),
            data: self.data.as_ptr() as *const _,
            size: self.data.len(),
        };
        // SAFETY:
        // * We are in `drop`, so no other reference to `self.data` can exist.
        // * The message is reconstructed field-for-field from its received values.
        unsafe { low_level_api::ipc_message_free(lowlevel_message) };
    }
}

/// An IPC receive inbox for a specific remote task.
///
/// Registers a caller-supplied buffer with the kernel on [`register`](IpcInbox::register),
/// allowing the kernel to write incoming messages into it. Incoming messages are
/// retrieved with [`try_receive`](IpcInbox::try_receive).
///
/// The inbox unregisters itself (clearing the kernel-held pointer) when dropped.
///
/// # Layout
///
/// `repr(C)` is required because the struct pointer is passed to the kernel.
#[repr(C)]
pub struct IpcInbox<'a> {
    remote: RemoteSysTask,
    buffer: *mut u8,
    buf_len: usize,
    // Holds a mutable borrow of the underlying buffer slice, preventing any
    // other code from aliasing it while the inbox is alive.
    _borrow: PhantomData<&'a mut [usize]>,
}

impl<'a> IpcInbox<'a> {
    /// Creates a new inbox for `remote`, backed by `buffer`.
    ///
    /// `buffer` is a `&mut [usize]` to guarantee pointer alignment required by the kernel.
    /// Call [`register`](IpcInbox::register) before polling for messages.
    pub const fn new(remote: RemoteSysTask, buffer: &'a mut [usize]) -> Self {
        Self {
            remote,
            buffer: buffer.as_ptr() as *mut _,
            buf_len: buffer.len() * core::mem::size_of::<usize>(),
            _borrow: PhantomData,
        }
    }

    /// Registers the inbox buffer with the kernel.
    ///
    /// Must be called before [`try_receive`](IpcInbox::try_receive).
    /// Panics in debug builds if registration fails (e.g. null or misaligned pointer).
    pub fn register(&self) {
        // SAFETY:
        // * `_borrow` holds exclusive access to the buffer for `'a`.
        // * We pass a raw pointer (not a reference) so the kernel can write into it
        //   without invalidating any Rust reference.
        // * No other code touches the buffer while the inbox is alive.
        let _result =
            unsafe { low_level_api::ipc_register(self.remote.into(), self.buffer, self.buf_len) };
        // Can only fail if the pointer is NULL or not aligned to `usize` — neither
        // should be possible given the `&mut [usize]` constructor.
        debug_assert!(_result.is_ok(), "Failed to register IPC");
    }

    /// Polls for an incoming message without blocking.
    ///
    /// Returns `Some(IpcMessage)` if a message is available, or `None` otherwise.
    /// The returned message borrows the inbox buffer and must be dropped before
    /// the inbox itself is dropped or re-registered.
    pub fn try_receive(&self) -> Option<IpcMessage<'a>> {
        let lowlevel_message = low_level_api::ipc_try_receive(self.remote.into()).ok()?;
        // SAFETY: The message was just returned by `ipc_try_receive` and its
        // lifetime is tied to `'a`, i.e. the lifetime of the inbox buffer.
        unsafe { IpcMessage::from_lowlevel(lowlevel_message) }
    }

    /// Returns the remote task this inbox is registered for.
    pub fn remote(&self) -> RemoteSysTask {
        self.remote
    }
}

impl<'a> Drop for IpcInbox<'a> {
    fn drop(&mut self) {
        // Clear the kernel-held pointer before the buffer is released.
        // Without this, the kernel could write into freed memory.
        low_level_api::ipc_unregister(self.remote.into());
    }
}

// SAFETY:
// `IpcInbox` contains a `*mut u8` which is not `Sync` by default.
// However, the pointer is only ever passed to the kernel via `register()` —
// we never dereference it ourselves — so sharing the inbox across threads is safe.
// (In practice the firmware is single-threaded, so this is moot.)
unsafe impl Sync for IpcInbox<'_> {}
