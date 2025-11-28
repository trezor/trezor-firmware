use core::marker::PhantomData;

use ufmt::derive::uDebug;

use crate::{low_level_api::{self, ApiError, ffi}};
use crate::log::debug;

/// Helper struct to convert between `ipc_message_t.fn_` and a tuple of service, message_id.
struct Fn {
    service: u16,
    message_id: u16,
}

impl Fn {
    pub fn from_fn(fn_: u32) -> Self {
        Self {
            service: (fn_ >> 16) as u16,
            message_id: (fn_ & 0xffff) as u16,
        }
    }

    pub fn to_fn(service: u16, message_id: u16) -> u32 {
        (service as u32) << 16 | message_id as u32
    }
}

#[repr(u8)]
#[derive(uDebug, Copy, Clone, PartialEq, Eq, num_enum::FromPrimitive, num_enum::IntoPrimitive)]
pub enum RemoteSysTask {
    Kernel = 0,
    CoreApp = 1,
    #[num_enum(catch_all)]
    Unknown(u8),
}

/// Data ownership indicator for an IPC message.
#[derive(uDebug, Copy, Clone, PartialEq, Eq)]
enum DataOwnership {
    /// Message data is owned by the app.
    App,
    /// Message was received from IPC and its data is owned by the IPC buffer.
    IpcBuffer,
}

/// IPC message.
///
/// All fields are private to prevent callers from modifying them.
/// Use accessor methods to read their values.
#[derive(uDebug, PartialEq, Eq)]
pub struct IpcMessage<'a> {
    remote: RemoteSysTask,
    service: u16,
    id: u16,
    data: &'a [u8],
    data_ownership: DataOwnership,
}

impl IpcMessage<'_> {
    pub fn service(&self) -> u16 {
        self.service
    }

    pub fn id(&self) -> u16 {
        self.id
    }

    pub fn data(&self) -> &[u8] {
        self.data
    }
}

impl<'a> IpcMessage<'a> {
    /// Construct an `IpcMessage` for sending to a remote task.
    pub fn new(id: u16, data: &'a [u8]) -> Self {
        Self {
            // remote is specified at send time
            remote: RemoteSysTask::Unknown(0xff),
            // service is specified at send time
            service: 0,
            id: id.into(),
            data,
            data_ownership: DataOwnership::App,
        }
    }

    /// Construct a `IpcMessage` from a low-level `ipc_message_t` struct.
    ///
    /// # Safety
    ///
    /// The `lowlevel_message` must be a valid `ipc_message_t` struct returned
    /// by `ipc_try_receive`. The returned `IpcMessage` has an unbounded
    /// lifetime, which must be constrained to the lifetime of the respective
    /// IPC inbox.
    unsafe fn from_lowlevel(lowlevel_message: ffi::ipc_message_t) -> Option<Self> {
        debug!("Received ipc_message_t: {:?}", lowlevel_message);
        let remote = RemoteSysTask::try_from(lowlevel_message.remote).ok()?;
        let fn_ = Fn::from_fn(lowlevel_message.fn_);
        // SAFETY:
        // If this message was received from kernel, the data pointer is valid.
        // However, we are constructing a slice with an unbounded lifetime, it is up to the caller
        // to constrain it properly.
        let data = unsafe {
            core::slice::from_raw_parts(lowlevel_message.data as *const u8, lowlevel_message.size)
        };
        let new = Self {
            remote,
            service: fn_.service,
            id: fn_.message_id,
            data,
            data_ownership: DataOwnership::IpcBuffer,
        };
        debug!("Constructed IpcMessage: {:?}", new);
        Some(new)
    }

    /// Send the message to a remote task.
    pub fn send(&self, remote: RemoteSysTask, service: u16) -> Result<(), ApiError> {
        let fn_ = Fn::to_fn(service, self.id);
        low_level_api::ipc_send(remote.into(), fn_, self.data)
    }
}

impl Drop for IpcMessage<'_> {
    fn drop(&mut self) {
        if matches!(self.data_ownership, DataOwnership::App) {
            // no special handling for app-owned data
            return;
        }
        let lowlevel_message = ffi::ipc_message_t {
            remote: self.remote.into(),
            fn_: Fn::to_fn(self.service as u16, self.id),
            data: self.data.as_ptr() as *const _,
            size: self.data.len(),
        };
        // SAFETY:
        // * we are dropping the message, so nobody should be retaining references
        //   to its data.
        // * the message is reconstructed exactly as it was when it was received.
        unsafe { low_level_api::ipc_message_free(lowlevel_message) };
    }
}

#[repr(C)]
pub struct IpcInbox<'a> {
    remote: RemoteSysTask,
    buffer: *mut u8,
    buf_len: usize,
    _borrow: PhantomData<&'a mut [usize]>,
}

impl<'a> IpcInbox<'a> {
    pub const fn new(remote: RemoteSysTask, buffer: &'a mut [usize]) -> Self {
        Self {
            remote,
            buffer: buffer.as_ptr() as *mut _,
            buf_len: buffer.len(),
            _borrow: PhantomData,
        }
    }

    pub fn register(&self) {
        // SAFETY:
        // We are handing off the pointer to the buffer to the kernel, and kernel will
        // write data into it. For that to work, we must:
        // * have exclusive access to the buffer (held mutably per PhantomData marker)
        // * not have a mutable reference that could become invalid (which is why we hold a pointer)
        // * and we must not give the pointer to anyone else (this is the only place touching the buffer)
        let _result =
            unsafe { low_level_api::ipc_register(self.remote.into(), self.buffer, self.buf_len) };
        // `ipc_register` should only fail if (a) buffer_ptr is NULL or (b) not aligned to usize.
        debug_assert!(_result.is_ok(), "Failed to register IPC");
    }

    pub fn try_receive(&self) -> Option<IpcMessage<'a>> {
        let lowlevel_message = low_level_api::ipc_try_receive(self.remote.into()).ok()?;
        unsafe { IpcMessage::from_lowlevel(lowlevel_message) }
    }

    pub fn remote(&self) -> RemoteSysTask {
        self.remote
    }
}

impl<'a> Drop for IpcInbox<'a> {
    fn drop(&mut self) {
        // unregistering the inbox in order to clear the about-to-be-dropped
        // pointer from kernel memory.
        low_level_api::ipc_unregister(self.remote.into());
    }
}

// SAFETY:
// Sharing a *mut u8 between threads is unsafe in the general case, but we are
// not touching the memory underneath it. We are only passing it to kernel in
// `register()`, and that would be safe to do concurrently from multiple
// threads.
//
// Oh and also let's not forget that we're not actually multi-threaded so not
// like this matters.
unsafe impl Sync for IpcInbox<'_> {}
