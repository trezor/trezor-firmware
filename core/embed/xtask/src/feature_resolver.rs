use anyhow::{Result, anyhow, bail};
use std::process;

use crate::{
    args::{BuildArgs, Component, ConsoleType, ResolvedBuild},
    config,
};

/// Resolves cargo features and target triple from the provided CLI arguments.
pub fn resolve_features(args: &BuildArgs) -> Result<ResolvedBuild> {
    let mut features: Vec<String> = vec![args.model.feature_name()];

    if args.emulator {
        features.push("emulator".into());
    }

    if args.production {
        features.push("production".into());
    }

    if args.bootloader_devel {
        features.push("bootloader_devel".into());
    }

    if args.bootloader_qa {
        features.push("bootloader_qa".into());
    }

    if args.emulator {
        features.push("dbg_console".into());
    } else {
        match (args.component, args.dbg_console) {
            (Component::Firmware, Some(_)) => features.push("dbg_console".into()),
            (Component::Secmon, Some(ConsoleType::Vcp)) => (),
            (Component::Boardloader, Some(ConsoleType::Vcp)) => (),
            (Component::Prodtest, Some(ConsoleType::Vcp)) => (),
            (_, Some(ConsoleType::Vcp)) => features.push("dbg_console_vcp".into()),
            (_, Some(ConsoleType::Swo)) => features.push("dbg_console_swo".into()),
            (_, Some(ConsoleType::SystemView)) => features.push("dbg_console_sysview".into()),
            (_, None) => (),
        }
    }

    let pyopt = args.pyopt.unwrap_or(!args.emulator);

    if args.component == Component::Firmware {
        if pyopt {
            features.push("pyopt".into());
        } else {
            features.push("debug".into());
        }

        if args.source_lines.unwrap_or(args.emulator) {
            features.push("micropy_enable_source_lines".into());
        }

        if args.benchmark {
            features.push("benchmark".into());
        }

        if args.log_stack_usage {
            features.push("log_stack_usage".into());
        }

        if args.block_on_vcp {
            features.push("block_on_vcp".into());
        }

        if args.apps {
            features.push("app_loading".into());
        }

        if args.mem_perf {
            features.push("memperf".into());
        }

        if !args.production {
            features.push("dev_keys".into());
        }

        if args.n4w1 {
            features.push("n4w1".into());
        }
    }

    if matches!(
        args.component,
        Component::Secmon | Component::Kernel | Component::Firmware
    ) {
        if !args.btc_only {
            features.push("universal_fw".into());
        }

        if !pyopt {
            features.push("optiga_testing".into());
        }

        if args.unsafe_fw {
            features.push("unsafe_fw".into());
        }

        if args.storage_insecure_testing_mode {
            if args.production {
                bail!("storage_insecure_testing_mode cannot be enabled in production builds");
            }
            features.push("storage_insecure_testing_mode".into());
        }
    }

    if matches!(
        args.component,
        Component::Firmware | Component::Bootloader | Component::Prodtest
    ) {
        if args.perf_overlay {
            features.push("ui_performance_overlay".into());
        }

        if args.debug_link.unwrap_or(args.emulator) {
            features.push("debuglink".into());
            features.push("ui_debug".into());
        }

        if args.disable_animation {
            features.push("disable_animation".into());
        }
    }

    if matches!(args.component, Component::Kernel) {
        if args.debug_link.unwrap_or(args.emulator) {
            features.push("debuglink".into());
        }
    }

    if args
        .frozen
        .unwrap_or(args.component.frozen_default(args.emulator))
    {
        features.push("frozen".into());
    }

    // Board and model-intrinsic features from TOML config
    let model_config = config::ModelConfig::load(args.model.model_id())?;
    let board_id = if args.emulator {
        model_config
            .emulator_board
            .as_deref()
            .ok_or_else(|| anyhow!("Model {} has no emulator board", args.model.model_id()))?
            .to_string()
    } else {
        args.board
            .clone()
            .unwrap_or_else(|| model_config.default_board.clone())
    };
    let mut board_feat =
        config::resolve_board_features(args.model.model_id(), &model_config, &board_id, args.component)?
            .features;
    if args.disable_optiga {
        board_feat.retain(|f| f != "optiga");
    }
    if args.disable_tropic.unwrap_or(args.emulator) {
        board_feat.retain(|f| f != "tropic");
    }
    features.extend(board_feat);

    let target_triple = if args.emulator {
        None
    } else {
        Some(model_config.target_triple()?)
    };

    Ok(ResolvedBuild { features, target_triple })
}

/// Configures a cargo command with the appropriate arguments and features.
pub fn configure_cargo(args: &BuildArgs, cmd: &mut process::Command) -> Result<()> {
    let resolved = resolve_features(args)?;

    cmd.args(["--package", args.component.package_name(args.emulator)]);
    cmd.args(["--features", &resolved.features.join(",")]);

    if !args.debug.unwrap_or(args.emulator) {
        cmd.arg("-Zbuild-std=core");
    }

    if let Some(triple) = resolved.target_triple {
        cmd.args(["--target", triple]);
    }

    if args.emit_memory_analysis {
        // 1. see https://nnethercote.github.io/perf-book/type-sizes.html#measuring-type-sizes for more details
        // 2. Adds an ELF section with Rust functions' stack sizes. See the following links for more details:
        // - https://doc.rust-lang.org/nightly/unstable-book/compiler-flags/emit-stack-sizes.html
        // - https://blog.japaric.io/stack-analysis/
        // - https://github.com/japaric/stack-sizes/
        cmd.env("RUSTFLAGS", "-Z print-type-sizes -Z emit-stack-sizes");
    }

    if args.emulator && args.asan {
        // # workaround for sanitizers being nightly-only
        //  remove after stabilized https://github.com/rust-lang/rust/issues/39699
        cmd.env("RUSTC_BOOTSTRAP", "1");
        cmd.args(["-Z", "sanitizer=address"]);
    }

    // We have different default for `--debug` for hardware and emulator builds
    if !args.debug.unwrap_or(args.emulator) {
        cmd.arg("--release");
    }

    if args.timings {
        cmd.arg("--timings");
    }

    if args.verbose {
        cmd.arg("--verbose");
    }

    Ok(())
}
