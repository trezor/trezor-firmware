use clap::Args;
use serde::Deserialize;

use crate::args::{BuildArgs, ConsoleType, Model, Project};

#[derive(Args, Deserialize, Debug, Clone, Default)]
#[serde(deny_unknown_fields)]
pub struct BuildOptions {
    /// Enable debug build
    #[arg(long, short = 'd', num_args = 0..=1, default_missing_value = "true")]
    pub debug: Option<bool>,

    /// Debug console backend
    #[arg(long)]
    pub dbg_console: Option<ConsoleType>,

    /// Build Bitcoin-only firmware
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub btc_only: Option<bool>,

    /// Enable production build
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub production: Option<bool>,

    /// Force bootloader upgrade
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub force_bootloader_upgrade: Option<bool>,

    /// Use dev bootloader
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub bootloader_devel: Option<bool>,

    /// Enable unsafe firmware features
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub unsafe_fw: Option<bool>,

    /// Embed frozen MicroPython modules
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub frozen: Option<bool>,

    /// Include MicroPython source lines
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub source_lines: Option<bool>,

    /// Optimize MicroPython bytecode
    #[arg(long, num_args = 0..=1, default_missing_value = "true", overrides_with = "pyopt")]
    pub pyopt: Option<bool>,

    /// Enable Micropython memory performance measurements
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub mem_perf: Option<bool>,

    /// Enable debug link
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub debug_link: Option<bool>,

    /// Enable N4W1 support
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub n4w1: Option<bool>,

    /// Disable UI animations
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub disable_animation: Option<bool>,

    /// Show UI perf overlay
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub perf_overlay: Option<bool>,

    /// Include crypto benchmarks
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub benchmark: Option<bool>,

    /// Log stack usage
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub log_stack_usage: Option<bool>,

    /// Use blocking VCP writes, in order to allow reliable debug data
    /// transmission over VCP. Disabled by default, to prevent debug
    /// firmware from getting stuck while writing log messages (if the host
    /// is not reading them).
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub block_on_vcp: Option<bool>,

    /// Enable Address Sanitizer (ASAN) instrumentation
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub asan: Option<bool>,

    /// Enable external app loading
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub apps: Option<bool>,

    /// Disable OPTIGA support
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub disable_optiga: Option<bool>,

    /// Board revision to build for (defaults to model's default_board)
    #[arg(long, short = 'b')]
    pub board: Option<String>,

    /// Disable TROPIC support
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub disable_tropic: Option<bool>,

    /// Enable insecure storage test mode
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub storage_insecure_testing_mode: Option<bool>,

    /// Emits memory analysis output (type sizes and stack sizes)
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub emit_memory_analysis: Option<bool>,

    /// Output cargo timings
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub timings: Option<bool>,

    /// Enable verbose output
    #[arg(long, num_args = 0..=1, default_missing_value = "true")]
    pub verbose: Option<bool>,
}

impl BuildOptions {
    pub fn defaults_for(_project: Project, _model: Model, emulator: bool) -> Self {
        Self {
            debug: Some(emulator),
            pyopt: Some(true),
            source_lines: Some(emulator),
            ..BuildOptions::default()
        }
    }

    pub fn overlay(self, opt: Self) -> Self {
        Self {
            debug: opt.debug.or(self.debug),
            dbg_console: opt.dbg_console.or(self.dbg_console),
            btc_only: opt.btc_only.or(self.btc_only),
            production: opt.production.or(self.production),
            force_bootloader_upgrade: opt
                .force_bootloader_upgrade
                .or(self.force_bootloader_upgrade),
            bootloader_devel: opt.bootloader_devel.or(self.bootloader_devel),
            unsafe_fw: opt.unsafe_fw.or(self.unsafe_fw),
            frozen: opt.frozen.or(self.frozen),
            source_lines: opt.source_lines.or(self.source_lines),
            pyopt: opt.pyopt.or(self.pyopt),
            mem_perf: opt.mem_perf.or(self.mem_perf),
            debug_link: opt.debug_link.or(self.debug_link),
            n4w1: opt.n4w1.or(self.n4w1),
            disable_animation: opt.disable_animation.or(self.disable_animation),
            perf_overlay: opt.perf_overlay.or(self.perf_overlay),
            benchmark: opt.benchmark.or(self.benchmark),
            log_stack_usage: opt.log_stack_usage.or(self.log_stack_usage),
            block_on_vcp: opt.block_on_vcp.or(self.block_on_vcp),
            asan: opt.asan.or(self.asan),
            apps: opt.apps.or(self.apps),
            disable_optiga: opt.disable_optiga.or(self.disable_optiga),
            board: opt.board.or(self.board),
            disable_tropic: opt.disable_tropic.or(self.disable_tropic),
            storage_insecure_testing_mode: opt
                .storage_insecure_testing_mode
                .or(self.storage_insecure_testing_mode),
            emit_memory_analysis: opt.emit_memory_analysis.or(self.emit_memory_analysis),
            timings: opt.timings.or(self.timings),
            verbose: opt.verbose.or(self.verbose),
        }
    }

