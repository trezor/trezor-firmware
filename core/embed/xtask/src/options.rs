use anyhow::Result;
use clap::Args;
use serde::Deserialize;

use crate::args::{BuildArgs, ConsoleType, Model, Project};
use crate::presets;

/// How an option's `Option<T>` value from the defaults/presets/CLI layers is
/// unwrapped into its [`ResolvedBuildArgs`] field.
pub trait ResolveValue: Sized {
    type Resolved;
    fn resolve(value: Option<Self>) -> Self::Resolved;
}

/// Flags resolve to plain bools; unset means disabled.
impl ResolveValue for bool {
    type Resolved = bool;
    fn resolve(value: Option<Self>) -> Self::Resolved {
        value.unwrap_or_default()
    }
}

/// Unset resolves to [`ConsoleType::None`] (no debug console).
impl ResolveValue for ConsoleType {
    type Resolved = ConsoleType;
    fn resolve(value: Option<Self>) -> Self::Resolved {
        value.unwrap_or_default()
    }
}

/// The board selection stays optional; unset means the model's default board.
impl ResolveValue for String {
    type Resolved = Option<String>;
    fn resolve(value: Option<Self>) -> Self::Resolved {
        value
    }
}

/// [`OptionsMap`] field type for an option, by kind: `map` options carry
/// their [`MapValue`] mapping table, `opt` options carry [`NotMappable`],
/// whose parsing always fails.
macro_rules! option_map_ty {
    (map, $ty:ty) => { Option<<$ty as MapValue>::Map> };
    (opt, $ty:ty) => { NotMappable };
}

/// [`OptionsMap::resolve`] arm for an option, by kind: `map` options select
/// features from their mapping table, `opt` options expand to nothing.
macro_rules! option_resolve_arm {
    ($activated:ident, $map:expr, $value:expr, map, $name:ident, $ty:ty) => {
        if let Some(map) = &$map {
            for feature in <$ty as MapValue>::select(map, $value) {
                $activated.push(ActivatedFeature {
                    option: stringify!($name).replace('_', "-"),
                    feature: feature.clone(),
                });
            }
        }
    };
    ($activated:ident, $map:expr, $value:expr, opt, $name:ident, $ty:ty) => {};
}

