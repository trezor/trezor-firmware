//! CLI argument types for `xtask modular <cmd>`, parsed with `clap`.

use anyhow::Result;
use cargo_metadata::Package;
use clap::{Args, Parser, Subcommand, ValueEnum};

use std::process;

use crate::prebuild;

/// A Trezor hardware model a modular app can be built for.
#[derive(ValueEnum, Debug, Clone, Copy, PartialEq, Eq)]
pub enum Model {
    /// Trezor Safe 5.
    #[value(name = "t3t1")]
    T3T1,
    /// Trezor Safe 7.
    #[value(name = "t3w1")]
    T3W1,
}

/// A language a modular app's UI can be built for.
#[derive(ValueEnum, Debug, Clone, Copy, PartialEq, Eq)]
pub enum Language {
    /// English.
    #[value(name = "en")]
    EN,
    /// Czech.
    #[value(name = "cs")]
    CS,
}

/// A CPU architecture a modular app can be built for. The emulator
/// architectures are host-only, so they are skipped on the command line
/// and resolved by [`crate::helpers::emulator_target_arch`] instead.
#[derive(ValueEnum, Debug, Clone, Copy, PartialEq, Eq)]
pub enum TargetArch {
    /// ARMv8-M (physical device).
    #[value(name = "armv8m")]
    Armv8m,
    /// Linux emulator on x86_64.
    #[value(skip)]
    LinuxX86_64,
    /// macOS emulator on Apple silicon.
    #[value(skip)]
    MacosAarch64,
}

impl TargetArch {
    /// Returns the architecture name used in artifact naming.
    pub fn name(self) -> &'static str {
        match self {
            TargetArch::Armv8m => "armv8m",
            TargetArch::LinuxX86_64 => "linux-x86_64",
            TargetArch::MacosAarch64 => "macos-aarch64",
        }
    }

    /// Returns true for host (emulator) architectures.
    pub fn is_emulator(self) -> bool {
        match self {
            TargetArch::Armv8m => false,
            TargetArch::LinuxX86_64 | TargetArch::MacosAarch64 => true,
        }
    }
}

/// Verbosity of an app's runtime logging, baked in at build time via a
/// cargo feature (see [`LogLevel::feature_name`]).
#[derive(ValueEnum, Debug, Clone, Copy, PartialEq, Eq)]
pub enum LogLevel {
    /// Only errors.
    #[value(name = "error")]
    Error,
    /// Errors and warnings.
    #[value(name = "warn")]
    Warn,
    /// Errors, warnings, and informational messages.
    #[value(name = "info")]
    Info,
    /// Everything, including debug messages.
    #[value(name = "debug")]
    Debug,
}

impl Model {
    /// Returns the cargo feature name corresponding to the model.
    ///
    /// ```
    /// use modular_app-tool::args::Model;
    ///
    /// assert_eq!(Model::T3T1.feature_name(), "model_t3t1");
    /// assert_eq!(Model::T3W1.feature_name(), "model_t3w1");
    /// ```
    pub fn feature_name(self) -> &'static str {
        match self {
            Model::T3T1 => "model_t3t1",
            Model::T3W1 => "model_t3w1",
        }
    }

    /// Returns the Rust target triple used when building firmware (i.e.
    /// non-emulator) for the model.
    pub fn target_triple(self) -> &'static str {
        match self {
            Model::T3T1 | Model::T3W1 => "thumbv8m.main-none-eabihf",
        }
    }

    /// Returns the CPU architecture of the model's firmware (i.e.
    /// non-emulator) build.
    pub fn target_arch(self) -> TargetArch {
        match self {
            Model::T3T1 | Model::T3W1 => TargetArch::Armv8m,
        }
    }

    /// Returns the model ID used in artifact/directory naming.
    ///
    /// ```
    /// use modular_app-tool::args::Model;
    ///
    /// assert_eq!(Model::T3W1.model_id(), "t3w1");
    /// ```
    pub fn model_id(self) -> &'static str {
        match self {
            Model::T3T1 => "T3T1",
            Model::T3W1 => "T3W1",
        }
    }

    /// Returns the 4-byte ASCII representation of the model ID.
    ///
    /// ```
    /// use modular_app-tool::args::Model;
    ///
    /// assert_eq!(Model::T3W1.model_id_bytes(), *b"T3W1");
    /// ```
    pub fn model_id_bytes(self) -> [u8; 4] {
        self.model_id().as_bytes().try_into().unwrap()
    }
}

impl Language {
    /// Returns the cargo feature name corresponding to the language.
    ///
    /// ```
    /// use modular_app-tool::args::Language;
    ///
    /// assert_eq!(Language::EN.feature_name(), "lang_en");
    /// assert_eq!(Language::CS.feature_name(), "lang_cs");
    /// ```
    pub fn feature_name(self) -> &'static str {
        match self {
            Language::EN => "lang_en",
            Language::CS => "lang_cs",
        }
    }

    pub fn name(self) -> &'static str {
        match self {
            Language::EN => "en",
            Language::CS => "cs",
        }
    }
}

