use std::process;

use anyhow::{Result, bail};

use crate::args::{BuildArgs, ConsoleType, Project, ResolvedBuild};
use crate::{config, helpers};

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

    if args.force_bootloader_upgrade {
        features.push("force_bootloader_upgrade".into());
    }

    if args.emulator {
        features.push("dbg_console".into());

        if args.asan {
            features.push("asan".into());
        }
    } else {
        match (args.project, args.dbg_console) {
            (Project::Firmware, Some(_)) => features.push("dbg_console".into()),
            (Project::Secmon, Some(ConsoleType::Vcp)) => (),
            (Project::Boardloader, Some(ConsoleType::Vcp)) => (),
            (Project::Prodtest, Some(ConsoleType::Vcp)) => (),
            (_, Some(ConsoleType::Vcp)) => features.push("dbg_console_vcp".into()),
            (_, Some(ConsoleType::Swo)) => features.push("dbg_console_swo".into()),
            (_, Some(ConsoleType::SystemView)) => features.push("dbg_console_system_view".into()),
            (_, None) => (),
        }
    }

    let pyopt = args.pyopt.unwrap_or(true);

    if args.project == Project::Firmware {
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

    if matches!(args.project, Project::Firmware | Project::Kernel) {
        if args.block_on_vcp {
            features.push("block_on_vcp".into());
        }

        if args.apps {
            features.push("app_loading".into());
        }
    }

    if matches!(
        args.project,
        Project::Secmon | Project::Kernel | Project::Firmware
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
        args.project,
        Project::Firmware | Project::Bootloader | Project::Prodtest
    ) {
        if args.perf_overlay {
            features.push("ui_performance_overlay".into());
        }

        if !pyopt {
            features.push("ui_debug_overlay".into());
        }

        if args.debug_link.unwrap_or(!pyopt) {
            features.push("debuglink".into());
            features.push("ui_debug".into());
        }

        if args.disable_animation {
            features.push("disable_animation".into());
        }
    }

    if matches!(args.project, Project::Kernel) {
        if args.debug_link.unwrap_or(!pyopt) {
            features.push("debuglink".into());
        }
    }

    if args.project == Project::Firmware && (args.frozen || !args.emulator) {
        features.push("frozen".into());
    }

    // Board and model-intrinsic features from TOML config. The emulator emulates
    // the same board it would build for on real hardware (`default_board`, or an
    // explicit `--board`); only the configuration header differs.
    let model_config = args.model.config()?;
    let board_id = args
        .board
        .clone()
        .unwrap_or_else(|| model_config.default_board.clone());
    let board_features =
        config::resolve_board_features(&model_config, &board_id, args.project, args.emulator)?;
    let mut board_feat = board_features.features;
    if args.disable_optiga {
        board_feat.retain(|f| f != "optiga");
    }
    if args.disable_tropic {
        board_feat.retain(|f| f != "tropic");
    }
    features.extend(board_feat);

    let target_triple = if args.emulator {
        None
    } else {
        Some(model_config.target_triple()?)
    };

    Ok(ResolvedBuild {
        features,
        target_triple,
        board_header: board_features.board_header,
    })
}

/// Configures a cargo command with the appropriate arguments and features.
pub fn configure_cargo(args: &BuildArgs, cmd: &mut process::Command) -> Result<()> {
    let resolved = resolve_features(args)?;
    let mut rebuild_std = false;

    cmd.args(["--package", args.project.package_name(args.emulator)]);
    cmd.args(["--features", &resolved.features.join(",")]);
    cmd.args(["--profile", args.profile_name()]);
    cmd.env("TREZOR_BOARD_HEADER", &resolved.board_header);

    if args.profile_name() == "release" {
        // Required by panic-immediate-abort in the release profile
        rebuild_std = true;
    }

    if let Some(triple) = resolved.target_triple {
        cmd.args(["--target", triple]);
    }

    if args.emit_memory_analysis {
        // See https://nnethercote.github.io/perf-book/type-sizes.html#measuring-type-sizes for more details
        // Also adds an ELF section with Rust functions' stack sizes. See:
        // - https://doc.rust-lang.org/nightly/unstable-book/compiler-flags/emit-stack-sizes.html
        // - https://blog.japaric.io/stack-analysis/
        // - https://github.com/japaric/stack-sizes/
        //
        // Use --config instead of RUSTFLAGS env so that rustflags in .cargo/config.toml
        // are not overridden (RUSTFLAGS env has higher precedence and replaces
        // them entirely).
        cmd.args([
            "--config",
            "build.rustflags=[\"-Zprint-type-sizes\", \"-Zemit-stack-sizes\"]",
        ]);
    }

    if args.emulator && args.asan {
        // -Zsanitizer=address is a rustc flag passed via RUSTFLAGS.
        //
        // Without an explicit --target, cargo compiles proc-macros and the firmware in
        // the same pass and RUSTFLAGS leaks into proc-macro crates, causing
        // "can't find crate" errors. Passing --target explicitly (even the same
        // triple as the host) makes cargo separate the host (proc-macros /
        // build scripts) and target (firmware) compilation units, so RUSTFLAGS
        // only reaches the firmware crates.
        cmd.args(["--target", &helpers::host_triple()?]);
        cmd.args([
            "--config",
            "build.rustflags=[\"-Zsanitizer=address\", \"-Clink-arg=-lgcc_s\"]",
        ]);

        // Rebuild standard library to be compiled with sanitizer instrumentation
        rebuild_std = true;
    }

    if args.timings {
        cmd.arg("--timings");
    }

    if args.verbose {
        cmd.arg("--verbose");
    }

    if rebuild_std {
        cmd.arg("-Zbuild-std=core");
    }

    Ok(())
}
