use super::ffi::*;
use crate::Result;
use crate::{error, info, trace};
use core::ffi::c_void;
use once_cell::sync::OnceCell;

extern crate alloc;

/// Global API singleton - initialized once and then immutable
static API: OnceCell<Api> = OnceCell::new();

/// API errors
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ApiError {
    /// API not initialized
    NotInitialized,
    /// Requested API version is unsupported
    UnsupportedVersion,
    /// Invalid function pointer
    InvalidFunction,
    /// Invalid message pointer
    InvalidMessage,
    /// Operation failed
    Failed,
}

impl ApiError {
    /// Convert to C integer error code
    pub fn to_c_int(&self) -> i32 {
        match self {
            ApiError::NotInitialized => -1,
            ApiError::UnsupportedVersion => -5,
            ApiError::InvalidFunction => -2,
            ApiError::InvalidMessage => -3,
            ApiError::Failed => -4,
        }
    }
}

/// IPC message wrapper that ensures cleanup after use
#[derive(Default)]
pub(crate) struct IpcMessage {
    pub inner: ipc_message_t,
}

impl IpcMessage {
    /// Get reference to message
    pub fn inner(&self) -> &ipc_message_t {
        &self.inner
    }

    /// Get mutable reference to message
    pub fn inner_mut(&mut self) -> &mut ipc_message_t {
        &mut self.inner
    }
}

impl Drop for IpcMessage {
    fn drop(&mut self) {
        trace!("Freeing IPC message from remote {}", self.inner.remote);
        let _ = Api::ipc_message_free(&mut self.inner);
    }
}

/// API wrapper trait
pub(crate) trait ApiWrapper {
    /// Register a buffer for receiving IPC messages from a specific task
    fn ipc_register(remote: systask_id_t, buffer: &mut [u8]) -> Result<bool>;

    /// Make synchronous IPC call with timeout
    fn ipc_call(
        remote: systask_id_t,
        fn_: ipc_fn_t,
        bytes: &[u8],
        rsp: &mut IpcMessage,
        timeout: u32,
    ) -> Result<bool>;

    /// Try to receive an IPC message (non-blocking)
    fn ipc_try_receive(msg: &mut IpcMessage) -> Result<bool>;

    /// Send an IPC message
    fn ipc_send(remote: systask_id_t, fn_: ipc_fn_t, bytes: &[u8]) -> Result<bool>;

    /// Poll for system events
    fn sysevents_poll(
        awaited: &sysevents_t,
        signalled: &mut sysevents_t,
        deadline: u32,
    ) -> Result<()>;

    /// Get system tick in milliseconds
    fn systick_ms() -> Result<u32>;

    /// Write to debug console
    fn dbg_console_write(data: &[u8]) -> Result<()>;

    /// Exit the application with the given exit code
    fn system_exit(code: i32) -> Result<()>;

    /// Exit the applicaiton with a fatal error message
    fn system_exit_fatal(message: &str, file: &str, line: i32) -> Result<()>;
}

/// API wrapper that can be initialized from a getter function
///
/// This enum holds different versions of the API to support future extensions
pub(crate) enum Api {
    /// API version 1
    V1(trezor_api_v1_t),
}

impl Api {
    /// Initialize the global API singleton from getter function pointer
    ///
    /// This should be called once at the start of your applet_main with the
    /// api_get parameter passed by the firmware. Subsequent calls will fail.
    ///
    /// # Safety
    /// The getter function must return a valid pointer to the requested API
    pub fn init(getter: trezor_api_getter_t, version: u32) -> Result<()> {
        trace!("Initializing API with version {}", version);
        let ptr = unsafe { getter(version) };
        if ptr.is_null() {
            error!("API getter returned null pointer for version {}", version);
            return Err(ApiError::UnsupportedVersion);
        }

        let api_instance = match version {
            TREZOR_API_VERSION_1 => {
                trace!("Loading API v1");
                let v1_ptr = ptr as *const trezor_api_v1_t;
                unsafe { Self::V1(*v1_ptr) }
            }
            _ => {
                error!("Unsupported API version: {}", version);
                return Err(ApiError::UnsupportedVersion);
            }
        };

        API.set(api_instance).map_err(|_| {
            error!("API already initialized");
            ApiError::Failed
        })?;

        info!("API initialized successfully");
        Ok(())
    }

    /// Get a reference to the global API singleton
    ///
    /// Returns None if the API has not been initialized yet
    fn get() -> Result<&'static Self> {
        API.get().ok_or(ApiError::NotInitialized)
    }

    /// Free resources associated with a received IPC message
    fn ipc_message_free(msg: &mut ipc_message_t) -> Result<()> {
        match Self::get()? {
            Api::V1(api) => {
                if let Some(func) = api.ipc_message_free {
                    unsafe { func(msg as *mut _) };
                }
            }
        }
        Ok(())
    }
}

