use core::ffi::c_void;

use super::ffi::{self, ipc_message_t, log_source_t};
#[cfg(not(feature = "test"))]
use super::ffi::{HMAC_SHA256_CTX, SHA3_CTX, SHA256_CTX, SHA512_CTX};
#[cfg(not(feature = "test"))]
use crate::crypto::Hasher;
use crate::unwrap;

pub const TREZOR_API_SUPPORTED_VERSION: u32 = 1;

unsafe impl Send for ffi::trezor_crypto_v1_t {}
unsafe impl Sync for ffi::trezor_crypto_v1_t {}
unsafe impl Send for ffi::trezor_api_v1_t {}
unsafe impl Sync for ffi::trezor_api_v1_t {}

/// Global API singleton - initialized once and then immutable
pub static API: spin::Once<&'static ffi::trezor_api_v1_t> = spin::Once::new();

/// API errors
#[derive(ufmt::derive::uDebug, Clone, Copy, PartialEq, Eq)]
#[cfg_attr(any(feature = "debug", feature = "test"), derive(Debug))]
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

    pub fn message(&self) -> &'static str {
        match self {
            ApiError::NotInitialized => "API not initialized",
            ApiError::UnsupportedVersion => "Unsupported API version",
            ApiError::InvalidFunction => "Invalid function pointer",
            ApiError::InvalidMessage => "Invalid message pointer",
            ApiError::Failed => "Operation failed",
        }
    }
}

#[cfg(feature = "debug")]
impl core::fmt::Display for ApiError {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        write!(f, "{}", self.message())
    }
}

#[cfg(feature = "debug")]
impl core::error::Error for ApiError {}

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
        // SAFETY: Safe, assuming getter itself is ok.
        let ptr = unsafe { unwrap!(getter)(TREZOR_API_SUPPORTED_VERSION) };
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

#[inline]
pub(crate) fn get_crypto_or_die() -> &'static ffi::trezor_crypto_v1_t {
    unsafe {
        (get_or_die().trezor_crypto_v1)
            .as_ref()
            .expect("Crypto API getter returned null pointer")
    }
}

/// Free resources associated with a received IPC message
///
/// # Safety
///
/// Should only be called with the `ipc_message_t` struct exactly as returned by
/// `ipc_try_receive`. The data pointed to by its `data` field may be
/// invalidated and overwritten.
pub unsafe fn ipc_message_free(mut msg: ipc_message_t) {
    unsafe { unwrap!(get_or_die().ipc_message_free)(&mut msg) };
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
    let result =
        unsafe { unwrap!(get_or_die().ipc_register)(remote, buffer as *mut c_void, buf_len) };
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
    unsafe { unwrap!(get_or_die().ipc_unregister)(remote) };
}

