use core::ffi::c_void;

use super::ffi::{self, ipc_message_t};
use crate::log::info;

extern crate alloc;

pub const TREZOR_API_SUPPORTED_VERSION: u32 = ffi::TREZOR_API_VERSION_1;

/// Global API singleton - initialized once and then immutable
pub static API: spin::Once<&'static ffi::trezor_api_v1_t> = spin::Once::new();

/// API errors
#[derive(ufmt::derive::uDebug, Clone, Copy, PartialEq, Eq)]
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

/// Initialize the global API singleton from getter function pointer
///
/// This should be called once at the start of your applet_main with the
/// api_get parameter passed by the firmware. Subsequent calls will fail.
///
/// # Safety
///
/// The `getter` must be a valid function pointer to the API getter function.
pub unsafe fn init(getter: ffi::trezor_api_getter_t) {
    API.call_once(|| {
        info!(
            "Initializing API with version {}",
            TREZOR_API_SUPPORTED_VERSION
        );
        // SAFETY: Safe, assuming getter itself is ok.
        let ptr = unsafe { getter(TREZOR_API_SUPPORTED_VERSION) };
        // SAFETY: Getter returns null or a valid pointer to the API struct.
        let v1_ptr = unsafe { (ptr as *const ffi::trezor_api_v1_t).as_ref() };
        v1_ptr.expect("API getter returned null pointer")
    });
    crate::print::enable_api_printer();
}

pub fn is_initialized() -> bool {
    API.get().is_some()
}

/// Get a reference to the global API singleton
#[inline]
fn get_or_die() -> &'static ffi::trezor_api_v1_t {
    API.get().expect("API not initialized")
}

/// Free resources associated with a received IPC message
///
/// # Safety
///
/// Should only be called with the `ipc_message_t` struct exactly as returned by
/// `ipc_try_receive`. The data pointed to by its `data` field may be
/// invalidated and overwritten.
pub unsafe fn ipc_message_free(mut msg: ipc_message_t) {
    unsafe { (get_or_die().ipc_message_free)(&mut msg) };
}

/// Register an IPC inbox
///
/// # Safety
///
/// The pointer to `buffer` is registered in kernel, constituting effectively an
/// indefinite mutable borrow. This function has no way to indicate that to the
/// type system.
///
/// Therefore, the caller must ensure that the memory that `buffer` points to
/// remains valid until the inbox is unregistered.
pub unsafe fn ipc_register(
    remote: ffi::systask_id_t,
    buffer: *mut u8,
    buf_len: usize,
) -> Result<(), ApiError> {
    let result = unsafe { (get_or_die().ipc_register)(remote, buffer as *mut c_void, buf_len) };
    if result {
        Ok(())
    } else {
        Err(ApiError::Failed)
    }
}

/// Unregister an IPC inbox
///
/// # Safety
///
/// Safe to call from anywhere. No data is invalidated, this only causes the
/// kernel to forget about it.
pub fn ipc_unregister(remote: ffi::systask_id_t) {
    unsafe { (get_or_die().ipc_unregister)(remote) };
}

pub fn ipc_send(remote: ffi::systask_id_t, fn_: ffi::ipc_fn_t, bytes: &[u8]) -> Result<(), ApiError> {
    let result = unsafe {
        (get_or_die().ipc_send)(remote, fn_, bytes.as_ptr() as *const c_void, bytes.len())
    };
    if result {
        Ok(())
    } else {
        Err(ApiError::Failed)
    }
}

/// Try to receive an IPC message from the specified remote task.
///
/// # Safety
///
/// The received data pointer will point into the buffer registered via
/// `ipc_register` for the given remote.
/// The result should be freed by calling `ipc_message_free`.
pub fn ipc_try_receive(remote: ffi::systask_id_t) -> Result<ffi::ipc_message_t, ApiError> {
    let mut msg = ffi::ipc_message_t::default();
    msg.remote = remote;
    let result = unsafe { (get_or_die().ipc_try_receive)(&mut msg) };
    if result {
        Ok(msg)
    } else {
        Err(ApiError::Failed)
    }
}

pub fn sysevents_poll(awaited: &ffi::sysevents_t, signalled: &mut ffi::sysevents_t, deadline: u32) {
    unsafe { (get_or_die().sysevents_poll)(awaited, signalled, deadline) };
}

pub fn systick_ms() -> u32 {
    unsafe { (get_or_die().systick_ms)() }
}

pub fn dbg_console_write(data: &[u8]) {
    unsafe { (get_or_die().dbg_console_write)(data.as_ptr() as *const c_void, data.len()) };
}

pub fn system_exit() -> ! {
    if let Some(api) = API.get() {
        // If the API was initialized, we call its system_exit function.
        unsafe { (api.system_exit)(0) };
    }
    // If API is not initialized, or if `system_exit` returns despite not being
    // supposed to, we abort.
    core::intrinsics::abort();
}

pub fn system_exit_error(title: &str, message: &str, footer: &str) -> ! {
    if let Some(api) = API.get() {
        unsafe {
            (api.system_exit_error_ex)(
                title.as_ptr() as *const core::ffi::c_char,
                title.len(),
                message.as_ptr() as *const core::ffi::c_char,
                message.len(),
                footer.as_ptr() as *const core::ffi::c_char,
                footer.len(),
            )
        };
    }
    // If API is not initialized, or if `system_exit_error_ex` returns despite
    // not being supposed to, we abort.
    core::intrinsics::abort();
}

pub fn system_exit_fatal(message: &str, file: &str, line: i32) -> ! {
    if let Some(api) = API.get() {
        unsafe {
            (api.system_exit_fatal_ex)(
                message.as_ptr() as *const core::ffi::c_char,
                message.len(),
                file.as_ptr() as *const core::ffi::c_char,
                file.len(),
                line,
            )
        };
    }
    // If API is not initialized, or if `system_exit_fatal_ex` returns despite
    // not being supposed to, we abort.
    core::intrinsics::abort();
}
