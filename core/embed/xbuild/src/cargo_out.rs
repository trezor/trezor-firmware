//! Buffering of `cargo::` directives written to stdout.
//!
//! Cargo echoes a failed build script's entire stdout back to the user, where
//! the directives bury the actual compiler diagnostics. They are worthless on
//! failure anyway - Cargo discards the run and re-executes the build script
//! next time no matter what it printed - so they are collected while a build
//! is in progress and written out only once it succeeds.
//!
//! [`warning`] is the exception: buffering one would drop it on failure, and
//! Cargo does surface build script warnings then - so it is written as soon as
//! it is produced.

use std::fmt::Display;
use std::io::{self, Write};
use std::path::Path;
use std::sync::Mutex;

/// Pending directives since the first deferred directive after the last flush.
static PENDING: Mutex<Option<Vec<String>>> = Mutex::new(None);

/// Emits `cargo::warning=` - a message Cargo shows to the user.
///
/// Written immediately so it survives a later build failure; see the module
/// documentation.
///
/// A multi-line message becomes one directive per line: Cargo parses its stdout
/// line by line, so an embedded newline would leave everything after it read as
/// junk. Blank lines are dropped rather than rendered as a bare `warning:`.
///
/// All the lines are written under a single lock, so that concurrently
/// compiling sources cannot interleave their diagnostics.
pub fn warning(message: impl Display) {
    let message = message.to_string();

    let stdout = io::stdout();
    let mut lock = stdout.lock();
    for line in message.lines().filter(|line| !line.trim().is_empty()) {
        let _ = writeln!(lock, "cargo::warning={line}");
    }
    let _ = lock.flush();
}

/// Emits `cargo::metadata=` - a `key=value` pair passed to the build scripts
/// of dependent crates as `DEP_<links>_<KEY>`.
pub fn metadata(key: &str, value: impl Display) {
    defer(format!("cargo::metadata={key}={value}"));
}

/// Emits `cargo::rustc-link-lib=`
pub fn rustc_link_lib(lib: impl Display) {
    defer(format!("cargo::rustc-link-lib={lib}"));
}

/// Emits `cargo::rustc-link-arg=`
pub fn rustc_link_arg(arg: impl Display) {
    defer(format!("cargo::rustc-link-arg={arg}"));
}

/// Emits `cargo::rustc-link-search=`
pub fn rustc_link_search(path: impl Display) {
    defer(format!("cargo::rustc-link-search={path}"));
}

/// Emits `cargo::rerun-if-changed=`.
pub fn rerun_if_changed(path: impl AsRef<Path>) {
    defer(format!(
        "cargo::rerun-if-changed={}",
        path.as_ref().display()
    ));
}

/// Emits `cargo::rerun-if-env-changed=`.
pub fn rerun_if_env_changed(var: &str) {
    defer(format!("cargo::rerun-if-env-changed={var}"));
}

/// Holds a directive back until [`flush`] is called.
fn defer(directive: String) {
    PENDING
        .lock()
        .expect("cargo output poisoned")
        .get_or_insert_default()
        .push(directive);
}

/// Writes out everything collected since the first deferred directive after
/// the previous flush.
pub(crate) fn flush() {
    let pending = PENDING.lock().expect("cargo output poisoned").take();

    let Some(pending) = pending else {
        return;
    };

    let stdout = io::stdout();
    let mut lock = stdout.lock();
    for directive in pending {
        let _ = writeln!(lock, "{directive}");
    }
}
