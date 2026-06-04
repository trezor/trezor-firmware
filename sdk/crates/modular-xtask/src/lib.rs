pub mod args;
pub mod arm;
pub mod cargo;
pub mod device_tests;
pub mod helpers;
pub mod postbuild;
pub mod pystyle;
mod tools;
pub mod upload;

use crate::args::Cmd;

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
        Cmd::Fmt => cargo::fmt(),
        Cmd::Upload(args) => {
            _ = upload::upload(args)?;
            Ok(())
        }
        Cmd::DeviceTests(args) => device_tests::device_tests(args),
        Cmd::PyStyle(args) => pystyle::run(args, false),
        Cmd::PyStyleCheck(args) => pystyle::run(args, true),
    };

    std::env::set_current_dir(prev_dir)?;
    result
}
