//! Mock implementations for unit testing only.
//!
//! This module provides stub implementations of the Trezor crypto and API interfaces
//! intended exclusively for use in unit tests. It must **not** be used in production builds.
//!
//! Each implementation is explicitly marked as either:
//! - **Functional** — delegates to a real software implementation via a third-party crate.
//! - **Stub** — always returns a fixed error value, zero, `false`, or `null`; does not perform
//!   any real computation.

use std::alloc::{GlobalAlloc, System};

use mock_hmac_sha256::{HMAC as HMAC256_impl, Hash as Sha256_impl};
use mock_hmac_sha512::{HMAC as HMAC512_impl, Hash as Sha512_impl};
use mock_sha3::digest::FixedOutput;
use mock_sha3::{
    Digest, Keccak256 as Keccak256_impl, Keccak512 as Keccak512_impl, Sha3_256 as Sha3_256_impl,
    Sha3_512 as Sha3_512_impl,
};
use stabby::slice::{Slice, SliceMut};
use stabby::str::Str;

use super::crypto::Hasher;
use crate::traits::ApiVariant;
use crate::traits::allocator::{FfiLayout, GlobalAllocatorV1, GlobalAllocatorV1Vtable};
use crate::traits::crypto::{
    BoxedHasher, CryptoError, CryptoV1, CryptoV1Vtable, EcCurve, HashingAlgorithm,
};
use crate::traits::service::{IpcError, IpcRemote, IpcRemoteVtable, MessageRef};
use crate::traits::syslog::{
    LogCallbackDyn as _, LogCallbackRef, LogLevel, LogRecord, SyslogV1, SyslogV1Vtable,
};
use crate::traits::trezor_v1::{TrezorApiV1, TrezorApiV1Struct, TrezorApiV1Vtable};
use crate::traits::util::FastResult;

// ============================================================================
// Dummy implementation of the stable ABI, for host-based unit tests.
//
// Only `syslog` and (indirectly, via `std`'s allocator) `allocator` do
// anything real; nothing in the current test suite exercises `crypto`/`ipc`
// through this API — hashing goes straight to the `Sha256`/`Keccak256`/etc.
// mocks further down instead (see `crate::crypto::sha2`/`sha3`), and no test
// talks to a (nonexistent, in this context) Core over IPC.
// ============================================================================

struct DummyApi;

impl TrezorApiV1 for DummyApi {
    extern "C" fn init(&self) {}

    extern "C" fn system_exit(&self) -> ! {
        panic!("app called system_exit")
    }

    extern "C" fn system_exit_error<'a>(
        &self,
        title: Str<'a>,
        message: Str<'a>,
        _footer: Str<'a>,
    ) -> ! {
        panic!(
            "app called system_exit_error: {} / {}",
            title.as_str(),
            message.as_str()
        )
    }

    extern "C" fn system_exit_fatal<'a>(&self, message: Str<'a>, file: Str<'a>, line: u32) -> ! {
        panic!(
            "app called system_exit_fatal: {} at {}:{}",
            message.as_str(),
            file.as_str(),
            line
        )
    }

    extern "C" fn systick_ms(&self) -> u32 {
        0
    }

    extern "C" fn sleep(&self, _timeout_ms: u32) {}
}

struct DummyAllocator;

// SAFETY: forwards to `std::alloc::System`, a real, correct allocator.
unsafe impl GlobalAllocatorV1 for DummyAllocator {
    unsafe extern "C" fn alloc(&self, layout: FfiLayout) -> *mut u8 {
        unsafe { System.alloc(layout.into()) }
    }

    unsafe extern "C" fn dealloc(&self, ptr: *mut u8, layout: FfiLayout) {
        unsafe { System.dealloc(ptr, layout.into()) }
    }

    unsafe extern "C" fn alloc_zeroed(&self, layout: FfiLayout) -> *mut u8 {
        unsafe { System.alloc_zeroed(layout.into()) }
    }

    unsafe extern "C" fn realloc(
        &self,
        ptr: *mut u8,
        layout: FfiLayout,
        new_size: usize,
    ) -> *mut u8 {
        unsafe { System.realloc(ptr, layout.into(), new_size) }
    }
}

struct DummyCrypto;

