use anyhow::Result;
use clap::{Args, Parser, Subcommand, ValueEnum};

use std::process;

#[derive(ValueEnum, Debug, Clone, Copy, PartialEq, Eq)]
pub enum Model {
    #[value(name = "t3t1")]
    T3T1,
    #[value(name = "t3w1")]
    T3W1,
}

#[derive(ValueEnum, Debug, Clone, Copy, PartialEq, Eq)]
pub enum Language {
    #[value(name = "en")]
    EN,
    #[value(name = "cs")]
    CS,
}

#[derive(ValueEnum, Debug, Clone, Copy, PartialEq, Eq)]
pub enum LogLevel {
    #[value(name = "error")]
    Error,
    #[value(name = "warn")]
    Warn,
    #[value(name = "info")]
    Info,
    #[value(name = "debug")]
    Debug,
    #[value(name = "trace")]
    Trace,
}

impl Model {
    /// Returns feature name corresponding to the model
    pub fn feature_name(self) -> &'static str {
        match self {
            Model::T3T1 => "model_t3t1",
            Model::T3W1 => "model_t3w1",
        }
    }

    /// Returns the Rust target triple for the building firmware for hardware target
    pub fn target_triple(self) -> &'static str {
        match self {
            Model::T3T1 | Model::T3W1 => "thumbv7em-none-eabihf",
        }
    }

    /// Returns the model ID used in artifact naming
    pub fn model_id(self) -> &'static str {
        match self {
            Model::T3T1 => "t3t1",
            Model::T3W1 => "t3w1",
        }
    }
}

impl Language {
    /// Returns feature name corresponding to the language
    pub fn feature_name(self) -> &'static str {
        match self {
            Language::EN => "lang_en",
            Language::CS => "lang_cs",
        }
    }
}

impl LogLevel {
    pub fn feature_name(self) -> &'static str {
        match self {
            LogLevel::Error => "log_level_error",
            LogLevel::Warn => "log_level_warn",
            LogLevel::Info => "log_level_info",
            LogLevel::Debug => "log_level_debug",
            LogLevel::Trace => "log_level_trace",
        }
    }
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
    /// Run clippy command with the specified configuration
    Clippy(BuildArgs),
    /// Run check command with the specified configuration
    Check(BuildArgs),
    /// Display size information of the built binary
    Size(BuildArgs),
    /// Run unit tests of specified package
    UnitTests(UnitTestArgs),
    /// Run device tests of specified package
    DeviceTests(UploadArgs),
    /// Clean build artifacts
    Clean,
    /// Format code with rustfmt
    Fmt,
    /// Upload firmware to device
    Upload(UploadArgs),
}

#[derive(Args, Debug, Clone)]
#[command(
    override_usage = "xtask build --model <MODEL> --language <LANGUAGE> --log_level <LOG_LEVEL> [OPTIONS]"
)]
pub struct BuildArgs {
    #[arg(default_value = "funnycoin_rust")]
    pub app: String,

    /// Build target model
    #[arg(long, short = 'm', ignore_case = true, default_value = "t3w1")]
    pub model: Model,

    /// Build target language
    #[arg(long, short = 'l', ignore_case = true, default_value = "en")]
    pub lang: Language,

    /// Log level for the built firmware
    #[arg(long, ignore_case = true, default_value = "info")]
    pub log_level: LogLevel,

    /// Use emulator build
    #[arg(long, short = 'e')]
    pub emulator: bool,

    #[arg(long, short = 'd', default_value = "false")]
    pub debug: bool,

    /// Enable production build
    #[arg(long, default_value = "false")]
    pub production: bool,

    /// Enable verbose output
    #[arg(long)]
    pub verbose: bool,
}

impl BuildArgs {
    /// Resolves the list of cargo features to enable based on the provided cli arguments
    pub fn resolve_features(&self) -> Result<Vec<&'static str>> {
        let mut features = vec![
            self.model.feature_name(),
            self.lang.feature_name(),
            self.log_level.feature_name(),
        ];

        if self.emulator {
            features.push("emulator");
        }

        if self.debug {
            features.push("debug");
        }

        if !self.production {
            features.push("dev_keys");
        }

        Ok(features)
    }

    // Configures the cargo command with the appropriate arguments and features
    // based on the provided cli arguments
    pub fn configure_cargo(&self, cmd: &mut process::Command) -> Result<()> {
        let features = self.resolve_features()?;

        cmd.args(["--features", &features.join(",")]);

        if !self.debug {
            cmd.arg("--release");
            cmd.arg("-Zbuild-std=core,alloc");
        }

        if !self.emulator {
            cmd.args(["--target", self.model.target_triple()]);
        } else {
        }

        if self.verbose {
            cmd.arg("--verbose");
        }

        Ok(())
    }
}

#[derive(Args, Debug)]
// #[command(override_usage = "xtask build --model <MODEL> --language <LANGUAGE> [OPTIONS]")]
pub struct UnitTestArgs {
    /// Build target model
    #[arg(long, short = 'm', ignore_case = true, default_value = "t3w1")]
    pub model: Model,

    /// Build target language
    #[arg(long, short = 'l', ignore_case = true, default_value = "en")]
    pub lang: Language,

    /// Test to run (defaults to all tests in the package)
    #[arg(long, short = 'p', default_value = "")]
    pub test: String,
}

#[derive(Args, Debug)]
#[command(override_usage = "xtask upload --model <MODEL> [OPTIONS]")]
pub struct UploadArgs {
    #[arg(default_value = "funnycoin_rust")]
    pub app: String,

    #[arg(long, short = 'm', ignore_case = true)]
    pub model: Model,

    #[arg(long, short = 'e')]
    pub emulator: bool,
}
