use stabby::str::Str;
use trezor_app_sdk::traits::allocator::GlobalAllocatorV1Vtable;
use trezor_app_sdk::traits::crypto::CryptoV1Vtable;
use trezor_app_sdk::traits::syslog::SyslogV1Vtable;
use trezor_app_sdk::traits::trezor_v1::TrezorApiV1Vtable;
use trezor_app_sdk::traits::{TrezorApiV1, TrezorApiV1Struct};

use crate::allocator::AllocatorProxy;
use crate::crypto::TrezorCryptoV1Impl;
use crate::syslog::TrezorSyslogV1Impl;

pub static TREZOR_API_V1: TrezorApiV1Struct = TrezorApiV1Struct {
    api: stabby::dynref_static!(TrezorApiV1Impl as TrezorApiV1Vtable),
    allocator: stabby::dynref_static!(AllocatorProxy as GlobalAllocatorV1Vtable),
    crypto: stabby::dynref_static!(TrezorCryptoV1Impl as CryptoV1Vtable),
    syslog: stabby::dynref_static!(TrezorSyslogV1Impl as SyslogV1Vtable),
};

struct TrezorApiV1Impl;

impl TrezorApiV1 for TrezorApiV1Impl {
    extern "C" fn system_exit(&self) -> ! {
        rtl::sysexit::system_exit()
    }

    extern "C" fn system_exit_error<'a>(
        &self,
        title: Str<'a>,
        message: Str<'a>,
        footer: Str<'a>,
    ) -> ! {
        rtl::sysexit::system_exit_error(
            Some(title.as_str()),
            message.as_str(),
            Some(footer.as_str()),
        )
    }

    extern "C" fn system_exit_fatal<'a>(&self, message: Str<'a>, file: Str<'a>, line: u32) -> ! {
        rtl::sysexit::system_exit_fatal(message.as_str(), file.as_str(), line)
    }

    extern "C" fn systick_ms(&self) -> u32 {
        sys::time::ticks_ms()
    }

    extern "C" fn sleep(&self, timeout_ms: u32) {
        todo!()
    }
}
