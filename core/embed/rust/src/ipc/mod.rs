pub mod ffi;

/// Helper struct to convert between `ipc_message_t.fn_` and a tuple of service,
/// message_id.
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
#[derive(Copy, Clone, PartialEq, Eq, num_enum::FromPrimitive, num_enum::IntoPrimitive)]
pub enum RemoteSysTask {
    Kernel = 0,
    CoreApp = 1,
    #[num_enum(catch_all)]
    Unknown(u8),
}

/// Data ownership indicator for an IPC message.
#[derive(Copy, Clone, PartialEq, Eq)]
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
#[derive(PartialEq, Eq)]
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
        let remote = RemoteSysTask::try_from(lowlevel_message.remote).ok()?;
        let fn_ = Fn::from_fn(lowlevel_message.fn_);
        // SAFETY:
        // If this message was received from kernel, the data pointer is valid.
        // However, we are constructing a slice with an unbounded lifetime, it is up to
        // the caller to constrain it properly.
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
        Some(new)
    }

    /// Send the message to a remote task.
    pub fn send(&self, remote: RemoteSysTask, service: u16) -> Result<(), ()> {
        let fn_ = Fn::to_fn(service, self.id);
        unsafe {
            ffi::ipc_send(
                remote.into(),
                fn_,
                self.data.as_ptr() as *const _,
                self.data.len(),
            )
            .then_some(())
            .ok_or(())
        }
    }

    pub fn try_receive(remote: RemoteSysTask) -> Option<Self> {
        let mut lowlevel_message = ffi::ipc_message_t {
            remote: remote.into(),
            fn_: 0,
            data: core::ptr::null(),
            size: 0,
        };
        let rec = unsafe { ffi::ipc_try_receive(&mut lowlevel_message) };
        if rec {
            unsafe { Self::from_lowlevel(lowlevel_message) }
        } else {
            None
        }
    }
}

impl Drop for IpcMessage<'_> {
    fn drop(&mut self) {
        if matches!(self.data_ownership, DataOwnership::App) {
            // no special handling for app-owned data
            return;
        }
        let mut lowlevel_message = ffi::ipc_message_t {
            remote: self.remote.into(),
            fn_: Fn::to_fn(self.service as u16, self.id),
            data: self.data.as_ptr() as *const _,
            size: self.data.len(),
        };
        // SAFETY:
        // * we are dropping the message, so nobody should be retaining references to
        //   its data.
        // * the message is reconstructed exactly as it was when it was received.
        unsafe { ffi::ipc_message_free(&mut lowlevel_message) };
    }
}

#[derive(Copy, Clone, PartialEq, Eq, num_enum::IntoPrimitive, num_enum::FromPrimitive)]
#[repr(u16)]
pub enum CoreIpcService {
    Lifecycle = 0,
    Ui = 1,
    WireStart = 2,
    WireContinue = 3,
    WireEnd = 4,
    Crypto = 5,
    Util = 6,
    #[num_enum(catch_all)]
    Unknown(u16),
}