impl CryptoV1 for DummyCrypto {
    extern "C" fn get_hasher(&self, _algorithm: HashingAlgorithm) -> BoxedHasher {
        unimplemented!("tests use crate::crypto::sha2/sha3, which bypass this vtable")
    }

    extern "C" fn get_hmac_hasher<'a>(&self, _key: Slice<'a, u8>) -> BoxedHasher {
        unimplemented!("tests use crate::crypto::hmac, which bypasses this vtable")
    }

    extern "C" fn hasher_update<'a>(&self, _hasher: BoxedHasher, _input: Slice<'a, u8>) {
        unimplemented!("tests use crate::crypto::sha2/sha3, which bypass this vtable")
    }

    extern "C" fn hasher_finalize(&self, _hasher: BoxedHasher) -> stabby::boxed::BoxedSlice<u8> {
        unimplemented!("tests use crate::crypto::sha2/sha3, which bypass this vtable")
    }

    extern "C" fn ec_verify_recover<'a>(
        &self,
        _curve: EcCurve,
        _public_key: Slice<'a, u8>,
        _signature: Slice<'a, u8>,
        _message: Slice<'a, u8>,
    ) -> FastResult<stabby::boxed::BoxedSlice<u8>, CryptoError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn ec_verify_recover_digest<'a>(
        &self,
        _curve: EcCurve,
        _public_key: Slice<'a, u8>,
        _signature: Slice<'a, u8>,
        _digest: Slice<'a, u8>,
    ) -> FastResult<stabby::boxed::BoxedSlice<u8>, CryptoError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn base58_encode<'a>(&self, _data: Slice<'a, u8>) -> stabby::string::String {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn base58_decode<'a>(
        &self,
        _data: Str<'a>,
    ) -> FastResult<stabby::boxed::BoxedSlice<u8>, CryptoError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn base58check_encode<'a>(&self, _data: Slice<'a, u8>) -> stabby::string::String {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn base58check_decode<'a>(
        &self,
        _data: Str<'a>,
    ) -> FastResult<stabby::boxed::BoxedSlice<u8>, CryptoError> {
        unimplemented!("not exercised by the current test suite")
    }
}

struct DummySyslog;

impl LogRecord for DummySyslog {
    extern "C" fn write<'a>(&self, string: Str<'a>) -> FastResult<(), ()> {
        print!("{}", string.as_str());
        Ok(()).into()
    }
}

impl SyslogV1 for DummySyslog {
    extern "C" fn log_simple<'a>(&self, _level: LogLevel, message: Str<'a>) {
        println!("{}", message.as_str());
    }

    extern "C" fn log<'a>(&self, _level: LogLevel, callback: LogCallbackRef<'a>) {
        callback.call(self.into());
        println!();
    }
}

struct DummyIpc;

impl IpcRemote for DummyIpc {
    extern "C" fn register_inbox<'remote, 'local>(&'remote self, _buffer: SliceMut<'local, usize>) {
    }

    extern "C" fn receive<'remote>(
        &'remote self,
        _timeout_ms: u32,
    ) -> FastResult<MessageRef<'remote>, IpcError<'remote>> {
        Err(IpcError::Timeout).into()
    }

    extern "C" fn send<'remote, 'local>(
        &'remote self,
        _service: u16,
        _id: u16,
        _message: Slice<'local, u8>,
    ) -> FastResult<(), IpcError<'remote>> {
        Err(IpcError::FailedToSend).into()
    }

    extern "C" fn call<'remote, 'local>(
        &'remote self,
        _service: u16,
        _id: u16,
        _message: Slice<'local, u8>,
        _timeout_ms: u32,
    ) -> FastResult<MessageRef<'remote>, IpcError<'remote>> {
        Err(IpcError::Timeout).into()
    }
}

static DUMMY_API: TrezorApiV1Struct = TrezorApiV1Struct {
    api: stabby::dynref_static!(DummyApi as TrezorApiV1Vtable),
    allocator: stabby::dynref_static!(DummyAllocator as GlobalAllocatorV1Vtable),
    crypto: stabby::dynref_static!(DummyCrypto as CryptoV1Vtable),
    syslog: stabby::dynref_static!(DummySyslog as SyslogV1Vtable),
    ipc: stabby::dynref_static!(DummyIpc as IpcRemoteVtable),
};

