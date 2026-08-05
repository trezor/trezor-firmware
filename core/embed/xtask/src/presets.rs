use std::collections::BTreeMap;
use std::fs;
use std::path::Path;

use anyhow::{Context, Result, bail};
use serde::Deserialize;

use crate::args::{BuildArgs, Model, Project};
use crate::helpers;
use crate::options::BuildOptions;

#[derive(Debug, Clone, Deserialize, Default)]
#[serde(deny_unknown_fields)]
pub struct PresetFilter {
    pub model: Option<Vec<Model>>,
    pub project: Option<Vec<Project>>,
    pub emulator: Option<bool>,
}

impl PresetFilter {
    fn matches(&self, args: &BuildArgs) -> bool {
        self.model
            .as_ref()
            .is_none_or(|models| models.contains(&args.model))
            && self
                .project
                .as_ref()
                .is_none_or(|projects| projects.contains(&args.project))
            && self
                .emulator
                .is_none_or(|emulator| emulator == args.emulator)
    }
}

#[derive(Deserialize, Debug, Clone, Default)]
#[serde(deny_unknown_fields)]
pub struct Preset {
    #[serde(rename = "when", default)]
    pub filter: PresetFilter,

    #[serde(flatten)]
    pub options: BuildOptions,
}

#[derive(Deserialize, Debug, Default)]
#[serde(transparent)]
pub struct PresetsFile {
    pub presets: BTreeMap<String, Vec<Preset>>,
}

impl PresetsFile {
    fn load(path: &Path) -> Result<Self> {
        let content = fs::read_to_string(&path)
            .with_context(|| format!("Failed to read build presets: {}", path.display()))?;
        toml::from_str(&content)
            .with_context(|| format!("Failed to parse build presets: {}", path.display()))
    }

    fn load_optional(path: &Path) -> Result<Self> {
        match Self::load(path) {
            Ok(presets) => Ok(presets),
            Err(error)
                if error
                    .downcast_ref::<std::io::Error>()
                    .is_some_and(|error| error.kind() == std::io::ErrorKind::NotFound) =>
            {
                Ok(Self::default())
            }
            Err(error) => Err(error),
        }
    }

    fn resolve(&self, name: &str, args: &BuildArgs) -> Option<BuildOptions> {
        let presets = self.presets.get(name)?;

        let matching: Vec<&Preset> = presets
            .iter()
            .filter(|preset| preset.filter.matches(args))
            .collect();

        if matching.is_empty() {
            return None;
        }

        Some(
            matching
                .into_iter()
                .fold(BuildOptions::default(), |options, preset| {
                    options.overlay(preset.options.clone())
                }),
        )
    }
}

pub fn resolve(args: &BuildArgs) -> Result<BuildOptions> {
    let presets_dir = helpers::workspace_dir()?.join("xtask");
    let shared = PresetsFile::load(&presets_dir.join("presets.toml"))?;
    let user = PresetsFile::load_optional(&presets_dir.join("user-presets.toml"))?;

    resolve_sources(&shared, &user, args)
}

