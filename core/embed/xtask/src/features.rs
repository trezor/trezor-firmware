use std::io::IsTerminal;
use std::{env, io, process};

use anyhow::{Result, bail};

use crate::args::ConsoleType;
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

    // The WARD service channel and coin support are independent options, but not every
    // combination means anything: WARD's message handlers are registered only when the firmware
    // is not bitcoin-only, so a bitcoin-only build with the service channel would carry a
    // dedicated interface with nothing behind it to serve. Rejected here rather than coupled to
    // `universal_fw`, which would make the service channel un-selectable on its own.
    if args.btc_only && args.enable_ward_service_channel {
        bail!("ward_service_channel needs WARD, which is not built in bitcoin-only firmware");
    }

    // WHICH TRANSPORT THE INTERFACE SPEAKS IS A SEPARATE QUESTION FROM WHETHER IT EXISTS, and the
    // default answer is codec v1 on every build. The THP service path is kept compiling behind
    // this option rather than deleted, so the choice can be revisited without recovering the work
    // from history -- but it cannot be selected without an interface to serve.
    if args.ward_service_thp && !args.enable_ward_service_channel {
        bail!(
            "ward_service_thp needs --enable-ward-service-channel: there is no interface to serve"
        );
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

    // Checked once the project is known: whether a build pays for the WARD interface depends on
    // whether THIS project registers it. The bootloader, prodtest and secmon do not map the
    // option at all and must not be charged an endpoint for an interface they never bring up.
    check_usb_endpoint_budget(
        args,
        project_config
            .options
            .enable_ward_service_channel
            .is_some(),
    )?;

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
    cmd.env("SCM_REVISION", helpers::git_revision()?);

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

    if args.xbuild_trace {
        // Cargo does not pass its own verbosity on to build scripts, so
        // `xbuild` reads the request from the environment instead.
        cmd.env("XBUILD_TRACE", "1");
        // `-vv`, not `-v`: Cargo relays build script output only at the second
        // verbosity level, and would otherwise discard what `xbuild` logs.
        cmd.arg("-vv");
    } else if args.verbose {
        cmd.arg("--verbose");
    }

    if rebuild_std {
        cmd.arg("-Zbuild-std=core");
    }

    forward_color_choice(cmd);

    Ok(())
}

/// Number of endpoint numbers the USB device core is brought up with, mirroring
/// `USBD_MAX_NUM_ENDPOINTS` in `core/embed/io/usb/stm32/usbd_conf.h`. Endpoint 0 is the control
/// endpoint, so `USB_MAX_ENDPOINTS - 1` data endpoint numbers are available.
///
/// Duplicated from C on purpose: the two cannot be shared, and the point of this check is to fail
/// at build-option resolution -- with the offending options named -- rather than at link time or,
/// worse, at runtime. Keep the two in step.
const USB_MAX_ENDPOINTS: u32 = 6;

