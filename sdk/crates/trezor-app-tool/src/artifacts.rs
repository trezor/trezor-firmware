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
    let entries = std::fs::read_dir(&dir)
        .with_context(|| format!("Failed to read `{}`", dir.display()))?
        .map(|entry| entry.map(|entry| entry.path()));
    with_ext(entries, extension).with_context(|| format!("Failed to read `{}`", dir.display()))
}

/// Sorted paths with `extension`; fails on the first entry error, so no
/// artifact is silently left out.
fn with_ext(
    entries: impl Iterator<Item = std::io::Result<PathBuf>>,
    extension: &str,
) -> Result<Vec<PathBuf>> {
    let mut paths = Vec::new();
    for path in entries {
        let path = path?;
        if path.extension().and_then(|ext| ext.to_str()) == Some(extension) {
            paths.push(path);
        }
    }
    paths.sort();
    Ok(paths)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn with_ext_filters_and_sorts() {
        let entries = ["b.bin", "a.elf", "a.bin"].map(|p| std::io::Result::Ok(PathBuf::from(p)));
        let paths = with_ext(entries.into_iter(), "bin").unwrap();
        assert_eq!(paths, [PathBuf::from("a.bin"), PathBuf::from("b.bin")]);
    }

    #[test]
    fn with_ext_propagates_entry_errors() {
        let entries = [
            std::io::Result::Ok(PathBuf::from("a.bin")),
            Err(std::io::Error::other("boom")),
        ];
        assert!(with_ext(entries.into_iter(), "bin").is_err());
    }
}
