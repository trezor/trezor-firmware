use crate::traits::ApiVariant as ApiVersion;
use crate::traits::crypto::StaticCryptoV1;
use crate::traits::syslog::StaticSyslogV1;
use crate::traits::trezor_v1::{TrezorApiV1Dyn as _, TrezorApiV1Struct};

pub mod allocator;

static API: spin::Once<&'static TrezorApiV1Struct> = spin::Once::new();

const API_VERSION: u32 = 1;

#[unsafe(no_mangle)]
pub unsafe extern "C" fn applet_main(api_get: crate::traits::ApiGetter) -> core::ffi::c_int {
    match api_get(API_VERSION) {
        ApiVersion::V1(api) => {
            API.call_once(|| api);
        }
    }
    0
}

fn get_api_or_die() -> &'static TrezorApiV1Struct {
    API.get().expect("API not initialized")
}

pub(crate) fn systick_ms() -> u32 {
    get_api_or_die().api.systick_ms()
}

pub(crate) fn sleep(timeout_ms: u32) {
    get_api_or_die().api.sleep(timeout_ms);
}

pub(crate) fn try_get_syslog() -> Option<StaticSyslogV1> {
    API.get().map(|api| api.syslog)
}

pub(crate) fn get_crypto_or_die() -> StaticCryptoV1 {
    get_api_or_die().crypto
}