impl LogLevel {
    /// Returns the cargo feature name corresponding to the log level.
    pub fn feature_name(self) -> &'static str {
        match self {
            LogLevel::Error => "log_level_error",
            LogLevel::Warn => "log_level_warn",
            LogLevel::Info => "log_level_info",
            LogLevel::Debug => "log_level_debug",
        }
    }
}

/// Top-level `xtask modular` CLI, parsed from `xtask modular <cmd> ...`.
#[derive(Parser, Debug)]
#[command(name = "xtask")]
#[command(about = "Trezor workspace automation tasks")]
pub struct Cli {
    /// The subcommand to run.
    #[command(subcommand)]
    pub command: Cmd,
}

/// A `xtask modular` subcommand.
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
    Test(TestArgs),
    /// Run device tests of specified package
    DeviceTest(DeviceTestArgs),
    /// Format code
    Fmt(FmtArgs),
    /// Clean build artifacts
    Clean,
}

/// Arguments for `xtask modular build`/`clippy`/`check`/`size`, i.e.
/// everything that needs a resolved feature set, profile, and (for a
/// non-emulator build) target triple. See [`BuildArgs::resolve_features`]
/// and [`BuildArgs::configure_cargo`].
#[derive(Args, Debug, Clone)]
#[command(
    override_usage = "xtask build [-p <PACKAGE>]... --model <MODEL> --language <LANGUAGE> --log_level <LOG_LEVEL> [OPTIONS]"
)]
pub struct BuildArgs {
    /// App package(s) to build; may be repeated. Defaults to every app
    /// package in the workspace.
    #[arg(long, short = 'p')]
    pub package: Vec<String>,

    /// Build target model
    #[arg(long, short = 'm', ignore_case = true)]
    pub model: Option<Model>,

    /// Build target architecture (defaults to the model's; required when
    /// no model is given for a non-emulator build)
    #[arg(long, ignore_case = true)]
    pub arch: Option<TargetArch>,

    /// Use emulator build
    #[arg(long, short = 'e')]
    pub emulator: bool,

    /// Build target language
    #[arg(long, ignore_case = true, default_value = "en")]
    pub lang: Language,

    /// Log level for the built firmware
    #[arg(long, ignore_case = true, default_value = "info")]
    pub log_level: LogLevel,

    /// Use the `debug-fw` cargo profile instead of `release-fw`.
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
    /// Resolves the list of cargo features to enable based on the provided
    /// cli arguments: always the model, language, and log-level features,
    /// plus `emulator`/`debug` when those flags are set, plus `dev_keys`
    /// unless this is a `--production` build.
    ///
    /// ```
    /// use modular_app-tool::args::{BuildArgs, Language, LogLevel, Model};
    ///
    /// let args = BuildArgs {
    ///     package: vec!["tron".into()],
    ///     model: Model::T3W1,
    ///     lang: Language::EN,
    ///     log_level: LogLevel::Info,
    ///     emulator: true,
    ///     debug: false,
    ///     production: false,
    ///     verbose: false,
    /// };
    ///
    /// let features = args.resolve_features().unwrap();
    /// assert_eq!(
    ///     features,
    ///     vec!["model_t3w1", "lang_en", "log_level_info", "emulator", "dev_keys"]
    /// );
    /// ```
    pub fn resolve_features(&self) -> Result<Vec<&'static str>> {
        let mut features = vec![self.lang.feature_name(), self.log_level.feature_name()];

        if let Some(model) = &self.model {
            features.push(model.feature_name());
        }

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

    /// Configures the cargo command with the appropriate arguments and features
    /// based on the provided cli arguments, restricted to `packages`.
    pub fn configure_cargo(&self, cmd: &mut process::Command, packages: &[Package]) -> Result<()> {
        for package in packages {
            cmd.arg("-p").arg(&package.name);
        }

        let features = self.resolve_features()?;
        cmd.args(["--features", &features.join(",")]);

        if self.debug {
            cmd.arg("--profile").arg("debug-fw");
        } else {
            cmd.arg("--profile")
                .arg("release-fw")
                .arg("-Zbuild-std=core,alloc");
        }

        if !self.emulator {
            // !@# TODO introduce --target option
            let target = self
                .model
                .map_or(Model::T3W1.target_triple(), |m| m.target_triple());
            // Not a file in the app's own source tree: the layout is fixed
            // by Core's loader and identical for every app, so the script
            // ships with this crate and gets written into the build
            // directory here -- see `crate::linker`.
            let linker_script = prebuild::prepare_linker_script()?;
            cmd.args(["--target", target]);
            cmd.env(
                "RUSTFLAGS",
                format!(
                    "-C link-arg=-T{} \
                     -C link-arg=--emit-relocs \
                     -C link-arg=-z \
                     -C link-arg=max-page-size=0x20 \
                     -C link-arg=--no-dynamic-linker",
                    linker_script.display()
                ),
            );
        }

        if self.verbose {
            cmd.arg("--verbose");
        }

        Ok(())
    }

