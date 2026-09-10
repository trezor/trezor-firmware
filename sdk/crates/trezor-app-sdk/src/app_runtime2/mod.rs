use stabby::str::Str;

use crate::debug;
use crate::traits::ApiVariant as ApiVersion;
use crate::traits::crypto::StaticCryptoV1;
use crate::traits::syslog::StaticSyslogV1;
use crate::traits::trezor_v1::{TrezorApiV1Dyn as _, TrezorApiV1Struct};
use crate::traits::ui::StaticUiV1;
use crate::traits::wire::StaticWireV1;

pub mod allocator;

static API: spin::Once<&'static TrezorApiV1Struct> = spin::Once::new();

const API_VERSION: u32 = 1;

#[cfg(not(feature = "test"))]
unsafe extern "Rust" {
    unsafe fn app() -> crate::error::Result<()>;
}

/// Words for this app's own IPC inbox buffer, registered with Core once at
/// startup (see [`register_inbox`]). 8192 `usize` words is 64 KiB on a
/// 32-bit target, matching the kernel's `IPC_MAX_BUFFER_SIZE`.
const INBOX_WORDS: usize = 8192;

/// Allocates this app's IPC inbox buffer out of its own heap and hands it to
/// Core. Core never allocates memory of its own for IPC — it only ever
/// borrows a buffer the app itself allocated, matching the per-app-heap
/// model apps already get everything else (`AllocatorProxy`) through.
fn register_inbox(api: &TrezorApiV1Struct) {
    use stabby::slice::SliceMut;

    use crate::traits::wire::WireV1Dyn as _;

    let buffer: &'static mut [usize] =
        alloc::boxed::Box::leak(alloc::vec![0usize; INBOX_WORDS].into_boxed_slice());
    api.wire.register_inbox(SliceMut::from(buffer));
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn applet_main(api_get: crate::traits::ApiGetter) -> core::ffi::c_int {
    match api_get(API_VERSION) {
        ApiVersion::V1(api) => {
            API.call_once(|| api);
        }
    }

    debug!(
        "Applet main entry point called, API version: {}",
        API_VERSION
    );

    #[cfg(not(feature = "test"))]
    {
        // `init` must run before anything that might allocate (including
        // `register_inbox`, right below): it's what gives this app's own
        // heap region to `AllocatorProxy` in the first place.
        get_api_or_die().api.init();
        register_inbox(get_api_or_die());

        match unsafe { app() } {
            Ok(()) => system_exit(),
            Err(e) => {
                let mut error_buf = [0u8; 256];
                let mut writer = crate::util::SliceWriter::new(&mut error_buf);
                _ = ufmt::uwrite!(writer, "{}", e);
                crate::error!("{}", writer.as_ref());
                system_exit_error("Error", writer.as_ref(), "");
            }
        }
    }

    #[cfg(feature = "test")]
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

/// Local, no-IPC crypto vtable (hashing, `ec_verify_recover`, `base58*`) —
/// see [`crate::traits::crypto::CryptoV1`]. Public: apps call this directly
/// (see e.g. `trezor_app_sdk::hasher`), not just SDK-internal code.
pub fn get_crypto_or_die() -> StaticCryptoV1 {
    get_api_or_die().crypto
}

pub(crate) fn get_wire_or_die() -> StaticWireV1 {
    get_api_or_die().wire
}

/// UI/progress vtable — see [`crate::traits::ui::UiV1`]. Public: apps call
/// this directly to show screens.
pub fn get_ui_or_die() -> StaticUiV1 {
    get_api_or_die().ui
}

/// Terminates the app normally.
pub(crate) fn system_exit() -> ! {
    get_api_or_die().api.system_exit()
}

/// Terminates the app, showing an error screen with `title`/`message`/`footer`.
pub(crate) fn system_exit_error(title: &str, message: &str, footer: &str) -> ! {
    get_api_or_die()
        .api
        .system_exit_error(Str::from(title), Str::from(message), Str::from(footer))
}

/// Terminates the app after an unrecoverable (e.g. panic) failure.
pub(crate) fn system_exit_fatal(message: &str, file: &str, line: u32) -> ! {
    get_api_or_die()
        .api
        .system_exit_fatal(Str::from(message), Str::from(file), line)
}

#[cfg(all(feature = "debug", not(feature = "test"), feature = "nightly"))]
#[lang = "eh_personality"]
fn eh_personality() -> ! {
    loop {}
}

#[cfg(all(feature = "debug", not(feature = "test"), feature = "nightly"))]
#[unsafe(no_mangle)]
unsafe extern "C" fn _Unwind_Resume() {
    unsafe { core::intrinsics::unreachable() };
}

#[cfg(all(feature = "debug", not(feature = "test")))]
#[panic_handler]
fn panic_handler(info: &core::panic::PanicInfo<'_>) -> ! {
    let msg = info.message().as_str().unwrap_or("PANIC");
    let (file, line) = info
        .location()
        .map(|loc| {
            let file = loc.file();
            let file_short = file.rsplit('/').next().unwrap_or(file);
            (file_short, loc.line())
        })
        .unwrap_or(("<unknown>", 0));
    system_exit_fatal(msg, file, line);
}
