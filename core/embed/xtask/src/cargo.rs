use std::process;

use anyhow::{Context, Result, ensure};
use owo_colors::OwoColorize;

use crate::args::{BuildArgs, Project, TestArgs};
use crate::options::ResolvedBuildArgs;
use crate::{artifacts, features, helpers, memusage, postbuild, pq, prebuild};

pub fn build(args: BuildArgs) -> Result<()> {
    let resolved_args = ResolvedBuildArgs::from_build_args(&args)?;

    // A bare bootloader build invalidates the published install set.
    if args.project == Project::Bootloader && pq::applies(&resolved_args)? {
        pq::invalidate_install_set(args.model)?;
    }

    // `--bootloader` picks an existing binary for a release to fold into, so
    // it means nothing when building the bootloader itself.
    ensure!(
        args.project != Project::Bootloader || args.bootloader == pq::BootloaderSource::Auto,
        "--bootloader says which existing bootloader a release folds into, so \
         it means nothing when BUILDING the bootloader.\n             \
         Drop it here; pass it to `xtask release` or `xtask build firmware` \
         instead."
    );

    // A Merkle-tree image is only installable next to a bootloader header that
    // commits to its root, so building one builds a release. Prodtest is a
    // leaf of the same tree.
    if matches!(args.project, Project::Firmware | Project::Prodtest) && pq::applies(&resolved_args)?
    {
        let variant = pq::selected_variant(&resolved_args);
        // A custom build folds into the committed release's custom slot; it
        // never cuts a tree.
        if variant == pq::Variant::Custom {
            return pq::build_presigned(&resolved_args);
        }
        // Standalone: sign inline with development keys.
        return pq::build_release(
            &resolved_args,
            &[variant],
            args.bootloader,
            pq::SignStage::Inline,
            // Signed in place; `tree/` belongs to `xtask release`.
            pq::Dest::Artifacts,
            // Not a ceremony: the signer's default sigmask.
            None,
        );
    }

    build_impl(resolved_args.clone(), false)?;

    if resolved_args.storage_insecure_testing_mode {
        println!(
            "{}",
            "STORAGE_INSECURE_TESTING_MODE enabled, DO NOT USE"
                .yellow()
                .bold()
        );
    }

    Ok(())
}

pub fn clippy(args: BuildArgs) -> Result<()> {
    let resolved_args = ResolvedBuildArgs::from_build_args(&args)?;
    run_cargo_subcommand("clippy", &resolved_args)
}

pub fn check(args: BuildArgs) -> Result<()> {
    let resolved_args = ResolvedBuildArgs::from_build_args(&args)?;
    run_cargo_subcommand("check", &resolved_args)
}

pub fn test(args: TestArgs) -> Result<()> {
    for package in &args.packages {
        let mut cmd = process::Command::new("cargo");

        if args.miri {
            cmd.arg("miri");
        }
        cmd.arg("test")
            .args(["--package", package])
            .args(["--features", "test"])
            .arg("--")
            .arg("--test-threads=1")
            .arg("--nocapture")
            .env("SCM_REVISION", helpers::git_revision()?)
            .current_dir(helpers::workspace_dir()?);

        println!("xtask: Running test on `{}`", &package);
        println!("{}", command_args_to_string(&cmd).bold().dimmed());

        let status = cmd.status().context("Failed to spawn `cargo test`")?;

        ensure!(
            status.success(),
            "`cargo test` failed with status: {status}"
        );
    }

    Ok(())
}

pub fn clean() -> Result<()> {
    let status = process::Command::new("cargo")
        .arg("clean")
        .current_dir(helpers::workspace_dir()?)
        .status()
        .context("Failed to spawn `cargo clean`")?;

    ensure!(
        status.success(),
        "`cargo clean` failed with status: {status}",
    );

    Ok(())
}

pub fn fmt() -> Result<()> {
    let status = process::Command::new("cargo")
        .arg("fmt")
        .current_dir(helpers::workspace_dir()?)
        .status()
        .context("Failed to spawn `cargo fmt`")?;

    ensure!(status.success(), "`cargo fmt` failed with status: {status}",);

    Ok(())
}

/// Build a single project with no release orchestration; called per variant
/// by [`pq::build_release`], so it must not route back through [`build`].
pub fn build_project(args: ResolvedBuildArgs) -> Result<()> {
    build_impl(args, false)
}

