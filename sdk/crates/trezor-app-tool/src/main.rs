use anyhow::Result;
use args::{Cli, Cmd};
use clap::Parser;

mod apptree;
mod args;
mod artifacts;
mod cargo;
mod device_test;
mod fmt;
mod helpers;
mod image;
mod prebuild;

fn main() -> Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Cmd::Build(args) => cargo::build(args),
        Cmd::Clippy(args) => cargo::clippy(args),
        Cmd::Check(args) => cargo::check(args),
        Cmd::Size(args) => cargo::size(args),
        Cmd::Test(args) => cargo::test(args),
        Cmd::DeviceTest(args) => device_test::test(args),
        Cmd::Fmt(args) => fmt::format(args),
        Cmd::Clean => cargo::clean(),
    }?;

    Ok(())
}
