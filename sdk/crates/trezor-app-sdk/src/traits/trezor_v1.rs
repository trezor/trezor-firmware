use stabby::str::Str;

use super::allocator::GlobalAllocatorV1Ref;
use super::crypto::CryptoV1Ref;
use super::syslog::SyslogV1Ref;
use super::ui::UiV1Ref;
use super::wire::WireV1Ref;

#[stabby::stabby(checked)]
pub trait TrezorApiV1: Send + Sync {
    /// Allocates and registers this app's `WireV1` inbox buffer,
    /// `inbox_words` [`usize`] words long. Must be called exactly once,
    /// before any other API call that talks to Core over the wire.
    ///
    /// The heap this allocates from is already live by the time an app can
    /// call in: Core claims the app's heap region for its allocator in
    /// `coreapp_app_entry`, the entry point it runs on the app's task
    /// *before* calling [`applet_main`].
    ///
    /// [`applet_main`]: crate::app_runtime2::applet_main
    extern "C" fn init(&self, inbox_words: usize);

    extern "C" fn system_exit(&self) -> !;
    extern "C" fn system_exit_error<'a>(
        &self,
        title: Str<'a>,
        message: Str<'a>,
        footer: Str<'a>,
    ) -> !;
    extern "C" fn system_exit_fatal<'a>(&self, message: Str<'a>, file: Str<'a>, line: u32) -> !;

    extern "C" fn systick_ms(&self) -> u32;
    extern "C" fn sleep(&self, timeout_ms: u32);
}

pub type TrezorApiV1Vtable = stabby::vtable!(TrezorApiV1 + Send + Sync);
pub type TrezorApiV1Ref<'a> = stabby::DynRef<'a, TrezorApiV1Vtable>;

#[stabby::stabby]
pub struct TrezorApiV1Struct {
    pub api: TrezorApiV1Ref<'static>,
    pub allocator: GlobalAllocatorV1Ref<'static>,
    pub crypto: CryptoV1Ref<'static>,
    pub syslog: SyslogV1Ref<'static>,
    pub wire: WireV1Ref<'static>,
    pub ui: UiV1Ref<'static>,
}
