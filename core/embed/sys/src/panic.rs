/// Panic handler shared by all binaries that link `sys`.
///
/// Only debug builds ever reach it - the release profile uses
/// `panic = "immediate-abort"`, which compiles every panic to an abort
/// instruction without referencing the handler, so it gets stripped there.
#[panic_handler]
fn panic(panic_info: &core::panic::PanicInfo) -> ! {
    // Filling at least the file and line information, if available.
    let msg = panic_info.message().as_str().unwrap_or("rs");
    if let Some(location) = panic_info.location() {
        rtl::system_exit_fatal(msg, location.file(), location.line());
    } else {
        rtl::system_exit_fatal(msg, "", 0);
    }
}
