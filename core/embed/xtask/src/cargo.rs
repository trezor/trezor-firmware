use std::process;

use anyhow::{Context, Result, ensure};
use owo_colors::OwoColorize;

use crate::args::{BuildArgs, Project, TestArgs};
use crate::options::ResolvedBuildArgs;
use crate::{artifacts, features, helpers, memusage, postbuild, pq, prebuild};

pub fn build(args: BuildArgs) -> Result<()> {
    let resolved_args = ResolvedBuildArgs::from_build_args(&args)?;

    // A Merkle-tree image is not installable on its own: its manifest has to
    // fold to the firmware_root of a signed boot header. So on a tree model,
    // building one means building a RELEASE -- variants, the bootloader header
    // they fold into, and the signature over it.
    //
    // Prodtest counts. It is its own project rather than a firmware variant,
    // but it is a leaf of the same tree, and built on its own it would emit the
    // same uninstallable manifest template (zero code_hash, no proof).
    if matches!(args.project, Project::Firmware | Project::Prodtest) && pq::applies(&resolved_args)?
    {
        let variant = pq::selected_variant(&resolved_args);
        // A CUSTOM build never cuts a tree: its leaf is code-independent, so it
        // folds into the one founder-signed custom slot of the COMMITTED
        // release. A fresh single-variant root would be self-consistent and
        // useless -- no field device carries it -- and it is impossible with
        // production keys anyway, so dev takes the same path.
        if variant == pq::Variant::Custom {
            return pq::build_presigned(&resolved_args);
        }
        return pq::build_release(&resolved_args, &[variant], args.bootloader);
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

/// Build a single project, as a plain build with no release orchestration.
/// [`pq::build_release`] calls this per variant, which is also why it must not
/// route back through [`build`].
pub fn build_project(args: ResolvedBuildArgs) -> Result<()> {
    build_impl(args, false)
}

fn build_impl(args: ResolvedBuildArgs, is_dependency: bool) -> Result<()> {
    if !args.emulator {
        // Recursively build dependencies (Firmware -> Kernel -> Secmon)
        if let Some(dependency) = args.project.dependency(args.model)? {
            // A presigned CUSTOM build embeds the COMMITTED secmon -- the one
            // the signed custom leaf covers -- so building one is not just
            // wasted work: it would leave artifacts/<MODEL>/secmon.bin holding a
            // binary that is NOT the one inside the firmware being built, which
            // is the sort of near-miss that gets promoted by mistake.
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

        // Sign the binary except for those that don't have headers. Firmware
        // built with the Merkle-tree layout is skipped too: its per-module
        // code hashes are filled into the manifest below, with the firmware_root
        // folded into the bootloader header by the tree signer.
        let is_tree = model_config.has_feature("pq_secure_boot");
        let skip_legacy_sign = matches!(args.project, Project::Boardloader | Project::Kernel)
            || (matches!(
                args.project,
                Project::Firmware | Project::Secmon | Project::Prodtest
            ) && is_tree);
        if !skip_legacy_sign {
            postbuild::sign_binary(&bin, args.project, &model_config, use_dev_keys)?;
        }

        // Merkle-tree firmware: the manifest code_hashes are filled at SIGN time
        // (fill-at-sign), NOT here. firmware_pq_sign.py computes each entry's
        // code_hash at the chosen chunk_size in the same step that folds the
        // variant leaves and signs -- so the authenticity data is produced in one
        // place. The build emits only the manifest TEMPLATE (manifest_header.S:
        // magic/variant/module_type/addr/size + a default chunk_size, code_hash
        // left zero). A raw `xtask build firmware` therefore yields an unfilled
        // template (not bootable on its own -- its leaf must fold into the
        // bootloader's signed firmware_root); `xtask build firmware` / `xtask
        // release` (build -> sign)
        // produces the filled, dev-signed bundle.

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
