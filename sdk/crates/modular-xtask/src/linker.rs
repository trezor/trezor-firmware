//! The linker script every modular app is linked with, and the code that
//! puts it on disk for `ld` to read.
//!
//! An app's memory layout is fixed by Core's loader, not by the app: every
//! app maps at the same addresses, exports the same entry symbol, and needs
//! the same section/segment layout. There is therefore nothing for an app
//! to configure here, so rather than making each app carry an identical
//! `memory.x` at its root -- copied by hand into every new app, and free to
//! drift once copied -- the script lives in this crate (see
//! [`MEMORY_X`]) and [`memory_x`] writes it into the build directory on
//! every build.

use anyhow::{Context, Result};
use std::{fs, path::PathBuf};

use crate::helpers;

/// The one linker script shared by every modular app, embedded from this
/// crate's own `memory.x` so it stays a real linker script (and the single
/// source of truth for the layout Core's loader expects) rather than a
/// string literal.
const MEMORY_X: &str = include_str!("../memory.x");

/// Writes [`MEMORY_X`] into the calling project's build directory and
/// returns its absolute path, for [`crate::args::BuildArgs::configure_cargo`]
/// to pass to `ld` as `-T`. Rewritten only when its content actually
/// changed, so repeated builds don't keep touching a file the linker reads.
pub fn memory_x() -> Result<PathBuf> {
    let build_dir = helpers::build_dir()?;
    helpers::ensure_directory(&build_dir)?;

    let path = build_dir.join("memory.x");
    if fs::read_to_string(&path).is_ok_and(|current| current == MEMORY_X) {
        return Ok(path);
    }

    fs::write(&path, MEMORY_X)
        .with_context(|| format!("Failed to write linker script {}", path.display()))?;

    Ok(path)
}
