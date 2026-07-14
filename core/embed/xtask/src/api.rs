use anyhow::{Context, bail, ensure};
use std::fs;
use tempfile::NamedTempFile;

use crate::{args::BuildArgs, cargo, helpers, model::Model};

const SUPPORTED_MODELS: &[Model] = &[Model::T3W1];
const BINDINGS_FILE: &str = "trezor-api.rs";

pub fn bindings(check_only: bool) -> anyhow::Result<()> {
    if check_only {
        println!("Checking API bindings...");
    } else {
        println!("Generating API bindings...");
    }

    for model in SUPPORTED_MODELS {
        let mut reference_file: Option<NamedTempFile> = None;

        for emulator in [true, false] {
            println!("Building for {:?} (emulator: {})...", model, emulator);

            let args = BuildArgs {
                project: crate::args::Project::Firmware,
                model: *model,
                emulator,
                apps: true,
                ..Default::default()
            };

            let profile_dir = helpers::profile_dir(&args)?;
            cargo::build(args)?;

            let bindings_path = profile_dir.join(BINDINGS_FILE);
            ensure!(
                bindings_path.exists(),
                "Expected bindings file not found at {:?}",
                bindings_path
            );

            match &reference_file {
                None => {
                    let tmp = NamedTempFile::new()
                        .context("Failed to create temporary reference file")?;
                    fs::copy(&bindings_path, tmp.path()).with_context(|| {
                        format!(
                            "Failed to copy bindings to temp file from {:?}",
                            bindings_path
                        )
                    })?;
                    reference_file = Some(tmp);
                }
                Some(reference) => {
                    let ref_content =
                        fs::read(reference.path()).context("Failed to read reference temp file")?;
                    let cur_content = fs::read(&bindings_path).with_context(|| {
                        format!("Failed to read bindings file at {:?}", bindings_path)
                    })?;

                    if ref_content != cur_content {
                        let ref_str = String::from_utf8_lossy(&ref_content);
                        let cur_str = String::from_utf8_lossy(&cur_content);

                        println!("--- Emulator bindings");
                        println!("+++ Non-emulator bindings");
                        for (i, (ref_line, cur_line)) in
                            ref_str.lines().zip(cur_str.lines()).enumerate()
                        {
                            if ref_line != cur_line {
                                println!("Line {}:", i + 1);
                                println!("-{}", ref_line);
                                println!("+{}", cur_line);
                            }
                        }
                        let ref_lines: Vec<_> = ref_str.lines().collect();
                        let cur_lines: Vec<_> = cur_str.lines().collect();
                        let min_len = ref_lines.len().min(cur_lines.len());
                        for (i, line) in cur_lines[min_len..].iter().enumerate() {
                            println!("Line {}: +{}", min_len + i + 1, line);
                        }
                        for (i, line) in ref_lines[min_len..].iter().enumerate() {
                            println!("Line {}: -{}", min_len + i + 1, line);
                        }

                        bail!(
                            "Bindings file for {:?} differs between emulator and non-emulator builds",
                            model
                        );
                    }
                }
            }
        }

        // Compare with the committed bindings in the SDK
        let sdk_bindings_path = helpers::workspace_dir()?
            .join("../../sdk/crates/trezor-app-sdk/src/low_level_api/ffi.rs");

        let generated_content = fs::read(reference_file.as_ref().unwrap().path())
            .context("Failed to read generated bindings temp file")?;

        ensure!(
            sdk_bindings_path.exists(),
            "SDK bindings file not found at {:?}",
            sdk_bindings_path
        );

        let sdk_content = fs::read(&sdk_bindings_path)
            .with_context(|| format!("Failed to read SDK bindings at {:?}", sdk_bindings_path))?;

        if generated_content != sdk_content {
            // Print a simple diff showing line differences
            let generated_str = String::from_utf8_lossy(&generated_content);
            let sdk_str = String::from_utf8_lossy(&sdk_content);

            println!("--- SDK bindings (committed)");
            println!("+++ Generated bindings");
            for (i, (gen_line, sdk_line)) in generated_str.lines().zip(sdk_str.lines()).enumerate()
            {
                if gen_line != sdk_line {
                    println!("Line {}: ", i + 1);
                    println!("-{}", sdk_line);
                    println!("+{}", gen_line);
                }
            }
            // Print extra lines if lengths differ
            let gen_lines: Vec<_> = generated_str.lines().collect();
            let sdk_lines: Vec<_> = sdk_str.lines().collect();
            let min_len = gen_lines.len().min(sdk_lines.len());
            for (i, line) in gen_lines[min_len..].iter().enumerate() {
                println!("Line {}: +{}", min_len + i + 1, line);
            }
            for (i, line) in sdk_lines[min_len..].iter().enumerate() {
                println!("Line {}: -{}", min_len + i + 1, line);
            }

            if check_only {
                // Optionally save the generated bindings next to the SDK file for inspection
                let save_path = sdk_bindings_path.with_extension("rs.generated");
                fs::write(&save_path, &generated_content).with_context(|| {
                    format!("Failed to save generated bindings at {:?}", save_path)
                })?;
                println!("Generated bindings saved for inspection at {:?}", save_path);
                bail!(
                    "SDK bindings for {:?} are outdated. Please run `make api` to update them.",
                    model
                );
            } else {
                fs::write(&sdk_bindings_path, &generated_content).with_context(|| {
                    format!("Failed to update SDK bindings at {:?}", sdk_bindings_path)
                })?;
                bail!(
                    "SDK bindings for {:?} were outdated and have been updated at {:?}. \
                     Please commit the updated file.",
                    model,
                    sdk_bindings_path
                );
            }
        }
    }

    println!("All API bindings are consistent and up to date.");
    Ok(())
}
