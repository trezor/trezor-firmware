use anyhow::Result;
use clap::Parser;
use modular_xtask::args::Cli;

fn main() -> Result<()> {
    modular_xtask::run_cmd(&Cli::parse().command, std::path::Path::new("."))
}
