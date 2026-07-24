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
pub struct ProfileFilter {
    pub model: Option<Vec<Model>>,
    pub project: Option<Vec<Project>>,
    pub emulator: Option<bool>,
}

impl ProfileFilter {
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
pub struct Profile {
    #[serde(rename = "when", default)]
    pub filter: ProfileFilter,

    #[serde(flatten)]
    pub options: BuildOptions,
}

#[derive(Deserialize, Debug, Default)]
#[serde(transparent)]
pub struct ProfilesFile {
    pub profiles: BTreeMap<String, Vec<Profile>>,
}

impl ProfilesFile {
    fn load(path: &Path) -> Result<Self> {
        let content = fs::read_to_string(&path)
            .with_context(|| format!("Failed to read build profiles: {}", path.display()))?;
        toml::from_str(&content)
            .with_context(|| format!("Failed to parse build profiles: {}", path.display()))
    }

    fn load_optional(path: &Path) -> Result<Self> {
        match Self::load(path) {
            Ok(profiles) => Ok(profiles),
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
        let profiles = self.profiles.get(name)?;

        let matching: Vec<&Profile> = profiles
            .iter()
            .filter(|profile| profile.filter.matches(args))
            .collect();

        if matching.is_empty() {
            return None;
        }

        Some(
            matching
                .into_iter()
                .fold(BuildOptions::default(), |options, profile| {
                    options.overlay(profile.options.clone())
                }),
        )
    }
}

pub fn resolve(args: &BuildArgs) -> Result<BuildOptions> {
    let Some(name) = args.profile.as_deref() else {
        return Ok(BuildOptions::default());
    };

    let profiles_dir = helpers::workspace_dir()?.join("xtask/tf-tools");
    let shared = ProfilesFile::load(&profiles_dir.join("profiles.toml"))?;
    let user = ProfilesFile::load_optional(&profiles_dir.join("user-profiles.toml"))?;

    resolve_sources(&shared, &user, name, args)
}

fn resolve_sources(
    shared: &ProfilesFile,
    user: &ProfilesFile,
    name: &str,
    args: &BuildArgs,
) -> Result<BuildOptions> {
    let shared_options = shared.resolve(name, args);
    let user_options = user.resolve(name, args);

    match (shared_options, user_options) {
        (None, None)
            if !shared.profiles.contains_key(name) && !user.profiles.contains_key(name) =>
        {
            bail!("Unknown build profile '{name}'")
        }
        (None, None) => bail!("Build profile '{name}' has no entries matching this build"),
        (Some(options), None) | (None, Some(options)) => Ok(options),
        (Some(shared), Some(user)) => Ok(shared.overlay(user)),
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
            profile: Some("test".to_string()),
            options: BuildOptions::default(),
        }
    }

    #[test]
    fn resolves_matching_profiles_in_file_order() {
        let profiles: ProfilesFile = toml::from_str(
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

        let options = profiles.resolve("test", &args()).unwrap();
        assert_eq!(options.pyopt, Some(true));
        assert_eq!(options.debug, Some(true));
        assert_eq!(options.debug_link, Some(false));
        assert_eq!(options.frozen, Some(true));
    }

    #[test]
    fn rejects_unknown_profile() {
        let profiles = ProfilesFile::default();
        assert!(resolve_sources(&profiles, &profiles, "missing", &args()).is_err());
    }

    #[test]
    fn explicit_options_override_profile_options() {
        let profiles: ProfilesFile = toml::from_str(
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

        let options = profiles
            .resolve("test", &args())
            .unwrap()
            .overlay(cli_options);
        assert_eq!(options.pyopt, Some(true));
    }

    #[test]
    fn user_profiles_override_shared_profiles() {
        let shared: ProfilesFile = toml::from_str(
            r#"
                [[test]]
                pyopt = false
            "#,
        )
        .unwrap();
        let user: ProfilesFile = toml::from_str(
            r#"
                [[test]]
                pyopt = true
                timings = true
            "#,
        )
        .unwrap();

        let options = resolve_sources(&shared, &user, "test", &args()).unwrap();
        assert_eq!(options.pyopt, Some(true));
        assert_eq!(options.timings, Some(true));
    }

    #[test]
    fn user_profiles_can_define_local_only_profiles() {
        let user: ProfilesFile = toml::from_str(
            r#"
                [[local]]
                benchmark = true
            "#,
        )
        .unwrap();

        let options = resolve_sources(&ProfilesFile::default(), &user, "local", &args()).unwrap();
        assert_eq!(options.benchmark, Some(true));
    }

    #[test]
    fn missing_optional_profiles_file_is_empty() {
        let directory = tempfile::tempdir().unwrap();
        let profiles = ProfilesFile::load_optional(&directory.path().join("missing.toml")).unwrap();
        assert!(profiles.profiles.is_empty());
    }
}
