use anyhow::Result;
use clap::Parser;

use xtask::{
    args::{Cli, Cmd},
    cargo, device_tests, upload,
};

fn main() -> Result<()> {
    let cli = Cli::parse();

    match cli.command {
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
    }
}
