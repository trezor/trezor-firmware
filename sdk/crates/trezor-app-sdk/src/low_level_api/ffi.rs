#![allow(non_camel_case_types)]

/// FFI type definitions that mirror the C API without requiring bindgen.
/// These must stay in sync with the actual C types in core/embed/sys/ipc/api.h

/// Function pointer type for getting the API of a requested version.
/// This is passed to applet_main by the firmware.
/// Returns a non-null opaque pointer on success; null if the requested version is unsupported.
pub type trezor_api_getter_t = unsafe extern "C" fn(u32) -> *const core::ffi::c_void;
pub type ipc_fn_t = u16;

/// Current API version numbers
pub const TREZOR_API_VERSION_1: u32 = 1;

/// Maximum IPC message payload size in bytes
// pub const IPC_MSG_PAYLOAD_SIZE: usize = 256;

// pub const SYSHANDLE_SYSCALL: syshandle_t = 10;
pub const SYSHANDLE_IPC0: syshandle_t = 11;
// pub const SYSHANDLE_IPC1: syshandle_t = 12;
// pub const SYSHANDLE_IPC2: syshandle_t = 13;

/// IPC message structure
#[repr(C)]
#[derive(Debug, Copy, Clone)]
pub struct ipc_message_t {
    pub remote: systask_id_t,
    pub fn_: ipc_fn_t,
    pub data: *const ::core::ffi::c_void,
    pub size: usize,
}

impl Default for ipc_message_t {
    fn default() -> Self {
        Self {
            remote: 0,
            fn_: 0,
            data: core::ptr::null(),
            size: 0,
        }
    }
}

/// System events structure with read/write ready masks
#[repr(C)]
#[derive(Debug, Default, Copy, Clone)]
pub struct sysevents_t {
    /// Bitmask of handles ready for reading
    pub read_ready: u32,
    /// Bitmask of handles ready for writing
    pub write_ready: u32,
}

/// System handle type
pub type syshandle_t = u32;

/// Zero-based task ID (up to SYSTASK_MAX_TASKS - 1)
pub type systask_id_t = u8;

/// Trezor API v1 function pointers
#[repr(C)]
#[derive(Debug, Default, Copy, Clone)]
pub struct trezor_api_v1_t {
    pub system_exit: Option<unsafe extern "C" fn(exitcode: core::ffi::c_int)>,
    pub system_exit_error: Option<
        unsafe extern "C" fn(
            title: *const core::ffi::c_char,
            message: *const core::ffi::c_char,
            footer: *const core::ffi::c_char,
        ),
    >,
    pub system_exit_error_ex: Option<
        unsafe extern "C" fn(
            title: *const core::ffi::c_char,
            title_len: usize,
            message: *const core::ffi::c_char,
            message_len: usize,
            footer: *const core::ffi::c_char,
            footer_len: usize,
        ),
    >,
    pub system_exit_fatal: Option<
        unsafe extern "C" fn(
            message: *const core::ffi::c_char,
            file: *const core::ffi::c_char,
            line: core::ffi::c_int,
        ),
    >,
    pub system_exit_fatal_ex: Option<
        unsafe extern "C" fn(
            message: *const core::ffi::c_char,
            message_len: usize,
            file: *const core::ffi::c_char,
            file_len: usize,
            line: core::ffi::c_int,
        ),
    >,
    pub dbg_console_write:
        Option<unsafe extern "C" fn(data: *const core::ffi::c_void, size: usize)>,
    pub systick_ms: Option<unsafe extern "C" fn() -> u32>,
    pub sysevents_poll: Option<
        unsafe extern "C" fn(
            awaited: *const sysevents_t,
            signalled: *mut sysevents_t,
            deadline: u32,
        ),
    >,
    pub syshandle_read: Option<
        unsafe extern "C" fn(
            handle: syshandle_t,
            buffer: *mut core::ffi::c_void,
            buffer_size: usize,
        ) -> isize,
    >,
    pub ipc_register: Option<
        unsafe extern "C" fn(
            remote: systask_id_t,
            buffer: *mut core::ffi::c_void,
            size: usize,
        ) -> bool,
    >,
    pub ipc_unregister: Option<unsafe extern "C" fn(remote: systask_id_t)>,
    pub ipc_try_receive: Option<unsafe extern "C" fn(msg: *mut ipc_message_t) -> bool>,
    pub ipc_message_free: Option<unsafe extern "C" fn(msg: *mut ipc_message_t)>,
    pub ipc_send: Option<
        unsafe extern "C" fn(
            remote: systask_id_t,
            fn_: u32,
            data: *const core::ffi::c_void,
            data_size: usize,
        ) -> bool,
    >,
}