extern "C" fn dummy_api_getter(version: u32) -> ApiVariant {
    match version {
        1 => ApiVariant::V1(&DUMMY_API),
        _ => panic!("unsupported API version: {version}"),
    }
}

/// Initializes the app-side SDK with a dummy stable-ABI implementation, so
/// `app_runtime2`-backed code (logging, `Timeout`, etc.) doesn't panic with
/// "API not initialized" in unit tests. Idempotent: call it as many times as
/// you like, from as many tests as you like — only the first call matters.
pub fn sdk_init() {
    // SAFETY: `dummy_api_getter` is a valid `ApiGetter`.
    unsafe {
        crate::app_runtime2::applet_main(dummy_api_getter);
    }
}

// ============================================================================
// Functional hash / HMAC implementations (via third-party crates)
// ============================================================================
//
// All structs below delegate to real software implementations and produce
// correct cryptographic output. They are safe to use in unit tests that
// need to verify hash or HMAC correctness.

// Sha functions

/// **Functional** — delegates to `mock_hmac_sha256::Hash` (software SHA-256).
pub struct Sha256 {
    ctx: Sha256_impl,
}

impl Sha256 {
    pub fn new(data: Option<&[u8]>) -> Self {
        let ctx = Sha256_impl::new();
        let mut hasher = Self { ctx };
        if let Some(data) = data {
            Self::update(&mut hasher, data);
        }
        hasher
    }

    pub fn digest(&mut self) -> [u8; 32] {
        self.ctx.clone().finalize()
    }
}

impl Drop for Sha256 {
    fn drop(&mut self) {
        unsafe {
            core::ptr::write_volatile(&mut self.ctx, core::mem::zeroed());
        }
    }
}

impl Hasher for Sha256 {
    fn update(&mut self, data: &[u8]) {
        self.ctx.update(data);
    }

    fn finalize(&mut self, output: &mut [u8]) {
        let digest = self.ctx.clone().finalize();
        output.copy_from_slice(digest.as_slice());
    }
}

/// **Functional** — delegates to `mock_hmac_sha512::Hash` (software SHA-512).
pub struct Sha512 {
    ctx: Sha512_impl,
}

impl Sha512 {
    pub fn new(data: Option<&[u8]>) -> Self {
        let ctx = Sha512_impl::new();
        let mut hasher = Self { ctx };
        if let Some(data) = data {
            Self::update(&mut hasher, data);
        }
        hasher
    }

    pub fn digest(&mut self) -> [u8; 64] {
        self.ctx.clone().finalize()
    }
}

impl Drop for Sha512 {
    fn drop(&mut self) {
        unsafe {
            core::ptr::write_volatile(&mut self.ctx, core::mem::zeroed());
        }
    }
}

impl Hasher for Sha512 {
    fn update(&mut self, data: &[u8]) {
        self.ctx.update(data);
    }

    fn finalize(&mut self, output: &mut [u8]) {
        let digest = Sha512::digest(self);
        output.copy_from_slice(digest.as_slice());
    }
}
// Sha3 functions

/// **Functional** — delegates to `mock_sha3::Keccak256` (software Keccak-256).
pub struct Keccak256 {
    ctx: Keccak256_impl,
}

impl Keccak256 {
    pub fn new(data: Option<&[u8]>) -> Self {
        let ctx = Keccak256_impl::new();
        let mut hasher = Self { ctx };
        if let Some(data) = data {
            Self::update(&mut hasher, data);
        }
        hasher
    }

    pub fn digest(&mut self) -> [u8; 32] {
        let mut out = [0u8; 32];
        Self::finalize(self, &mut out);
        out
    }
}

impl Hasher for Keccak256 {
    fn update(&mut self, data: &[u8]) {
        self.ctx.update(data);
    }

    fn finalize(&mut self, output: &mut [u8]) {
        output.copy_from_slice(self.ctx.clone().finalize_fixed().as_slice());
    }
}

impl Drop for Keccak256 {
    fn drop(&mut self) {
        self.ctx.reset();
    }
}

/// **Functional** — delegates to `mock_sha3::Sha3_256` (software SHA3-256).
pub struct Sha3_256 {
    ctx: Sha3_256_impl,
}

