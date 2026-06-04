use anyhow::Result;
use clap::Parser;
use modular_xtask::run_cmd;

use xtask::{
    args::{Cli, Cmd},
    cargo, combine, flash, upload,
};

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
        Cmd::FlashErase(args) => flash::flash_erase(args),
        Cmd::Upload(args) => upload::upload(args),
        Cmd::Combine(args) => combine::combine(args),
        Cmd::Modular(args) => run_cmd(&args.command, std::path::Path::new("../../sdk/apps/")),
    }
}
