use std::io::IsTerminal;
use std::{env, io, process};

use anyhow::{Result, bail};

use crate::options::ResolvedBuildArgs;
use crate::{config, helpers};

#[derive(Debug)]
pub struct ResolvedBuildFeatures {
    pub features: Vec<String>,
    pub target_triple: Option<&'static str>,
    pub board_header: String,
}

/// Resolves cargo features and target triple from the provided build
/// arguments.
///
/// Option-dependent features come from the `[build-options]` table of the
/// project's project.toml; board- and model-intrinsic features come from the
/// model/board TOML configs filtered by the project's `uses` list. Only
/// features tied to build mechanics (model selection, emulator, asan) are
/// added directly here.
pub fn resolve_features(args: &ResolvedBuildArgs) -> Result<ResolvedBuildFeatures> {
    if args.production {
        if args.storage_insecure_testing_mode {
            bail!("storage_insecure_testing_mode cannot be used in production builds");
        }
        if args.disable_optiga {
            bail!("disable_optiga cannot be used in production builds");
        }
        if args.disable_tropic {
            bail!("disable_tropic cannot be used in production builds");
        }
    }

    let mut features: Vec<String> = vec![args.model.feature_name()];

    if args.emulator {
        features.push("emulator".into());

        if args.asan {
            features.push("asan".into());
        }
    }

    // Option-mapped features, validated against the target package's declared
    // features so an unsupported option fails here with the option named,
    // instead of as a cargo error.
    let project_config = config::ProjectConfig::load(args.project)?;
    let package = args.project.package_name(args.emulator);
    let package_features = config::package_features(package)?;
    for activated in project_config.options.resolve(args) {
        // Crate-qualified features ("io/foo") belong to dependencies and
        // can't be checked against this package's feature table.
        if !activated.feature.contains('/') && !package_features.contains(&activated.feature) {
            bail!(
                "option '{}' is not supported by this build: feature '{}' is not defined in package '{}'",
                activated.option,
                activated.feature,
                package
            );
        }
        features.push(activated.feature);
    }

    // Board and model-intrinsic features from TOML config. The emulator
    // emulates the same board it would build for on real hardware
    // (`default_board`, or an explicit `--board`); only the configuration
    // header differs.
    let model_config = args.model.config()?;

    let board_id = args
        .board
        .clone()
        .unwrap_or_else(|| model_config.default_board.clone());

    // Get the model/board features filtered by the project's `uses` list.
    let board_def = config::resolve_board_definition(
        &model_config,
        &board_id,
        &project_config,
        args.project,
        args.emulator,
    )?;

    // Remove features that are disabled by command-line flags.
    let mut board_features = board_def.features;
    if args.disable_optiga {
        board_features.retain(|f| f != "optiga");
    }
    if args.disable_tropic {
        board_features.retain(|f| f != "tropic");
    }
    features.extend(board_features);

    let target_triple = if args.emulator {
        None
    } else {
        Some(model_config.target_triple()?)
    };

    Ok(ResolvedBuildFeatures {
        features,
        target_triple,
        board_header: board_def.board_header,
    })
}

/// Resolves `CARGO_TERM_COLOR` to `always`/`never` for the spawned Cargo.
///
/// Build scripts see only pipes (Cargo captures their output), so `xtask` -
/// the last process attached to the real terminal - decides for them; `xbuild`
/// reads the result to color C compiler diagnostics. An explicit
/// `always`/`never` in the environment is left alone (the child inherits it).
fn forward_color_choice(cmd: &mut process::Command) {
    let explicit = env::var("CARGO_TERM_COLOR").is_ok_and(|v| v == "always" || v == "never");
    if explicit {
        return;
    }

    // https://no-color.org
    let color = if env::var_os("NO_COLOR").is_some_and(|v| !v.is_empty()) {
        "never"
    // https://bixense.com/clicolors
    } else if env::var_os("CLICOLOR_FORCE").is_some_and(|v| !v.is_empty() && v != "0") {
        "always"
    } else if io::stderr().is_terminal() {
        "always"
    } else {
        "never"
    };

    cmd.env("CARGO_TERM_COLOR", color);
}

/// Configures a cargo command with the appropriate arguments and features.
pub fn configure_cargo(args: &ResolvedBuildArgs, cmd: &mut process::Command) -> Result<()> {
    let resolved = resolve_features(args)?;
    let mut rebuild_std = false;

    cmd.args(["--package", args.project.package_name(args.emulator)]);
    cmd.args(["--features", &resolved.features.join(",")]);
    cmd.args(["--profile", args.cargo_profile_name()]);
    cmd.env("TREZOR_BOARD_HEADER", &resolved.board_header);

    if args.cargo_profile_name() == "release" {
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

    forward_color_choice(cmd);

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::args::Project;

    #[test]
    fn rejects_insecure_storage_in_production_builds() {
        let args = ResolvedBuildArgs {
            production: true,
            storage_insecure_testing_mode: true,
            ..ResolvedBuildArgs::default()
        };

        let error = resolve_features(&args).unwrap_err();
        assert!(error.to_string().contains("production"));
    }

    #[test]
    fn rejects_disable_optiga_in_production_builds() {
        let args = ResolvedBuildArgs {
            production: true,
            disable_optiga: true,
            ..ResolvedBuildArgs::default()
        };

        let error = resolve_features(&args).unwrap_err();
        assert!(error.to_string().contains("production"));
    }

    #[test]
    fn rejects_disable_tropic_in_production_builds() {
        let args = ResolvedBuildArgs {
            production: true,
            disable_tropic: true,
            ..ResolvedBuildArgs::default()
        };

        let error = resolve_features(&args).unwrap_err();
        assert!(error.to_string().contains("production"));
    }

    #[test]
    fn rejects_options_unsupported_by_the_package() {
        // `memperf` exists only in the unix (emulator) package. The firmware
        // project maps it, so a hardware build must reject the option up
        // front instead of failing later inside cargo.
        let args = ResolvedBuildArgs {
            frozen: true,
            pyopt: true,
            mem_perf: true,
            ..ResolvedBuildArgs::default()
        };

        let error = resolve_features(&args).unwrap_err();
        assert!(
            error
                .to_string()
                .contains("option 'mem-perf' is not supported"),
            "unexpected error: {error}"
        );
    }

    #[test]
    fn ignores_options_the_project_does_not_map() {
        // prodtest doesn't map `disable-animation` (the package has no such
        // feature), so the option is ignored like any other unmapped option.
        let args = ResolvedBuildArgs {
            project: Project::Prodtest,
            frozen: true,
            pyopt: true,
            disable_animation: true,
            ..ResolvedBuildArgs::default()
        };

        let features = resolve_features(&args).unwrap().features;
        assert!(!features.contains(&"disable_animation".to_string()));
    }
}
