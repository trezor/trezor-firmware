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
use stabby::boxed::{Box, BoxedSlice};
use stabby::slice::{Slice, SliceMut};
use stabby::str::Str;

use crate::traits::ApiVariant;
use crate::traits::allocator::{FfiLayout, GlobalAllocatorV1, GlobalAllocatorV1Vtable};
use crate::traits::crypto::{
    BoxedHasher, CryptoError, CryptoV1, CryptoV1Vtable, EcCurve, HashingAlgorithm, Hasher,
};
use crate::traits::syslog::{
    LogCallbackDyn as _, LogCallbackRef, LogLevel, LogRecord, SyslogV1, SyslogV1Vtable,
};
use crate::traits::trezor_v1::{TrezorApiV1, TrezorApiV1Struct, TrezorApiV1Vtable};
use crate::traits::ui::{
    ConfirmAction, ConfirmProperties, ConfirmSummary, ConfirmTrade, ConfirmValue,
    ConfirmValueIntro, ConfirmWithInfo, RequestNumber, SelectMenu, ShowAddress, ShowDanger,
    ShowInfoWithCancel, ShowMismatch, ShowProperties, ShowPublicKey, ShowSuccess, ShowWarning,
    TrezorUiResult, UiV1, UiV1Vtable,
};
use crate::traits::util::FastResult;
use crate::traits::wire::{WireError, WireMessage, WireV1, WireV1Vtable};

// ============================================================================
// Dummy implementation of the stable ABI, for host-based unit tests.
//
// `syslog`, `allocator` (indirectly, via `std`'s allocator), and `crypto`'s
// `get_hasher`/`get_hmac` (via the `Sha256`/`Keccak256`/etc. mocks further
// down) do real work; everything else in `crypto` and all of `ipc` are
// unimplemented — no test talks to a (nonexistent, in this context) Core
// over IPC.
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
    extern "C" fn get_hasher(&self, algorithm: HashingAlgorithm) -> BoxedHasher {
        match algorithm {
            HashingAlgorithm::Sha256 => Box::new(Sha256::new(None)).into(),
            HashingAlgorithm::Sha512 => Box::new(Sha512::new(None)).into(),
            HashingAlgorithm::Sha3_256 => Box::new(Sha3_256::new(None)).into(),
            HashingAlgorithm::Keccak256 => Box::new(Keccak256::new(None)).into(),
        }
    }

    extern "C" fn get_hmac<'a>(&self, key: Slice<'a, u8>) -> BoxedHasher {
        Box::new(HmacSha256::new(key.as_slice(), None)).into()
    }

    extern "C" fn get_xpub<'a>(
        &self,
        _address_n: Slice<'a, u32>,
        _xpub_magic: u32,
    ) -> FastResult<[u8; 111], WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn get_public_key<'a>(
        &self,
        _address_n: Slice<'a, u32>,
        _compressed: bool,
    ) -> FastResult<stabby::boxed::BoxedSlice<u8>, WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn sign_typed_hash<'a>(
        &self,
        _address_n: Slice<'a, u32>,
        _hash: [u8; 32],
        _encoded_network: stabby::option::Option<Slice<'a, u8>>,
        _encoded_token: stabby::option::Option<Slice<'a, u8>>,
        _chain_id: stabby::option::Option<u64>,
        _show_progress: bool,
    ) -> FastResult<[u8; 65], WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn sign_digest<'a>(
        &self,
        _address_n: Slice<'a, u32>,
        _digest: [u8; 32],
        _compressed: bool,
    ) -> FastResult<[u8; 65], WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn check_address_mac<'a>(
        &self,
        _address_n: Slice<'a, u32>,
        _mac: [u8; 32],
        _address: Str<'a>,
    ) -> FastResult<bool, WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn get_address_mac<'a>(
        &self,
        _address_n: Slice<'a, u32>,
        _address: Str<'a>,
    ) -> FastResult<[u8; 32], WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn verify_nonce_cache<'a>(
        &self,
        _nonce: Slice<'a, u8>,
    ) -> FastResult<bool, WireError> {
        unimplemented!("not exercised by the current test suite")
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

struct DummyWire;

impl WireV1 for DummyWire {
    extern "C" fn register_inbox<'a>(&self, _buffer: SliceMut<'a, usize>) {}

    extern "C" fn wire_receive_start(&self, _timeout_ms: u32) -> FastResult<WireMessage, WireError> {
        Err(WireError::Timeout).into()
    }

    extern "C" fn wire_request<'a>(
        &self,
        _id: u16,
        _data: Slice<'a, u8>,
        _timeout_ms: u32,
    ) -> FastResult<WireMessage, WireError> {
        Err(WireError::Timeout).into()
    }

    extern "C" fn wire_respond<'a>(
        &self,
        _response_id: u16,
        _data: Slice<'a, u8>,
    ) -> FastResult<(), WireError> {
        Err(WireError::FailedToSend).into()
    }

    extern "C" fn wire_error<'a>(&self, _code: u16, _message: Str<'a>) -> FastResult<(), WireError> {
        Err(WireError::FailedToSend).into()
    }
}

struct DummyUi;