impl ApiWrapper for Api {
    fn ipc_register(remote: systask_id_t, buffer: &mut [u8]) -> Result<bool> {
        trace!(
            "Registering IPC for remote task {} with buffer size {}",
            remote,
            buffer.len()
        );
        match Self::get()? {
            Api::V1(api) => {
                let func = api.ipc_register.ok_or(ApiError::InvalidFunction)?;
                let result =
                    unsafe { func(remote, buffer.as_mut_ptr() as *mut c_void, buffer.len()) };
                trace!("IPC register result: {}", result);
                Ok(result)
            }
        }
    }

    fn ipc_call(
        remote: systask_id_t,
        fn_: ipc_fn_t,
        bytes: &[u8],
        rsp: &mut IpcMessage,
        timeout: u32,
    ) -> Result<bool> {
        trace!(
            "IPC call to remote {} fn {} with {} bytes, timeout {}ms",
            remote,
            fn_,
            bytes.len(),
            timeout
        );

        if Api::ipc_send(remote, fn_, bytes)? == false {
            error!("IPC send failed for remote {} fn {}", remote, fn_);
            return Ok(false);
        }

        let handle: syshandle_t = SYSHANDLE_IPC0 + remote as syshandle_t;
        let awaited = sysevents_t {
            read_ready: 1u32 << handle,
            ..sysevents_t::default()
        };
        let mut signalled = sysevents_t::default();
        Api::sysevents_poll(&awaited, &mut signalled, timeout)?;

        if (signalled.read_ready & (1u32 << handle)) != 0 {
            // Read the IPC message
            rsp.inner.remote = remote;
            let result = Api::ipc_try_receive(rsp)?;
            trace!(
                "IPC call completed successfully, received {} bytes",
                rsp.inner.size
            );
            return Ok(result);
        }

        error!("IPC call timeout after {}ms", timeout);
        Ok(false)
    }

    fn ipc_try_receive(msg: &mut IpcMessage) -> Result<bool> {
        match Self::get()? {
            Api::V1(api) => {
                let func = api.ipc_try_receive.ok_or(ApiError::InvalidFunction)?;
                let result = unsafe { func(msg.inner_mut() as *mut _) };
                if result {
                    trace!(
                        "IPC receive successful, got {} bytes from remote {}",
                        msg.inner.size,
                        msg.inner.remote
                    );
                }
                Ok(result)
            }
        }
    }

    fn ipc_send(remote: systask_id_t, fn_: ipc_fn_t, bytes: &[u8]) -> Result<bool> {
        trace!(
            "Sending IPC message to remote {} fn {} ({} bytes)",
            remote,
            fn_,
            bytes.len()
        );
        match Self::get()? {
            Api::V1(api) => {
                let func = api.ipc_send.ok_or(ApiError::InvalidFunction)?;
                let result =
                    unsafe { func(remote, fn_ as _, bytes.as_ptr() as *const c_void, bytes.len()) };
                if result {
                    trace!("IPC send successful");
                } else {
                    error!("IPC send returned false");
                }
                Ok(result)
            }
        }
    }

    fn sysevents_poll(
        awaited: &sysevents_t,
        signalled: &mut sysevents_t,
        deadline: u32,
    ) -> Result<()> {
        match Self::get()? {
            Api::V1(api) => {
                if let Some(func) = api.sysevents_poll {
                    unsafe { func(awaited as *const _, signalled as *mut _, deadline) };
                }
            }
        }
        Ok(())
    }

    fn systick_ms() -> Result<u32> {
        let ticks = match Self::get()? {
            Api::V1(api) => {
                if let Some(func) = api.systick_ms {
                    unsafe { func() }
                } else {
                    0
                }
            }
        };
        Ok(ticks)
    }

    fn dbg_console_write(data: &[u8]) -> Result<()> {
        match Self::get()? {
            Api::V1(api) => {
                let func = api.dbg_console_write.ok_or(ApiError::InvalidFunction)?;
                unsafe { func(data.as_ptr() as *const c_void, data.len()) };
            }
        };
        Ok(())
    }

    fn system_exit(code: i32) -> Result<()> {
        info!("System exit called with code: {}", code);
        match Self::get()? {
            Api::V1(api) => {
                let func = api.system_exit.ok_or(ApiError::InvalidFunction)?;
                unsafe { func(code as core::ffi::c_int) };
            }
        };
        Ok(())
    }

    fn system_exit_fatal(message: &str, file: &str, line: i32) -> Result<()> {
        match Self::get()? {
            Api::V1(api) => {
                let func = api.system_exit_fatal_ex.ok_or(ApiError::InvalidFunction)?;
                unsafe {
                    func(
                        message.as_ptr() as *const i8,
                        message.len(),
                        file.as_ptr() as *const i8,
                        file.len(),
                        line,
                    )
                };
            }
        }
        Ok(())
    }
}
