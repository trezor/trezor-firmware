use std::fs;

use anyhow::{Context, Result};
use serde::Serialize;

use crate::args::{BuildArgs, Project, RaConfigArgs};
use crate::features::resolve_features;
use crate::options::ResolvedBuildArgs;

#[derive(Serialize)]
struct RustAnalyzerToml {
    cargo: RustAnalyzerCargoConfig,
    #[serde(skip_serializing_if = "Option::is_none")]
    check: Option<RustAnalyzerCheckConfig>,
}

#[derive(Serialize)]
struct RustAnalyzerCargoConfig {
    features: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    target: Option<&'static str>,
    #[serde(rename = "allTargets")]
    all_targets: bool,
}

#[derive(Serialize)]
struct RustAnalyzerCheckConfig {
    #[serde(rename = "extraArgs")]
    extra_args: [&'static str; 4],
}

struct ResolvedRustAnalyzerConfig {
    features: Vec<String>,
    target: Option<&'static str>,
}

fn resolve_config(args: &RaConfigArgs) -> Result<ResolvedRustAnalyzerConfig> {
    let projects = [
        Project::Bootloader,
        Project::BootloaderCi,
        Project::Boardloader,
        Project::Firmware,
        Project::Prodtest,
        Project::Kernel,
        Project::Secmon,
    ];

    let mut features = Vec::new();
    let mut target = None;

    for project in projects {
        let build_args = BuildArgs {
            project,
            model: args.model,
            emulator: args.emulator,
            preset: args.preset.clone(),
            options: args.options.clone(),
        };

        let resolved_args = ResolvedBuildArgs::from_build_args(&build_args)?;
        let resolved_features = resolve_features(&resolved_args)?;
        target = target.or(resolved_features.target_triple);

        features.extend(resolved_features.features.into_iter().map(|feature| {
            if feature.contains('/') {
                feature
            } else {
                format!("{}/{feature}", project.package_name())
            }
        }));
    }

    features.sort();
    features.dedup();

    Ok(ResolvedRustAnalyzerConfig { features, target })
}

pub fn generate(args: RaConfigArgs) -> Result<()> {
    let ResolvedRustAnalyzerConfig { features, target } = resolve_config(&args)?;

    let config = RustAnalyzerToml {
        cargo: RustAnalyzerCargoConfig {
            features,
            target,
            all_targets: false,
        },
        check: (!args.emulator).then_some(RustAnalyzerCheckConfig {
            extra_args: ["--exclude", "xtask", "--exclude", "xbuild"],
        }),
    };

    let output = toml::to_string_pretty(&config)?;
    if let Some(path) = args.file {
        fs::write(&path, output)
            .with_context(|| format!("Failed to write configuration to {}", path.display()))?;
    } else {
        println!("{output}");
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::Model;
    use crate::options::BuildOptions;

    fn args(emulator: bool) -> RaConfigArgs {
        RaConfigArgs {
            model: Model::T3W1,
            file: None,
            emulator,
            preset: None,
            options: BuildOptions::default(),
        }
    }

    #[test]
    fn resolves_target_and_sorted_features() {
        let hardware = resolve_config(&args(false)).unwrap();
        assert_eq!(hardware.target, Some("thumbv8m.main-none-eabihf"));
        assert!(hardware.features.is_sorted());
        assert!(hardware.features.windows(2).all(|pair| pair[0] != pair[1]));
        assert!(hardware.features.contains(&"models/model_t3w1".into()));

        let emulator = resolve_config(&args(true)).unwrap();
        assert_eq!(emulator.target, None);
        assert!(emulator.features.contains(&"firmware/emulator".into()));
    }

    #[test]
    fn explicit_options_override_preset() {
        let config = RaConfigArgs {
            preset: Some("test".into()),
            options: BuildOptions {
                debug_link: Some(false),
                ..BuildOptions::default()
            },
            ..args(true)
        };

        let resolved = resolve_config(&config).unwrap();
        assert!(
            resolved
                .features
                .contains(&"firmware/disable_animation".into())
        );
        assert!(!resolved.features.contains(&"firmware/debuglink".into()));
    }

    #[test]
    fn writes_configuration_to_file() {
        let output = tempfile::NamedTempFile::new().unwrap();
        let config = RaConfigArgs {
            file: Some(output.path().into()),
            ..args(true)
        };

        generate(config).unwrap();

        let contents = fs::read_to_string(output.path()).unwrap();
        let parsed = contents.parse::<toml::Table>().unwrap();
        assert!(parsed.contains_key("cargo"));
    }
}
