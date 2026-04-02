use anyhow::Result;
use clap::Parser;

mod args;
mod artifacts;
mod cargo;
mod flash;
mod helpers;
mod postbuild;
mod upload;

use args::{Cli, Cmd};

fn main() -> Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Cmd::Build(args) => cargo::build(args),
        Cmd::Clippy(args) => cargo::clippy(args),
        Cmd::Check(args) => cargo::check(args),
        Cmd::Test(args) => cargo::test(args),
        Cmd::Clean => cargo::clean(),
        Cmd::Fmt => cargo::fmt(),
        Cmd::Flash(args) => flash::flash(args),
        Cmd::Upload(args) => upload::upload(args),
    }
}
