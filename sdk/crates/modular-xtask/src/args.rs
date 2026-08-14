//! CLI argument types for `xtask modular <cmd>`, parsed with `clap`.

use anyhow::{Result, ensure};
use clap::{Args, Parser, Subcommand, ValueEnum};

use std::process;

use crate::helpers;

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
    /// use modular_xtask::args::Model;
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

    /// Returns the model ID used in artifact/directory naming.
    ///
    /// ```
    /// use modular_xtask::args::Model;
    ///
    /// assert_eq!(Model::T3W1.model_id(), "t3w1");
    /// ```
    pub fn model_id(self) -> &'static str {
        match self {
            Model::T3T1 => "t3t1",
            Model::T3W1 => "t3w1",
        }
    }
}

impl Language {
    /// Returns the cargo feature name corresponding to the language.
    ///
    /// ```
    /// use modular_xtask::args::Language;
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
    UnitTests(UnitTestArgs),
    /// Run device tests of specified package
    DeviceTests(DeviceTestsArgs),
    /// Clean build artifacts
    Clean,
    /// Format code with rustfmt
    Fmt,
    /// Check code formatting with rustfmt
    FmtCheck,
    /// Upload firmware to device
    Upload(UploadArgs),
    /// Run Python style tools
    PyStyle(ProjectArgs),
    /// Run Python style checks
    PyStyleCheck(ProjectArgs),
    /// Run translation style tools
    TranslationStyle(ProjectArgs),
    /// Run translation style checks
    TranslationStyleCheck(ProjectArgs),
}

/// Arguments for `xtask modular build`/`clippy`/`check`/`size`, i.e.
/// everything that needs a resolved feature set, profile, and (for a
/// non-emulator build) target triple. See [`BuildArgs::resolve_features`]
/// and [`BuildArgs::configure_cargo`].
#[derive(Args, Debug, Clone)]
#[command(
    override_usage = "xtask build --project <PROJECT> --model <MODEL> --language <LANGUAGE> --log_level <LOG_LEVEL> [OPTIONS]"
)]
pub struct BuildArgs {
    /// Name of the app package to build (required when run in a workspace,
    /// ignored for a standalone app).
    #[arg(long, short = 'p', ignore_case = true, default_value = "")]
    pub project: String,

    /// Build target model
    #[arg(long, short = 'm', ignore_case = true, default_value = "t3w1")]
    pub model: Model,

    /// Build target language
    #[arg(long, ignore_case = true, default_value = "en")]
    pub lang: Language,

    /// Log level for the built firmware
    #[arg(long, ignore_case = true, default_value = "info")]
    pub log_level: LogLevel,

    /// Use emulator build
    #[arg(long, short = 'e')]
    pub emulator: bool,

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
    /// use modular_xtask::args::{BuildArgs, Language, LogLevel, Model};
    ///
    /// let args = BuildArgs {
    ///     project: "tron".into(),
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

    /// Configures the cargo command with the appropriate arguments and features
    /// based on the provided cli arguments
    pub fn configure_cargo(&self, cmd: &mut process::Command) -> Result<()> {
        if helpers::is_workspace()? {
            ensure!(
                !self.project.is_empty(),
                "Project name must be specified when running in a workspace"
            );
            cmd.arg("-p").arg(&self.project);
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
            let linker_script = if helpers::is_workspace()? {
                format!("{}/memory.x", self.project)
            } else {
                "memory.x".into()
            };
            cmd.args(["--target", self.model.target_triple()]);
            cmd.env(
                "RUSTFLAGS",
                format!(
                    "-C link-arg=-T{} \
                     -C link-arg=--emit-relocs \
                     -C link-arg=-z \
                     -C link-arg=max-page-size=0x20 \
                     -C link-arg=--no-dynamic-linker",
                    linker_script
                ),
            );
        }

        if self.verbose {
            cmd.arg("--verbose");
        }

        Ok(())
    }
}

/// Arguments for `xtask modular unit-tests`.
#[derive(Args, Debug)]
#[command(
    override_usage = "cargo xtask unit-tests --project <PROJECT> --model <MODEL> --language <LANGUAGE> [OPTIONS]"
)]
pub struct UnitTestArgs {
    /// Name of the app package to test (required when run in a workspace,
    /// ignored for a standalone app).
    #[arg(long, short = 'p', ignore_case = true, default_value = "")]
    pub project: String,

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

/// Arguments for `xtask modular upload`.
#[derive(Args, Debug)]
#[command(override_usage = "cargo xtask upload --project <PROJECT> --model <MODEL> [OPTIONS]")]
pub struct UploadArgs {
    /// Name of the app package to upload (required when run in a workspace,
    /// ignored for a standalone app).
    #[arg(long, short = 'p', ignore_case = true, default_value = "")]
    pub project: String,

    /// Target model the build being uploaded was built for.
    #[arg(long, short = 'm', ignore_case = true)]
    pub model: Model,

    /// Upload to the emulator instead of a physical device.
    #[arg(long, short = 'e')]
    pub emulator: bool,
}

/// Arguments for `xtask modular device-tests`.
#[derive(Args, Debug)]
#[command(
    override_usage = "cargo xtask device-tests --project <PROJECT> --model <MODEL> [OPTIONS]"
)]
pub struct DeviceTestsArgs {
    /// Name of the app package to test (required when run in a workspace,
    /// ignored for a standalone app).
    #[arg(long, short = 'p', ignore_case = true, default_value = "")]
    pub project: String,

    /// Target model the build under test was built for.
    #[arg(long, short = 'm', ignore_case = true)]
    pub model: Model,

    /// Run against the emulator instead of a physical device.
    #[arg(long, short = 'e')]
    pub emulator: bool,

    /// Test to run (defaults to all tests in the package)
    #[arg(long, short = 't', default_value = "")]
    pub test: String,
}

/// Arguments for the Python-style and translation-style subcommands, which
/// only need to know which app package to operate on.
#[derive(Args, Debug)]
pub struct ProjectArgs {
    /// Name of the app package (required when run in a workspace, ignored
    /// for a standalone app).
    #[arg(long, short = 'p', default_value = "")]
    pub project: String,
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
            project: "tron".into(),
            model: Model::T3W1,
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
