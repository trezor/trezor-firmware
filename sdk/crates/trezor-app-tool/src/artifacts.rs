//! Functions for publishing and retrieving artifacts from the artifacts directory.

use crate::helpers;
use anyhow::{Context, Ok, Result};
use std::path::{Path, PathBuf};

/// Publishes the given `file` as an artifact with the specified `name`.
pub fn publish_artifact(source_path: &Path, artifact_name: &str) -> Result<PathBuf> {
    let artifact_path = helpers::artifacts_dir()?.join(artifact_name);

    std::fs::copy(source_path, &artifact_path).with_context(|| {
        format!(
            "Failed to copy `{}` to `{}`",
            source_path.display(),
            artifact_path.display()
        )
    })?;

    Ok(artifact_path)
}

/// Returns the files from the artifacts directory with the given extension,
/// sorted to keep the order deterministic.
pub fn artifact_with_ext(extension: &str) -> Result<Vec<PathBuf>> {
    let dir = helpers::artifacts_dir()?;
    let mut apps: Vec<PathBuf> = std::fs::read_dir(&dir)
        .with_context(|| format!("Failed to read `{}`", dir.display()))?
        .filter_map(|entry| entry.ok().map(|entry| entry.path()))
        .filter(|path| path.extension().and_then(|ext| ext.to_str()) == Some(extension))
        .collect();

    apps.sort();
    Ok(apps)
}