    pub fn postfix(self) -> Self {
        let pyopt = self.pyopt.unwrap_or(true);
        Self {
            debug_link: self.debug_link.or(Some(!pyopt)),
            pyopt: Some(pyopt),
            ..self
        }
    }
}

#[derive(Debug, Clone)]
pub struct ResolvedBuildArgs {
    pub project: Project,
    pub model: Model,
    pub emulator: bool,
    pub debug: bool,
    pub dbg_console: Option<ConsoleType>,
    pub btc_only: bool,
    pub production: bool,
    pub force_bootloader_upgrade: bool,
    pub bootloader_devel: bool,
    pub unsafe_fw: bool,
    pub frozen: bool,
    pub source_lines: bool,
    pub pyopt: bool,
    pub mem_perf: bool,
    pub debug_link: bool,
    pub n4w1: bool,
    pub disable_animation: bool,
    pub perf_overlay: bool,
    pub benchmark: bool,
    pub log_stack_usage: bool,
    pub block_on_vcp: bool,
    pub asan: bool,
    pub apps: bool,
    pub disable_optiga: bool,
    pub board: Option<String>,
    pub disable_tropic: bool,
    pub storage_insecure_testing_mode: bool,
    pub emit_memory_analysis: bool,
    pub timings: bool,
    pub verbose: bool,
}

impl ResolvedBuildArgs {
    pub fn from_build_args(args: &BuildArgs) -> Self {
        let o = BuildOptions::defaults_for(args.project, args.model, args.emulator)
            .overlay(args.options.clone())
            .postfix();

        Self {
            project: args.project,
            model: args.model,
            emulator: args.emulator,
            debug: o.debug.unwrap_or_default(),
            dbg_console: o.dbg_console,
            btc_only: o.btc_only.unwrap_or_default(),
            production: o.production.unwrap_or_default(),
            force_bootloader_upgrade: o.force_bootloader_upgrade.unwrap_or_default(),
            bootloader_devel: o.bootloader_devel.unwrap_or_default(),
            unsafe_fw: o.unsafe_fw.unwrap_or_default(),
            frozen: o.frozen.unwrap_or_default(),
            source_lines: o.source_lines.unwrap_or_default(),
            pyopt: o.pyopt.unwrap_or_default(),
            mem_perf: o.mem_perf.unwrap_or_default(),
            debug_link: o.debug_link.unwrap_or_default(),
            n4w1: o.n4w1.unwrap_or_default(),
            disable_animation: o.disable_animation.unwrap_or_default(),
            perf_overlay: o.perf_overlay.unwrap_or_default(),
            benchmark: o.benchmark.unwrap_or_default(),
            log_stack_usage: o.log_stack_usage.unwrap_or_default(),
            block_on_vcp: o.block_on_vcp.unwrap_or_default(),
            asan: o.asan.unwrap_or_default(),
            apps: o.apps.unwrap_or_default(),
            disable_optiga: o.disable_optiga.unwrap_or_default(),
            board: o.board,
            disable_tropic: o.disable_tropic.unwrap_or_default(),
            storage_insecure_testing_mode: o.storage_insecure_testing_mode.unwrap_or_default(),
            emit_memory_analysis: o.emit_memory_analysis.unwrap_or_default(),
            timings: o.timings.unwrap_or_default(),
            verbose: o.verbose.unwrap_or_default(),
        }
    }

    /// Determines the Cargo profile to use
    pub fn cargo_profile_name(&self) -> &'static str {
        if self.debug {
            if self.emulator { "dev" } else { "debug-opt" }
        } else {
            "release"
        }
    }
}
