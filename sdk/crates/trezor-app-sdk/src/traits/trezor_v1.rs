use stabby::str::Str;

use super::allocator::GlobalAllocatorV1Ref;
use super::crypto::CryptoV1Ref;
use super::syslog::SyslogV1Ref;

#[stabby::stabby(checked)]
pub trait TrezorApiV1: Send + Sync {
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
}