    /// Returns the Rust target triple used when building firmware (i.e.
    /// non-emulator) for the model.
    pub fn target_triple(&self) -> Option<&'static str> {
        if self.emulator {
            None
        } else if let Some(model) = &self.model {
            Some(model.target_triple())
        } else {
            Some(Model::T3W1.target_triple())
        }
    }
}

/// Arguments for `xtask modular unit-tests`.
#[derive(Args, Debug)]
#[command(
    override_usage = "cargo xtask unit-tests [-p <PACKAGE>]... --model <MODEL> --language <LANGUAGE> [OPTIONS]"
)]
pub struct TestArgs {
    /// App package(s) to test; may be repeated. Defaults to every app
    /// package in the workspace.
    #[arg(long, short = 'p')]
    pub package: Vec<String>,

    /// Build target model
    #[arg(long, short = 'm', ignore_case = true, default_value = "t3w1")]
    pub model: Model,

    /// Build target language
    #[arg(long, ignore_case = true, default_value = "en")]
    pub lang: Language,

    /// Test to run (defaults to all tests in the package)
    #[arg(long, short = 't', default_value = "")]
    pub test: String,
}

/// Arguments for `xtask modular device-tests`.
#[derive(Args, Debug)]
#[command(override_usage = "cargo xtask device-tests [-p <PACKAGE>] --model <MODEL> [OPTIONS]")]
pub struct DeviceTestArgs {
    #[command(flatten)]
    pub build: BuildArgs,

    /// Test to run (defaults to all tests in the package).
    #[arg(long, short = 't', default_value = "")]
    pub test: String,

    /// Run with UI screenshot testing enabled.
    #[arg(long)]
    pub ui: bool,

    /// Language of the device UI for this test run.
    #[arg(long)]
    pub device_lang: Option<Language>,
}

#[derive(Args, Debug)]
pub struct FmtArgs {
    /// App package(s) to format; may be repeated. Defaults to every app
    /// package in the workspace.
    #[arg(long, short = 'p')]
    pub package: Vec<String>,

    /// Run `cargo fmt` in check mode (does not modify files)
    #[arg(long)]
    pub check: bool,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn model_feature_names_are_unique_and_prefixed() {
        let names = [Model::T3T1, Model::T3W1].map(Model::feature_name);
        assert_eq!(names, ["model_t3t1", "model_t3w1"]);
    }

    #[test]
    fn model_id_matches_clap_value_name() {
        // `model_id` feeds artifact/directory naming and is maintained
        // separately from the `#[value(name = "...")]` clap attributes on
        // `Model`'s variants -- catch the two drifting apart.
        for model in [Model::T3T1, Model::T3W1] {
            let clap_name = model.to_possible_value().unwrap().get_name().to_string();
            assert_eq!(model.model_id(), clap_name);
        }
    }

    #[test]
    fn language_feature_names() {
        assert_eq!(Language::EN.feature_name(), "lang_en");
        assert_eq!(Language::CS.feature_name(), "lang_cs");
    }

    #[test]
    fn log_level_feature_names() {
        assert_eq!(LogLevel::Error.feature_name(), "log_level_error");
        assert_eq!(LogLevel::Warn.feature_name(), "log_level_warn");
        assert_eq!(LogLevel::Info.feature_name(), "log_level_info");
        assert_eq!(LogLevel::Debug.feature_name(), "log_level_debug");
    }

    fn build_args(emulator: bool, debug: bool, production: bool) -> BuildArgs {
        BuildArgs {
            package: vec!["tron".into()],
            arch: None,
            model: Some(Model::T3W1),
            lang: Language::EN,
            log_level: LogLevel::Info,
            emulator,
            debug,
            production,
            verbose: false,
        }
    }

    #[test]
    fn resolve_features_always_includes_model_lang_and_log_level() {
        let features = build_args(false, false, false).resolve_features().unwrap();
        assert!(features.contains(&"model_t3w1"));
        assert!(features.contains(&"lang_en"));
        assert!(features.contains(&"log_level_info"));
    }

    #[test]
    fn resolve_features_dev_build_adds_dev_keys_not_production() {
        let features = build_args(false, false, false).resolve_features().unwrap();
        assert!(features.contains(&"dev_keys"));
        assert!(!features.contains(&"emulator"));
        assert!(!features.contains(&"debug"));
    }

    #[test]
    fn resolve_features_production_build_omits_dev_keys() {
        let features = build_args(false, false, true).resolve_features().unwrap();
        assert!(!features.contains(&"dev_keys"));
    }

    #[test]
    fn resolve_features_emulator_and_debug_add_their_own_features() {
        let features = build_args(true, true, false).resolve_features().unwrap();
        assert!(features.contains(&"emulator"));
        assert!(features.contains(&"debug"));
    }
}