impl Sha3_256 {
    pub fn new(data: Option<&[u8]>) -> Self {
        let ctx = Sha3_256_impl::new();
        let mut hasher = Self { ctx };
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

impl Hasher for Sha3_256 {
    fn update(&mut self, data: &[u8]) {
        self.ctx.update(data);
    }

    fn finalize(&mut self, output: &mut [u8]) {
        output.copy_from_slice(self.ctx.clone().finalize_fixed().as_slice());
    }
}

impl Drop for Sha3_256 {
    fn drop(&mut self) {
        self.ctx.reset();
    }
}

/// **Functional** — delegates to `mock_sha3::Keccak256` (software Keccak-512).
pub struct Keccak512 {
    ctx: Keccak512_impl,
}

impl Keccak512 {
    pub fn new(data: Option<&[u8]>) -> Self {
        let ctx = Keccak512_impl::new();
        let mut hasher = Self { ctx };
        if let Some(data) = data {
            Self::update(&mut hasher, data);
        }
        hasher
    }

    pub fn digest(&mut self) -> [u8; 64] {
        let mut out = [0u8; 64];
        Self::finalize(self, &mut out);
        out
    }
}

impl Hasher for Keccak512 {
    fn update(&mut self, data: &[u8]) {
        self.ctx.update(data);
    }

    fn finalize(&mut self, output: &mut [u8]) {
        output.copy_from_slice(self.ctx.clone().finalize_fixed().as_slice());
    }
}

impl Drop for Keccak512 {
    fn drop(&mut self) {
        self.ctx.reset();
    }
}

/// **Functional** — delegates to `mock_sha3::Sha3_512` (software SHA3-512).
pub struct Sha3_512 {
    ctx: Sha3_512_impl,
}

impl Sha3_512 {
    pub fn new(data: Option<&[u8]>) -> Self {
        let ctx = Sha3_512_impl::new();
        let mut hasher = Self { ctx };
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

impl Drop for Sha3_512 {
    fn drop(&mut self) {
        self.ctx.reset();
    }
}

impl Hasher for Sha3_512 {
    fn update(&mut self, data: &[u8]) {
        self.ctx.update(data);
    }

    fn finalize(&mut self, output: &mut [u8]) {
        output.copy_from_slice(self.ctx.clone().finalize_fixed().as_slice());
    }
}

// HMAC functions

/// **Functional** — delegates to `mock_hmac_sha256::HMAC` (software HMAC-SHA-256).
pub struct HmacSha256 {
    ctx: HMAC256_impl,
}

impl HmacSha256 {
    pub fn new(key: &[u8], data: Option<&[u8]>) -> Self {
        let ctx = HMAC256_impl::new(key);
        let mut hasher = Self { ctx };
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

impl Hasher for HmacSha256 {
    fn update(&mut self, data: &[u8]) {
        self.ctx.update(data);
    }

    fn finalize(&mut self, output: &mut [u8]) {
        output.copy_from_slice(self.ctx.clone().finalize().as_slice());
    }
}

impl Drop for HmacSha256 {
    fn drop(&mut self) {
        unsafe {
            core::ptr::write_volatile(&mut self.ctx, core::mem::zeroed());
        }
    }
}

/// **Functional** — delegates to `mock_hmac_sha512::HMAC` (software HMAC-SHA-512).
pub struct HmacSha512 {
    ctx: HMAC512_impl,
}

impl HmacSha512 {
    pub fn new(key: &[u8], data: Option<&[u8]>) -> Self {
        let ctx = HMAC512_impl::new(key);
        let mut hasher = Self { ctx };
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

impl Hasher for HmacSha512 {
    fn update(&mut self, data: &[u8]) {
        self.ctx.update(data);
    }

    fn finalize(&mut self, output: &mut [u8]) {
        // output.copy_from_slice(self.ctx.clone().finalize().as_slice());
        let ctx = core::mem::replace(&mut self.ctx, HMAC512_impl::new(&[]));
        let digest = ctx.finalize();
        output.copy_from_slice(&digest);
    }
}

impl Drop for HmacSha512 {
    fn drop(&mut self) {
        unsafe {
            core::ptr::write_volatile(&mut self.ctx, core::mem::zeroed());
        }
    }
}