fn resolve_sources(
    shared: &PresetsFile,
    user: &PresetsFile,
    args: &BuildArgs,
) -> Result<BuildOptions> {
    let defaults = shared
        .resolve("defaults", args)
        .unwrap_or_default()
        .overlay(user.resolve("defaults", args).unwrap_or_default());

    let Some(name) = args.preset.as_deref() else {
        return Ok(defaults);
    };

    let shared_options = shared.resolve(name, args);
    let user_options = user.resolve(name, args);

    match (shared_options, user_options) {
        (None, None) if !shared.presets.contains_key(name) && !user.presets.contains_key(name) => {
            bail!("Unknown build preset '{name}'")
        }
        (None, None) => bail!("Build preset '{name}' has no entries matching this build"),
        (Some(options), None) | (None, Some(options)) => Ok(defaults.overlay(options)),
        (Some(shared), Some(user)) => Ok(defaults.overlay(shared.overlay(user))),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn args() -> BuildArgs {
        BuildArgs {
            project: Project::Firmware,
            model: Model::T3W1,
            emulator: true,
            preset: Some("test".to_string()),
            options: BuildOptions::default(),
        }
    }

    #[test]
    fn resolves_matching_presets_in_file_order() {
        let presets: PresetsFile = toml::from_str(
            r#"
                [[test]]
                when = { model = ["t3w1"], project = ["firmware"], emulator = true }
                pyopt = false
                frozen = true

                [[test]]
                when = { emulator = true }
                pyopt = true
                debug = true
                debug-link = false
            "#,
        )
        .unwrap();

        let options = presets.resolve("test", &args()).unwrap();
        assert_eq!(options.pyopt, Some(true));
        assert_eq!(options.debug, Some(true));
        assert_eq!(options.debug_link, Some(false));
        assert_eq!(options.frozen, Some(true));
    }

    #[test]
    fn rejects_unknown_preset() {
        let presets = PresetsFile::default();
        assert!(resolve_sources(&presets, &presets, &args()).is_err());
    }

    #[test]
    fn explicit_options_override_preset_options() {
        let presets: PresetsFile = toml::from_str(
            r#"
                [[test]]
                pyopt = false
            "#,
        )
        .unwrap();
        let cli_options = BuildOptions {
            pyopt: Some(true),
            ..BuildOptions::default()
        };

        let options = presets
            .resolve("test", &args())
            .unwrap()
            .overlay(cli_options);
        assert_eq!(options.pyopt, Some(true));
    }

    #[test]
    fn user_presets_override_shared_presets() {
        let shared: PresetsFile = toml::from_str(
            r#"
                [[test]]
                pyopt = false
            "#,
        )
        .unwrap();
        let user: PresetsFile = toml::from_str(
            r#"
                [[test]]
                pyopt = true
                timings = true
            "#,
        )
        .unwrap();

        let options = resolve_sources(&shared, &user, &args()).unwrap();
        assert_eq!(options.pyopt, Some(true));
        assert_eq!(options.timings, Some(true));
    }

    #[test]
    fn user_presets_can_define_local_only_presets() {
        let user: PresetsFile = toml::from_str(
            r#"
                [[local]]
                benchmark = true
            "#,
        )
        .unwrap();

        let mut build_args = args();
        build_args.preset = Some("local".to_string());

        let options = resolve_sources(&PresetsFile::default(), &user, &build_args).unwrap();
        assert_eq!(options.benchmark, Some(true));
    }

    #[test]
    fn missing_optional_presets_file_is_empty() {
        let directory = tempfile::tempdir().unwrap();
        let presets = PresetsFile::load_optional(&directory.path().join("missing.toml")).unwrap();
        assert!(presets.presets.is_empty());
    }

    #[test]
    fn applies_defaults_without_an_explicit_preset() {
        let presets: PresetsFile = toml::from_str(
            r#"
                [[defaults]]
                when = { emulator = true }
                debug = true
                pyopt = false
            "#,
        )
        .unwrap();
        let mut build_args = args();
        build_args.preset = None;

        let options = resolve_sources(&presets, &PresetsFile::default(), &build_args).unwrap();
        assert_eq!(options.debug, Some(true));
        assert_eq!(options.pyopt, Some(false));
    }

    #[test]
    fn named_presets_override_defaults() {
        let presets: PresetsFile = toml::from_str(
            r#"
                [[defaults]]
                pyopt = true

                [[test]]
                pyopt = false
            "#,
        )
        .unwrap();

        let options = resolve_sources(&presets, &PresetsFile::default(), &args()).unwrap();
        assert_eq!(options.pyopt, Some(false));
    }

    #[test]
    fn user_defaults_override_shared_defaults() {
        let shared: PresetsFile = toml::from_str(
            r#"
                [[defaults]]
                pyopt = true
            "#,
        )
        .unwrap();
        let user: PresetsFile = toml::from_str(
            r#"
                [[defaults]]
                pyopt = false
            "#,
        )
        .unwrap();
        let mut build_args = args();
        build_args.preset = None;

        let options = resolve_sources(&shared, &user, &build_args).unwrap();
        assert_eq!(options.pyopt, Some(false));
    }
}
