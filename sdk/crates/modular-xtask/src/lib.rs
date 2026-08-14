//! # modular-xtask
//!
//! Build/test driver for Trezor modular apps ("extapps") -- the `cargo xtask`
//! convention applied to `xtask modular <cmd>`. It wraps `cargo build`/`test`/
//! `clippy` with the right feature flags and profile for a given model and
//! language, packages the resulting ELF into the app binary format Core
//! loads (see [`binary`] / [`armv8m`]), and drives the auxiliary steps apps
//! need: Merkle proof and RootPacket generation ([`postbuild`]), device
//! tests ([`device_tests`]), and Python/translation style checks
//! ([`pystyle`] / [`translations`]).
//!
//! It's used both in-tree, as the build tool for the `sdk/apps` workspace in
//! this repository, and out-of-tree, as a path dependency from a standalone
//! app repository (see `sdk/doc/development.md`). [`run_cmd`] is the single
//! entry point both `core/embed/xtask`'s `modular` subcommand and a
//! standalone app's own `xtask` binary call into.

#![deny(missing_docs)]

pub mod args;
pub mod armv8m;
pub mod binary;
pub mod cargo;
pub mod device_tests;
pub mod helpers;
pub mod metadata;
pub mod postbuild;
pub mod pystyle;
mod tools;
pub mod translations;
pub mod upload;

use crate::args::Cmd;

/// Runs a parsed [`Cmd`] with the current directory temporarily switched to
/// `workspace_root` (the app's or app workspace's own root, not necessarily
/// the process's cwd), restoring the original directory afterwards -- even
/// if the command itself returns an error.
pub fn run_cmd(cmd: &args::Cmd, workspace_root: &std::path::Path) -> anyhow::Result<()> {
    let prev_dir = std::env::current_dir()?;

    std::env::set_current_dir(workspace_root)?;

    let result = match cmd {
        Cmd::Build(args) => cargo::build(args),
        Cmd::Clippy(args) => cargo::clippy(args),
        Cmd::Check(args) => cargo::check(args),
        Cmd::Size(args) => cargo::size(args),
        Cmd::UnitTests(args) => cargo::test(args),
        Cmd::Clean => cargo::clean(),
        Cmd::Fmt => cargo::fmt(false),
        Cmd::FmtCheck => cargo::fmt(true),
        Cmd::Upload(args) => {
            _ = upload::upload(args)?;
            Ok(())
        }
        Cmd::DeviceTests(args) => device_tests::device_tests(args),
        Cmd::PyStyle(args) => pystyle::run(args, false),
        Cmd::PyStyleCheck(args) => pystyle::run(args, true),
        Cmd::TranslationStyle(args) => translations::run(args, false),
        Cmd::TranslationStyleCheck(args) => translations::run(args, true),
    };

    std::env::set_current_dir(prev_dir)?;
    result
}