pub fn ipc_send(remote: ffi::systask_id_t, fn_: u32, bytes: &[u8]) -> Result<(), ApiError> {
    let result = unsafe {
        unwrap!(get_or_die().ipc_send)(remote, fn_, bytes.as_ptr() as *const c_void, bytes.len())
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
    let result = unsafe { unwrap!(get_or_die().ipc_try_receive)(&mut msg) };
    if result {
        Ok(msg)
    } else {
        Err(ApiError::Failed)
    }
}

pub fn sysevents_poll(awaited: &ffi::sysevents_t, signalled: &mut ffi::sysevents_t, deadline: u32) {
    unsafe { unwrap!(get_or_die().sysevents_poll)(awaited, signalled, deadline) };
}

pub fn systick_ms() -> u32 {
    unsafe { unwrap!(get_or_die().systick_ms)() }
}

pub fn dbg_console_write(data: &[u8]) {
    unsafe { unwrap!(get_or_die().dbg_console_write)(data.as_ptr() as *const c_void, data.len()) };
}

pub fn syslog_start_record(module_name: &[u8], log_level: u32) {
    unsafe {
        let source = log_source_t {
            name: module_name.as_ptr() as *const _,
            name_len: module_name.len(),
        };
        unwrap!(get_or_die().syslog_start_record)(&source as *const _, log_level)
    };
}

pub fn syslog_write_chunk(data: &[u8], is_last_chunk: bool) {
    unsafe {
        unwrap!(get_or_die().syslog_write_chunk)(
            data.as_ptr() as *const _,
            data.len(),
            is_last_chunk,
        )
    };
}

pub fn system_exit() -> ! {
    if let Some(api) = API.get() {
        // If the API was initialized, we call its system_exit function.
        unsafe { unwrap!(api.system_exit)(0) };
    }
    // If API is not initialized, or if `system_exit` returns despite not being
    // supposed to, we abort.
    core::intrinsics::abort();
}

pub fn system_exit_error(title: &str, message: &str, footer: &str) -> ! {
    if let Some(api) = API.get() {
        unsafe {
            unwrap!(api.system_exit_error_ex)(
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
            unwrap!(api.system_exit_fatal_ex)(
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

pub(crate) fn app_get_heap() -> Result<&'static [u8], ApiError> {
    unsafe {
        let mut heap_ptr: *mut c_void = core::ptr::null_mut();
        let mut heap_size: usize = 0;
        let status = unwrap!(get_or_die().app_get_heap)(
            &mut heap_ptr as *mut *mut c_void,
            &mut heap_size as *mut usize,
        );
        if status.code != 0 {
            return Err(ApiError::Failed);
        }
        Ok(core::slice::from_raw_parts(
            heap_ptr as *const u8,
            heap_size,
        ))
    }
}

pub(crate) fn ed25519_sign_open(
    public_key: &[u8; 32],
    signature: &[u8; 64],
    message: &[u8],
) -> i32 {
    unsafe {
        unwrap!(get_crypto_or_die().ed25519_sign_open)(
            message.as_ptr(),
            message.len(),
            public_key.as_ptr() as *const _,
            signature.as_ptr() as *const _,
        )
    }
}

pub(crate) fn ed25519_cosi_combine_publickeys(
    pks: &[ffi::ed25519_public_key],
    res: &mut [u8; 32],
) -> i32 {
    let n = pks.len();
    unsafe {
        unwrap!(get_crypto_or_die().ed25519_cosi_combine_publickeys)(
            res.as_mut_ptr(),
            pks.as_ptr() as *const _,
            n,
        )
    }
}

#[cfg(not(feature = "test"))]
pub struct Sha256 {
    ctx: SHA256_CTX,
}

#[cfg(not(feature = "test"))]
impl Sha256 {
    pub fn new(data: Option<&[u8]>) -> Self {
        let ctx = SHA256_CTX {
            state: [0u32; 8],
            bitcount: 0,
            buffer: [0u32; 16],
        };
        let mut hasher = Self { ctx };
        unsafe { unwrap!(get_crypto_or_die().sha256_Init)(&mut hasher.ctx) };
        if let Some(data) = data {
            Self::update(&mut hasher, data);
        }
        hasher
    }

    pub fn digest(&mut self) -> [u8; 32] {
        let mut digest = [0u8; 32];
        Self::finalize(self, &mut digest);
        digest
    }
}

#[cfg(not(feature = "test"))]
impl Hasher for Sha256 {
    fn update(&mut self, data: &[u8]) {
        unsafe {
            unwrap!(get_crypto_or_die().sha256_Update)(&mut self.ctx, data.as_ptr(), data.len())
        };
    }

    fn finalize(&mut self, output: &mut [u8]) {
        unsafe { unwrap!(get_crypto_or_die().sha256_Final)(&mut self.ctx, output.as_mut_ptr()) };
    }
}

#[cfg(not(feature = "test"))]
impl Drop for Sha256 {
    fn drop(&mut self) {
        unsafe {
            core::ptr::write_volatile(&mut self.ctx, core::mem::zeroed());
        }
    }
}

#[cfg(not(feature = "test"))]
pub struct Keccak256 {
    ctx: SHA3_CTX,
}

#[cfg(not(feature = "test"))]
impl Keccak256 {
    pub fn new(data: Option<&[u8]>) -> Self {
        let ctx = SHA3_CTX {
            hash: [0u64; 25usize],
            message: [0u64; 24usize],
            rest: 0,
            block_size: 0,
        };
        let mut hasher = Self { ctx };
        unsafe { unwrap!(get_crypto_or_die().sha3_256_Init)(&mut hasher.ctx) };
        if let Some(data) = data {
            Self::update(&mut hasher, data);
        }
        hasher
    }

    pub fn digest(&mut self) -> [u8; 32] {
        let mut digest = [0u8; 32];
        Self::finalize(self, &mut digest);
        digest
    }
}

#[cfg(not(feature = "test"))]
impl Hasher for Keccak256 {
    fn update(&mut self, data: &[u8]) {
        unsafe {
            unwrap!(get_crypto_or_die().sha3_Update)(&mut self.ctx, data.as_ptr(), data.len())
        };
    }

    fn finalize(&mut self, output: &mut [u8]) {
        unsafe { unwrap!(get_crypto_or_die().keccak_Final)(&mut self.ctx, output.as_mut_ptr()) };
    }
}

#[cfg(not(feature = "test"))]
impl Drop for Keccak256 {
    fn drop(&mut self) {
        unsafe {
            core::ptr::write_volatile(&mut self.ctx, core::mem::zeroed());
        }
    }
}

#[cfg(not(feature = "test"))]
pub struct Sha3_256 {
    ctx: SHA3_CTX,
}

#[cfg(not(feature = "test"))]
impl Sha3_256 {
    pub fn new(data: Option<&[u8]>) -> Self {
        let ctx = SHA3_CTX {
            hash: [0u64; 25usize],
            message: [0u64; 24usize],
            rest: 0,
            block_size: 0,
        };
        let mut hasher = Self { ctx };
        unsafe { unwrap!(get_crypto_or_die().sha3_256_Init)(&mut hasher.ctx) };
        if let Some(data) = data {
            Self::update(&mut hasher, data);
        }
        hasher
    }

    pub fn digest(&mut self) -> [u8; 32] {
        let mut digest = [0u8; 32];
        Self::finalize(self, &mut digest);
        digest
    }
}

#[cfg(not(feature = "test"))]
impl Hasher for Sha3_256 {
    fn update(&mut self, data: &[u8]) {
        unsafe {
            unwrap!(get_crypto_or_die().sha3_Update)(&mut self.ctx, data.as_ptr(), data.len())
        };
    }

    fn finalize(&mut self, output: &mut [u8]) {
        unsafe { unwrap!(get_crypto_or_die().sha3_Final)(&mut self.ctx, output.as_mut_ptr()) };
    }
}

#[cfg(not(feature = "test"))]
impl Drop for Sha3_256 {
    fn drop(&mut self) {
        unsafe {
            core::ptr::write_volatile(&mut self.ctx, core::mem::zeroed());
        }
    }
}

#[cfg(not(feature = "test"))]
pub struct Sha512 {
    ctx: SHA512_CTX,
}

#[cfg(not(feature = "test"))]
impl Sha512 {
    pub fn new(data: Option<&[u8]>) -> Self {
        let ctx = SHA512_CTX {
            state: [0u64; 8],
            bitcount: [0u64; 2],
            buffer: [0u64; 16],
        };
        let mut hasher = Self { ctx };
        unsafe { unwrap!(get_crypto_or_die().sha512_Init)(&mut hasher.ctx) };
        if let Some(data) = data {
            Self::update(&mut hasher, data);
        }
        hasher
    }

    pub fn digest(&mut self) -> [u8; 64] {
        let mut digest = [0u8; 64];
        Self::finalize(self, &mut digest);
        digest
    }
}

#[cfg(not(feature = "test"))]
impl Hasher for Sha512 {
    fn update(&mut self, data: &[u8]) {
        unsafe {
            unwrap!(get_crypto_or_die().sha512_Update)(&mut self.ctx, data.as_ptr(), data.len())
        };
    }

    fn finalize(&mut self, output: &mut [u8]) {
        unsafe { unwrap!(get_crypto_or_die().sha512_Final)(&mut self.ctx, output.as_mut_ptr()) };
    }
}

#[cfg(not(feature = "test"))]
impl Drop for Sha512 {
    fn drop(&mut self) {
        unsafe {
            core::ptr::write_volatile(&mut self.ctx, core::mem::zeroed());
        }
    }
}

#[cfg(not(feature = "test"))]
pub struct HmacSha256 {
    ctx: HMAC_SHA256_CTX,
}

#[cfg(not(feature = "test"))]
impl HmacSha256 {
    pub fn new(key: &[u8], data: Option<&[u8]>) -> Self {
        let ctx = HMAC_SHA256_CTX {
            o_key_pad: [0u8; 64],
            ctx: SHA256_CTX {
                state: [0u32; 8],
                bitcount: 0,
                buffer: [0u32; 16],
            },
        };
        let mut hasher = Self { ctx };
        unsafe {
            unwrap!(get_crypto_or_die().hmac_sha256_Init)(
                &mut hasher.ctx,
                key.as_ptr(),
                key.len() as u32,
            )
        };
        if let Some(data) = data {
            Self::update(&mut hasher, data);
        }
        hasher
    }

    pub fn digest(&mut self) -> [u8; 32] {
        let mut digest = [0u8; 32];
        Self::finalize(self, &mut digest);
        digest
    }
}

#[cfg(not(feature = "test"))]
impl Hasher for HmacSha256 {
    fn update(&mut self, data: &[u8]) {
        unsafe {
            unwrap!(get_crypto_or_die().hmac_sha256_Update)(
                &mut self.ctx,
                data.as_ptr(),
                data.len() as u32,
            )
        };
    }

    fn finalize(&mut self, output: &mut [u8]) {
        unsafe {
            unwrap!(get_crypto_or_die().hmac_sha256_Final)(&mut self.ctx, output.as_mut_ptr())
        };
    }
}

#[cfg(not(feature = "test"))]
impl Drop for HmacSha256 {
    fn drop(&mut self) {
        unsafe {
            core::ptr::write_volatile(&mut self.ctx, core::mem::zeroed());
        }
    }
}
