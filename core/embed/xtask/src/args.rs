use anyhow::Result;
use clap::{Args, Parser, Subcommand, ValueEnum};

#[derive(ValueEnum, Debug, Clone, Copy, PartialEq, Eq)]
pub enum Model {
    #[value(name = "d001")]
    D001,
    #[value(name = "d002")]
    D002,
    #[value(name = "t2t1")]
    T2T1,
    #[value(name = "t2b1")]
    T2B1,
    #[value(name = "t3b1")]
    T3B1,
    #[value(name = "t3t1")]
    T3T1,
    #[value(name = "t3w1")]
    T3W1,
}

impl Model {
    pub fn feature_name(self) -> &'static str {
        match self {
            Model::D001 => "model_d001",
            Model::D002 => "model_d002",
            Model::T2T1 => "model_t2t1",
            Model::T2B1 => "model_t2b1",
            Model::T3B1 => "model_t3b1",
            Model::T3T1 => "model_t3t1",
            Model::T3W1 => "model_t3w1",
        }
    }

    pub fn target_triple(self) -> &'static str {
        match self {
            Model::D001 | Model::T2T1 | Model::T2B1 => "thumbv7em-none-eabihf",
            Model::D002 | Model::T3B1 | Model::T3T1 | Model::T3W1 => "thumbv8m.main-none-eabihf",
        }
    }
}

#[derive(ValueEnum, Debug, Clone, Copy, PartialEq, Eq)]
pub enum Component {
    Bootloader,
    Boardloader,
    #[value(name = "bootloader_ci")]
    BootloaderCi,
    Firmware,
    Prodtest,
    Kernel,
    Secmon,
}

impl Component {
    pub fn package_name(self, emulator: bool) -> &'static str {
        match self {
            Component::Bootloader => "bootloader",
            Component::Boardloader => "boardloader",
            Component::BootloaderCi => "bootloader_ci",
            Component::Firmware => emulator.then_some("unix").unwrap_or("firmware"),
            Component::Prodtest => "prodtest",
            Component::Kernel => "kernel",
            Component::Secmon => "secmon",
        }
    }

    pub fn frozen_default(self, emulator: bool) -> bool {
        match self {
            Component::Firmware => !emulator,
            _ => false,
        }
    }

    pub fn btc_only_default(self) -> bool {
        match self {
            Component::Firmware | Component::Kernel | Component::Secmon => false,
            _ => true,
        }
    }
}

#[derive(ValueEnum, Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConsoleType {
    Vcp,
    Swo,
    SystemView,
}

#[derive(Parser, Debug)]
#[command(name = "xtask")]
#[command(about = "Trezor workspace automation tasks")]
pub struct Cli {
    #[command(subcommand)]
    pub command: Cmd,
}

#[derive(Subcommand, Debug)]
pub enum Cmd {
    /// Build a component with the specified configuration
    Build(BuildArgs),
    /// Run clippy linter on a component with the specified configuration
    Clippy(BuildArgs),
    /// Run cargo check on a component with the specified configuration
    Check(BuildArgs),
    /// Clean build artifacts
    Clean,
    /// Format code with rustfmt
    Fmt,
}

#[derive(Args, Debug, Copy, Clone)]
#[command(override_usage = "xtask build <COMPONENT> --model <MODEL> [OPTIONS]")]
pub struct BuildArgs {
    pub component: Component,

    /// Target model to build
    #[arg(long, short = 'm', ignore_case = true)]
    pub model: Model,

    /// Build for the emulator instead of hardware
    #[arg(long, short = 'e')]
    pub emulator: bool,

    /// Enable debug mode
    #[arg(long, short = 'd', num_args = 0..=1, default_missing_value = "true")]
    pub debug: Option<bool>,

    /// Debug console type
    #[arg(long)]
    pub dbg_console: Option<ConsoleType>,

    /// Build Bitcoin-only version
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub btc_only: Option<bool>,

    /// Enable production features
    #[arg(long)]
    pub production: bool,

    /// Embed QA bootloader instead of production
    #[arg(long)]
    pub bootloader_qa: bool,

    /// Build firmware for development bootloader
    #[arg(long)]
    pub bootloader_devel: bool,

    /// Embed frozen MicroPython modules
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub frozen: Option<bool>,

    /// Include MicroPython source lines for debugging
    #[arg(long)]
    pub source_lines: Option<bool>,

    /// Optimize micropython bytecode for speed
    #[arg(long)]
    pub pyopt: Option<bool>,

    /// Enable debug link interface
    #[arg(long)]
    pub debug_link: Option<bool>,