/// Refuse a build whose USB configuration wants more endpoints than the device core has.
///
/// `usb_configure` (`core/embed/io/usb/usb_config.c`) hands out interface numbers in registration
/// order and derives every endpoint number from one: `ep_in = ep_out = 0x01 + iface_num`, and vcp
/// additionally `ep_cmd = 0x01 + iface_num + 1`. So the highest endpoint number a configuration
/// uses is `interface count`, and the budget is exhausted at `USB_MAX_ENDPOINTS - 1`.
///
/// WHY THIS IS CHECKED HERE AND NOT ONLY IN C. The class-level guards do reject an out-of-range
/// endpoint now, but they reject it at boot, on the device, by refusing to bring USB up at all --
/// a build that flashes and then cannot talk. Naming the two options that collide, at the moment
/// they are combined, is the answer that can actually be acted on.
///
/// Skipped for the emulator, which has no endpoints: interfaces there are UDP ports.
fn check_usb_endpoint_budget(
    args: &ResolvedBuildArgs,
    project_maps_ward_channel: bool,
) -> Result<()> {
    if args.emulator {
        return Ok(());
    }

    // The wire interface is intrinsic rather than option-driven, so it is not read from args.
    let mut interfaces = 1; // wire
    if args.debug_link {
        interfaces += 1;
    }
    if !args.btc_only {
        interfaces += 1; // webauthn, via universal_fw
    }
    if args.dbg_console == ConsoleType::Vcp {
        interfaces += 2; // vcp takes a control and a data interface
    }
    if project_maps_ward_channel && args.enable_ward_service_channel {
        interfaces += 1;
    }

    if interfaces > USB_MAX_ENDPOINTS - 1 {
        bail!(
            "USB configuration needs {} endpoints but the device core has {}; drop one \
             interface-bearing option. THE WARD SERVICE CHANNEL IS OFF BY DEFAULT and this build \
             asked for it, so dropping --enable-ward-service-channel costs no debugging \
             facility. Otherwise drop --dbg-console vcp (two interfaces) or --debug-link.",
            interfaces,
            USB_MAX_ENDPOINTS - 1
        );
    }

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
    fn rejects_a_usb_configuration_that_overruns_the_endpoint_budget() {
        // wire(1) + debug(1) + webauthn(1) + vcp(2) + ward(1) = 6 interfaces, so the highest
        // endpoint number is 6 and the core only has 0..5. This is the one combination the
        // existing options can reach, and it used to build and then fail silently on the device.
        let args = ResolvedBuildArgs {
            debug_link: true,
            dbg_console: ConsoleType::Vcp,
            enable_ward_service_channel: true,
            ..ResolvedBuildArgs::default()
        };

        let error = resolve_features(&args).unwrap_err();
        assert!(
            error.to_string().contains("endpoints"),
            "unexpected error: {error}"
        );
    }

    #[test]
    fn rejects_a_thp_service_transport_without_a_service_interface() {
        // The transport option says WHAT the interface speaks, so it needs one to speak on.
        let args = ResolvedBuildArgs {
            ward_service_thp: true,
            ..ResolvedBuildArgs::default()
        };

        let error = resolve_features(&args).unwrap_err();
        assert!(
            error.to_string().contains("ward_service_thp"),
            "unexpected error: {error}"
        );
    }

    #[test]
    fn accepts_the_service_channel_speaking_thp_when_asked_for() {
        // The default is codec v1 on the service interface; this is the opt-in that keeps the THP
        // service path buildable, and it must remain selectable.
        let args = ResolvedBuildArgs {
            enable_ward_service_channel: true,
            ward_service_thp: true,
            ..ResolvedBuildArgs::default()
        };

        assert!(resolve_features(&args).is_ok());
    }

    #[test]
    fn accepts_the_service_channel_without_a_vcp_console() {
        // The same build minus the vcp console is 4 interfaces, which fits -- so the check must
        // not turn into a blanket refusal of the service channel.
        let args = ResolvedBuildArgs {
            debug_link: true,
            enable_ward_service_channel: true,
            ..ResolvedBuildArgs::default()
        };

        assert!(check_usb_endpoint_budget(&args, true).is_ok());
    }

    #[test]
    fn ignores_the_endpoint_budget_for_the_emulator() {
        // Emulator interfaces are UDP ports, so there is no budget to overrun.
        let args = ResolvedBuildArgs {
            emulator: true,
            debug_link: true,
            dbg_console: ConsoleType::Vcp,
            enable_ward_service_channel: true,
            ..ResolvedBuildArgs::default()
        };

        assert!(check_usb_endpoint_budget(&args, true).is_ok());
    }

    #[test]
    fn does_not_build_the_ward_service_channel_unless_it_is_asked_for() {
        // THE DEFAULT IS OFF: a firmware nobody asked serves WARD over the ordinary connection,
        // and the dedicated interface costs a USB endpoint nobody gets back. This is what stops
        // the polarity being flipped by accident.
        let features = resolve_features(&ResolvedBuildArgs::default())
            .unwrap()
            .features;
        assert!(!features.contains(&"ward_service_channel".to_string()));

        let args = ResolvedBuildArgs {
            enable_ward_service_channel: true,
            ..ResolvedBuildArgs::default()
        };
        let features = resolve_features(&args).unwrap().features;
        assert!(features.contains(&"ward_service_channel".to_string()));
    }

    #[test]
    fn the_kernel_maps_the_service_channel_too() {
        // Two project.toml tables have to agree, and the default model has a secure monitor, so
        // its firmware really is built through both.
        let args = ResolvedBuildArgs {
            project: Project::Kernel,
            enable_ward_service_channel: true,
            ..ResolvedBuildArgs::default()
        };

        let features = resolve_features(&args).unwrap().features;
        assert!(features.contains(&"ward_service_channel".to_string()));
    }

    #[test]
    fn rejects_the_service_channel_on_a_bitcoin_only_build() {
        // WARD's handlers are registered only on a universal build, so the interface would carry
        // nothing behind it. REFUSED rather than resolved off silently: the channel is opt-in, so
        // reaching here means the caller asked for both in the same breath.
        let args = ResolvedBuildArgs {
            btc_only: true,
            enable_ward_service_channel: true,
            ..ResolvedBuildArgs::default()
        };

        let error = resolve_features(&args).unwrap_err();
        assert!(
            error.to_string().contains("bitcoin-only"),
            "unexpected error: {error}"
        );
    }

    #[test]
    fn a_project_that_never_registers_the_interface_is_not_charged_for_it() {
        // The bootloader maps neither the option nor the interface, and already sits at exactly
        // the budget with vcp + debug-link. Asking for WARD on a project that ignores the option
        // must not cost an endpoint, or `PYOPT=0 WARD_SERVICE_CHANNEL=1` would refuse to build a
        // project that cannot serve WARD at all.
        let args = ResolvedBuildArgs {
            project: Project::Bootloader,
            debug_link: true,
            dbg_console: ConsoleType::Vcp,
            enable_ward_service_channel: true,
            ..ResolvedBuildArgs::default()
        };

        assert!(check_usb_endpoint_budget(&args, false).is_ok());
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