/// Generates the whole option plumbing from a single option list:
/// [`BuildOptions`] (every option as an overridable `Option<T>` CLI
/// argument), its `overlay()`, [`ResolvedBuildArgs`] (the project, model and
/// emulator build parameters plus every option unwrapped per
/// [`ResolveValue`]), `from_build_args()`, and [`OptionsMap`] with its
/// `resolve()`.
///
/// Each entry is declared as `<kind> <name>: <type>`:
/// - `map`  — the option may be mapped to cargo features in a project.toml
///   `[build-options]` table (the type must implement [`MapValue`]);
/// - `opt`  — a plain build option; mapping it in project.toml fails to parse.
macro_rules! build_options {
    ($($(#[$attr:meta])* $kind:ident $name:ident: $ty:ty),+ $(,)?) => {
        #[derive(Args, Deserialize, Debug, Clone, Default)]
        #[serde(deny_unknown_fields)]
        #[serde(rename_all = "kebab-case")]
        pub struct BuildOptions {
            $(
                $(#[$attr])*
                pub $name: Option<$ty>,
            )+
        }

        impl BuildOptions {
            /// Overlays `opt` onto `self`; values set in `opt` win.
            pub fn overlay(self, opt: Self) -> Self {
                Self {
                    $($name: opt.$name.or(self.$name),)+
                }
            }
        }

        /// Build arguments with the defaults, preset and CLI layers applied.
        #[derive(Debug, Clone, Default)]
        pub struct ResolvedBuildArgs {
            pub project: Project,
            pub model: Model,
            pub emulator: bool,
            $(pub $name: <$ty as ResolveValue>::Resolved,)+
        }

        impl ResolvedBuildArgs {
            pub fn from_build_args(args: &BuildArgs) -> Result<Self> {
                let preset_options = presets::resolve(args)?;
                let o = preset_options
                    .overlay(args.options.clone());

                Ok(Self {
                    project: args.project,
                    model: args.model,
                    emulator: args.emulator,
                    $($name: <$ty as ResolveValue>::resolve(o.$name),)+
                })
            }
        }

        /// The `[build-options]` table of a project.toml: the project's complete
        /// mapping from [`BuildOptions`] to cargo features. An option absent
        /// from the table is ignored by the project. Options declared `opt`
        /// never map to features; putting them in the table fails at parse
        /// time.
        ///
        /// The schema stays a plain "option value -> feature list" lookup;
        /// anything needing conditions on other options or build parameters
        /// belongs in Rust (see `feature_resolver`).
        #[derive(Deserialize, Debug, Clone, Default)]
        #[serde(deny_unknown_fields, rename_all = "kebab-case")]
        pub struct OptionsMap {
            $(
                #[serde(default)]
                pub $name: option_map_ty!($kind, $ty),
            )+
        }

        impl OptionsMap {
            /// Selects the features activated by the resolved option values.
            /// Options are visited in declaration order for deterministic
            /// output.
            pub fn resolve(&self, args: &ResolvedBuildArgs) -> Vec<ActivatedFeature> {
                let mut activated = Vec::new();

                $(option_resolve_arm!(activated, self.$name, args.$name, $kind, $name, $ty);)+

                activated
            }
        }
    };
}

build_options! {
    /// Enable debug build
    #[arg(long, short = 'd', num_args = 0..=1, default_missing_value = "true")]
    opt debug: bool,

    /// Debug console backend
    #[arg(long)]
    map dbg_console: ConsoleType,

    /// Build Bitcoin-only firmware
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    map btc_only: bool,

    /// Enable production build
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    map production: bool,

    /// Force bootloader upgrade
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    map force_bootloader_upgrade: bool,

    /// Use dev bootloader
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    map bootloader_devel: bool,

    /// Enable unsafe firmware features
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    map unsafe_fw: bool,

    /// Embed frozen MicroPython modules
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    map frozen: bool,

    /// Include MicroPython source lines
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    map source_lines: bool,

    /// Optimize MicroPython bytecode
    #[arg(long, num_args = 0..=1, default_missing_value = "true", overrides_with = "pyopt")]
    map pyopt: bool,

    /// Enable Micropython memory performance measurements
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    map mem_perf: bool,

    /// Enable debug link
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    map debug_link: bool,

    /// Enable N1W1 support
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    map n1w1: bool,

    /// Disable UI animations
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    map disable_animation: bool,

    /// Show UI perf overlay
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    map perf_overlay: bool,

    /// Include crypto benchmarks
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    map benchmark: bool,

    /// Log stack usage
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    map log_stack_usage: bool,

    /// Use blocking VCP writes, in order to allow reliable debug data
    /// transmission over VCP. Disabled by default, to prevent debug
    /// firmware from getting stuck while writing log messages (if the host
    /// is not reading them).
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    map block_on_vcp: bool,

    /// Enable Address Sanitizer (ASAN) instrumentation
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    opt asan: bool,

    /// Enable external app loading
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    map apps: bool,

    /// Disable OPTIGA support
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    opt disable_optiga: bool,

    /// Board revision to build for (defaults to model's default_board)
    #[arg(long, short = 'b')]
    opt board: String,

    /// Disable TROPIC support
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    opt disable_tropic: bool,

    /// Enable insecure storage test mode
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    map storage_insecure_testing_mode: bool,

    /// Output cargo timings
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    opt timings: bool,

    /// Enable verbose output
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    opt verbose: bool,

    /// Log build script progress (executed commands and timings)
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    opt xbuild_trace: bool,
}

impl ResolvedBuildArgs {
    /// Determines the Cargo profile to use
    pub fn cargo_profile_name(&self) -> &'static str {
        if self.debug {
            if self.emulator { "dev" } else { "debug-opt" }
        } else {
            "release"
        }
    }
}

/// Cargo features activated by a boolean build option, per option value.
/// An omitted key means the value activates no features.
#[derive(Deserialize, Debug, Clone, Default)]
#[serde(deny_unknown_fields)]
pub struct BoolMap {
    #[serde(rename = "true", default)]
    pub on: Vec<String>,
    #[serde(rename = "false", default)]
    pub off: Vec<String>,
}

/// Implemented by option value types that can be mapped to cargo features in
/// a project.toml `[build-options]` table; associates the value type with its
/// mapping-table representation and selects the features for a value.
pub trait MapValue: Sized {
    type Map;
    fn select(map: &Self::Map, value: Self) -> &[String];
}

impl MapValue for bool {
    type Map = BoolMap;
    fn select(map: &Self::Map, value: Self) -> &[String] {
        if value { &map.on } else { &map.off }
    }
}

impl MapValue for ConsoleType {
    type Map = ConsoleMap;
    fn select(map: &Self::Map, value: Self) -> &[String] {
        match value {
            ConsoleType::None => &[],
            ConsoleType::Vcp => &map.vcp,
            ConsoleType::Swo => &map.swo,
            ConsoleType::SystemView => &map.system_view,
        }
    }
}

/// Cargo features activated by the `dbg-console` option, per console type.
/// An omitted key means the console type activates no features.
#[derive(Deserialize, Debug, Clone, Default)]
#[serde(deny_unknown_fields, rename_all = "kebab-case")]
pub struct ConsoleMap {
    #[serde(default)]
    pub vcp: Vec<String>,
    #[serde(default)]
    pub swo: Vec<String>,
    #[serde(default)]
    pub system_view: Vec<String>,
}

/// A feature selected from the `[build-options]` table, together with the
/// option that activated it (for error reporting).
pub struct ActivatedFeature {
    pub option: String,
    pub feature: String,
}

/// [`OptionsMap`] field type for options declared `opt`: parsing always
/// fails, so project.toml cannot map these options to cargo features.
#[derive(Debug, Clone, Default)]
pub struct NotMappable;

impl<'de> Deserialize<'de> for NotMappable {
    fn deserialize<D>(_deserializer: D) -> Result<Self, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        Err(serde::de::Error::custom(
            "this build option cannot be mapped to cargo features",
        ))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_bool_and_console_maps() {
        let map: OptionsMap = toml::from_str(
            r#"
                production  = { true = ["production"], false = ["dev_keys"] }
                btc-only    = { false = ["universal_fw"] }
                debug-link  = { true = ["debuglink", "ui_debug"] }
                dbg-console = { vcp = ["dbg_console_vcp"], system-view = ["dbg_console_system_view"] }
            "#,
        )
        .unwrap();

        assert_eq!(map.production.as_ref().unwrap().on, ["production"]);
        assert_eq!(map.production.as_ref().unwrap().off, ["dev_keys"]);
        assert!(map.btc_only.as_ref().unwrap().on.is_empty());
        assert_eq!(
            map.dbg_console.as_ref().unwrap().system_view,
            ["dbg_console_system_view"]
        );
        assert!(map.dbg_console.as_ref().unwrap().swo.is_empty());
    }

    #[test]
    fn rejects_unknown_option_names() {
        let result: Result<OptionsMap, _> = toml::from_str(r#"prodction = { true = ["x"] }"#);
        assert!(result.is_err());
    }

    #[test]
    fn rejects_non_mappable_options() {
        // `verbose` is a build option but never maps to features.
        let result: Result<OptionsMap, _> = toml::from_str(r#"verbose = { true = ["x"] }"#);
        assert!(result.is_err());
    }

    #[test]
    fn rejects_unknown_console_types() {
        let result: Result<OptionsMap, _> = toml::from_str(r#"dbg-console = { uart = ["x"] }"#);
        assert!(result.is_err());
    }
}