fn build_impl(args: ResolvedBuildArgs, is_dependency: bool) -> Result<()> {
    if !args.emulator {
        // Recursively build dependencies (Firmware -> Kernel -> Secmon)
        if let Some(dependency) = args.project.dependency(args.model)? {
            // A presigned custom build embeds the committed secmon; skip it.
            let embeds_committed_secmon =
                dependency == Project::Secmon && args.unsafe_fw && pq::applies(&args)?;
            if embeds_committed_secmon {
                println!(
                    "{}",
                    "xtask: skipping the secmon build -- a custom build embeds the committed one"
                        .dimmed()
                );
            } else {
                build_impl(
                    ResolvedBuildArgs {
                        project: dependency,
                        ..args.clone()
                    },
                    true,
                )?;
            }
        }
    }

    // Prebuild steps
    if matches!(args.project, Project::Firmware) {
        prebuild::update_templates()?;
        prebuild::update_translations()?;
    }

    // Build the project
    run_cargo_subcommand("build", &args)?;

    let elf = helpers::elf_path(&args)?;

    if !args.emulator {
        let use_dev_keys = args.bootloader_devel || !args.production;

        let model_config = args.model.config()?;

        // For hardware targets, we need to convert the ELF file into a raw
        // binary before signing it.
        let bin = postbuild::elf_to_bin(&elf, args.project, &model_config, use_dev_keys)?;

        // Sign the binary except for those that don't have headers. Merkle-tree
        // firmware is signed by the tree signer instead.
        let is_tree = model_config.has_feature("pq_secure_boot");
        let skip_legacy_sign = matches!(args.project, Project::Boardloader | Project::Kernel)
            || (matches!(
                args.project,
                Project::Firmware | Project::Secmon | Project::Prodtest
            ) && is_tree);
        if !skip_legacy_sign {
            postbuild::sign_binary(&bin, args.project, &model_config, use_dev_keys)?;
        }

        // Merkle-tree firmware: code_hashes are filled at sign time by
        // firmware_pq_sign.py; the build emits only the manifest template.

        if args.project == Project::Firmware {
            let firwmare_cc_json = bin.with_extension("cc.json");
            let kernel_cc_json = bin.with_file_name("kernel").with_extension("cc.json");
            let secmon_cc_json = bin.with_file_name("secmon").with_extension("cc.json");

            postbuild::merge_compile_commands(
                &[&secmon_cc_json, &kernel_cc_json, &firwmare_cc_json],
                &firwmare_cc_json,
            )?;
        }

        let is_kernel = matches!(args.project, Project::Kernel);
        let is_secmon = matches!(args.project, Project::Secmon);
        // Copy the final binary to the `pub` directory
        if !(is_kernel || (is_secmon && is_dependency)) {
            let version_file = helpers::get_version_file(args.project)?;
            let infix =
                (matches!(args.project, Project::Firmware) && args.btc_only).then_some("btconly");
            postbuild::publish_artifact(
                &bin,
                args.project,
                args.model,
                &version_file,
                None,
                infix,
            )?;
        }
    }

    // Copy build artifacts (ELF, map files) to the `artifacts` directory
    artifacts::collect_artifacts(&args, is_dependency)?;

    // Print memory usage
    if !args.emulator && !is_dependency {
        let mapfile = elf
            .with_file_name(args.project.binary_name())
            .with_extension("map");
        memusage::print_memusage(&mapfile)?;
    }

    Ok(())
}

fn run_cargo_subcommand(subcommand: &str, args: &ResolvedBuildArgs) -> Result<()> {
    let mut cmd = process::Command::new("cargo");

    cmd.arg(subcommand).current_dir(helpers::workspace_dir()?);

    features::configure_cargo(args, &mut cmd)
        .context(format!("Failed to construct {} command", subcommand))?;

    let project_name = format!("{:?}", args.project).to_lowercase();
    println!("xtask: Running {} on `{}`", subcommand, project_name);
    println!("{}", command_args_to_string(&cmd).bold().dimmed());

    let status = cmd
        .status()
        .context(format!("Failed to spawn `cargo {}`", subcommand))?;

    ensure!(
        status.success(),
        "`cargo {subcommand}` failed with status: {status}"
    );

    Ok(())
}

fn command_args_to_string(cmd: &process::Command) -> String {
    let mut parts = vec![cmd.get_program().to_string_lossy().into_owned()];
    parts.extend(cmd.get_args().map(|arg| arg.to_string_lossy().into_owned()));
    parts.join(" ")
}