impl UiV1 for DummyUi {
    extern "C" fn confirm_value<'a>(
        &self,
        _value: ConfirmValue<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn confirm_value_intro<'a>(
        &self,
        _value: ConfirmValueIntro<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn confirm_summary<'a>(
        &self,
        _value: ConfirmSummary<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn confirm_action<'a>(
        &self,
        _value: ConfirmAction<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn select_menu<'a>(
        &self,
        _value: SelectMenu<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn confirm_properties<'a>(
        &self,
        _value: ConfirmProperties<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn show_properties<'a>(
        &self,
        _value: ShowProperties<'a>,
    ) -> FastResult<(), WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn show_warning<'a>(&self, _value: ShowWarning<'a>) -> FastResult<(), WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn show_info_with_cancel<'a>(
        &self,
        _value: ShowInfoWithCancel<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn show_mismatch<'a>(
        &self,
        _value: ShowMismatch<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn confirm_trade<'a>(
        &self,
        _value: ConfirmTrade<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn show_danger<'a>(
        &self,
        _value: ShowDanger<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn show_success<'a>(&self, _value: ShowSuccess<'a>) -> FastResult<(), WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn request_number<'a>(
        &self,
        _value: RequestNumber<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn show_public_key<'a>(
        &self,
        _value: ShowPublicKey<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn confirm_with_info<'a>(
        &self,
        _value: ConfirmWithInfo<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn show_address<'a>(
        &self,
        _value: ShowAddress<'a>,
    ) -> FastResult<TrezorUiResult, WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn init_progress<'a>(
        &self,
        _description: stabby::option::Option<stabby::slice::Slice<'a, u8>>,
        _title: stabby::option::Option<stabby::slice::Slice<'a, u8>>,
        _indeterminate: bool,
        _danger: bool,
    ) -> FastResult<(), WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn update_progress<'a>(
        &self,
        _description: stabby::option::Option<stabby::slice::Slice<'a, u8>>,
        _value: u32,
    ) -> FastResult<(), WireError> {
        unimplemented!("not exercised by the current test suite")
    }

    extern "C" fn end_progress(&self) -> FastResult<(), WireError> {
        unimplemented!("not exercised by the current test suite")
    }
}

static DUMMY_API: TrezorApiV1Struct = TrezorApiV1Struct {
    api: stabby::dynref_static!(DummyApi as TrezorApiV1Vtable),
    allocator: stabby::dynref_static!(DummyAllocator as GlobalAllocatorV1Vtable),
    crypto: stabby::dynref_static!(DummyCrypto as CryptoV1Vtable),
    syslog: stabby::dynref_static!(DummySyslog as SyslogV1Vtable),
    wire: stabby::dynref_static!(DummyWire as WireV1Vtable),
    ui: stabby::dynref_static!(DummyUi as UiV1Vtable),
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
            hasher.ctx.update(data);
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
    extern "C" fn update<'a>(&mut self, input: Slice<'a, u8>) {
        self.ctx.update(input.as_slice());
    }

    extern "C" fn finalize(&mut self) -> BoxedSlice<u8> {
        BoxedSlice::from(&self.ctx.clone().finalize()[..])
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
            hasher.ctx.update(data);
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
    extern "C" fn update<'a>(&mut self, input: Slice<'a, u8>) {
        self.ctx.update(input.as_slice());
    }

    extern "C" fn finalize(&mut self) -> BoxedSlice<u8> {
        BoxedSlice::from(&self.digest()[..])
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
            hasher.ctx.update(data);
        }
        hasher
    }

    pub fn digest(&mut self) -> [u8; 32] {
        let mut out = [0u8; 32];
        out.copy_from_slice(self.ctx.clone().finalize_fixed().as_slice());
        out
    }
}

impl Hasher for Keccak256 {
    extern "C" fn update<'a>(&mut self, input: Slice<'a, u8>) {
        self.ctx.update(input.as_slice());
    }

    extern "C" fn finalize(&mut self) -> BoxedSlice<u8> {
        BoxedSlice::from(&self.digest()[..])
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
            hasher.ctx.update(data);
        }
        hasher
    }

    pub fn digest(&mut self) -> [u8; 32] {
        let mut out = [0u8; 32];
        out.copy_from_slice(self.ctx.clone().finalize_fixed().as_slice());
        out
    }
}

impl Hasher for Sha3_256 {
    extern "C" fn update<'a>(&mut self, input: Slice<'a, u8>) {
        self.ctx.update(input.as_slice());
    }

    extern "C" fn finalize(&mut self) -> BoxedSlice<u8> {
        BoxedSlice::from(&self.digest()[..])
    }
}

impl Drop for Sha3_256 {
    fn drop(&mut self) {
        self.ctx.reset();
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
            hasher.ctx.update(data);
        }
        hasher
    }

    pub fn digest(&mut self) -> [u8; 32] {
        let mut out = [0u8; 32];
        out.copy_from_slice(self.ctx.clone().finalize().as_slice());
        out
    }
}

impl Hasher for HmacSha256 {
    extern "C" fn update<'a>(&mut self, input: Slice<'a, u8>) {
        self.ctx.update(input.as_slice());
    }

    extern "C" fn finalize(&mut self) -> BoxedSlice<u8> {
        BoxedSlice::from(&self.digest()[..])
    }
}

impl Drop for HmacSha256 {
    fn drop(&mut self) {
        unsafe {
            core::ptr::write_volatile(&mut self.ctx, core::mem::zeroed());
        }
    }
}