    /// Disable UI animations
    #[arg(long)]
    pub disable_animation: bool,

    /// Show performance overlay in UI
    #[arg(long)]
    pub perf_overlay: bool,

    /// Include cryptographic benchmarks in the build
    #[arg(long)]
    pub benchmark: bool,

    /// Log stack usage
    #[arg(long)]
    pub log_stack_usage: bool,

    /// Use blocking write on VCP console
    #[arg(long)]
    pub block_on_vcp: bool,

    /// Output cargo build timings
    #[arg(long)]
    pub timings: bool,

    /// Enable verbose output
    #[arg(long)]
    pub verbose: bool,
}

impl BuildArgs {
    pub fn resolve_features(&self) -> Vec<&'static str> {
        let mut features = vec![self.model.feature_name()];

        if self.emulator {
            features.push("emulator");
        }

        if !self.btc_only.unwrap_or(self.component.btc_only_default()) {
            features.push("universal_fw");
        }

        if self.production {
            features.push("production");
        }

        if self.bootloader_devel {
            features.push("bootloader_devel");
        }

        if self.bootloader_qa {
            features.push("bootloader_qa");
        }

        if self.emulator {
            features.push("dbg_console");
        } else {
            match (self.component, self.dbg_console) {
                (Component::Firmware, Some(_)) => features.push("dbg_console"),
                (Component::Secmon, Some(ConsoleType::Vcp)) => (),
                (Component::Boardloader, Some(ConsoleType::Vcp)) => (),
                (Component::Prodtest, Some(ConsoleType::Vcp)) => (),
                (_, Some(ConsoleType::Vcp)) => features.push("dbg_console_vcp"),
                (_, Some(ConsoleType::Swo)) => features.push("dbg_console_swo"),
                (_, Some(ConsoleType::SystemView)) => features.push("dbg_console_sysview"),
                (_, None) => (),
            }
        }

        let pyopt = self.pyopt.unwrap_or(!self.emulator);

        if self.component == Component::Firmware {
            if pyopt {
                features.push("pyopt");
            } else {
                features.push("debug");
            }

            if self.source_lines.unwrap_or(self.emulator) {
                features.push("micropy_enable_source_line");
            }

            if self.benchmark {
                features.push("benchmark");
            }

            if self.log_stack_usage {
                features.push("log_stack_usage");
            }

            if self.block_on_vcp {
                features.push("block_on_vcp");
            }
        }

        if self.component == Component::Secmon
            || self.component == Component::Kernel
            || self.component == Component::Firmware
        {
            if !pyopt {
                features.push("optiga_testing");
            }
        }

        if self.component == Component::Firmware
            || self.component == Component::Bootloader
            || self.component == Component::Prodtest
        {
            if self.perf_overlay {
                features.push("ui_performance_overlay");
            }

            if self.debug_link.unwrap_or(self.emulator) {
                features.push("debuglink");
                features.push("ui_debug");
            }

            if self.disable_animation {
                features.push("disable_animation");
            }
        }

        // By default, we want to build with `frozen` for hardware targets
        if self
            .frozen
            .unwrap_or(self.component.frozen_default(self.emulator))
        {
            features.push("frozen");
        }

        features
    }

    // Configures the cargo command with the appropriate arguments and features
    // based on the provided cli arguments
    pub fn configure_cargo(&self, cmd: &mut std::process::Command) -> Result<()> {
        let features = self.resolve_features();

        cmd.args(["--package", self.component.package_name(self.emulator)]);
        cmd.args(["--features", &features.join(",")]);

        if !self.emulator {
            cmd.arg("-Zbuild-std=core");
            cmd.arg("-Zbuild-std-features=panic_immediate_abort");
            cmd.args(["--target", self.model.target_triple()]);
        }

        // 1. see https://nnethercote.github.io/perf-book/type-sizes.html#measuring-type-sizes for more details
        // 2. Adds an ELF section with Rust functions' stack sizes. See the following links for more details:
        // - https://doc.rust-lang.org/nightly/unstable-book/compiler-flags/emit-stack-sizes.html
        // - https://blog.japaric.io/stack-analysis/
        // - https://github.com/japaric/stack-sizes/
        // !@# cmd.env("RUSTFLAGS", "-Z print-type-sizes -Z emit-stack-sizes");

        // We have different default for `--debug` for hardware and emulator builds
        if !self.debug.unwrap_or(self.emulator) {
            cmd.arg("--release");
        }

        if self.timings {
            cmd.arg("--timings");
        }

        if self.verbose {
            cmd.arg("--verbose");
        }

        Ok(())
    }
}
