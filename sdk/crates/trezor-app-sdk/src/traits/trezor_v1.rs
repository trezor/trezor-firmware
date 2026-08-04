use stabby::str::Str;

use super::allocator::GlobalAllocatorV1Ref;
use super::crypto::CryptoV1Ref;
use super::syslog::SyslogV1Ref;
use super::ui::UiV1Ref;
use super::wire::WireV1Ref;

#[stabby::stabby(checked)]
/// System functions of the API: exiting and timing.
pub trait TrezorApiV1: Send + Sync {
    /// Ends the app normally.
    extern "C" fn system_exit(&self) -> !;

    /// Ends the app with an error, reported to the host as an app failure.
    extern "C" fn system_exit_error<'a>(
        &self,
        title: Str<'a>,
        message: Str<'a>,
        footer: Str<'a>,
    ) -> !;

    /// Ends the app on a fatal error at `file`:`line`, e.g. a panic.
    extern "C" fn system_exit_fatal<'a>(&self, message: Str<'a>, file: Str<'a>, line: u32) -> !;

    /// Milliseconds since the device started.
    extern "C" fn systick_ms(&self) -> u32;

    /// Sleeps for `timeout_ms` milliseconds.
    extern "C" fn sleep(&self, timeout_ms: u32);
}

/// The stabby vtable of [`TrezorApiV1`].
pub type TrezorApiV1Vtable = stabby::vtable!(TrezorApiV1 + Send + Sync);
/// A borrowed `dyn TrezorApiV1`.
pub type TrezorApiV1Ref<'a> = stabby::DynRef<'a, TrezorApiV1Vtable>;

/// Version 1 of the API Core hands to an app: one interface per area.
#[stabby::stabby]
pub struct TrezorApiV1Struct {
    /// System functions.
    pub api: TrezorApiV1Ref<'static>,
    /// Heap allocation.
    pub allocator: GlobalAllocatorV1Ref<'static>,
    /// Cryptography.
    pub crypto: CryptoV1Ref<'static>,
    /// Logging.
    pub syslog: SyslogV1Ref<'static>,
    /// Messaging with the host.
    pub wire: WireV1Ref<'static>,
    /// User interface.
    pub ui: UiV1Ref<'static>,
}
