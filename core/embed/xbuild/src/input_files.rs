use std::{
    fs,
    path::{Path, PathBuf},
};

use color_eyre::{Result, eyre::WrapErr};

use globset::Glob;

/// Helper struct for managing input files based on glob-like filters.
//
/// This struct allows adding and removing files from a list of inputs based on
/// filters that can include wildcards and directory patterns.
#[derive(Default)]
pub struct InputFiles {
    files: Vec<PathBuf>,
}

impl InputFiles {
    /// Creates a new empty `InputFiles`.
    pub fn new() -> Self {
        Self::default()
    }

    /// Adds files matching the given filter under the specified base directory.
    pub fn add(&mut self, base: impl AsRef<Path>, filter: &str) -> Result<()> {
        let base = base.as_ref();
        let normalized_filter = filter.trim_start_matches('/');
        let search_dirs = filter_search_dirs(base, filter)?;

        for dir in search_dirs {
            if !dir.exists() {
                continue;
            }

            for entry in fs::read_dir(&dir)
                .with_context(|| format!("Failed to read directory {}", dir.display()))?
            {
                let entry = entry?;
                let entry_type = entry.file_type()?;
                if !entry_type.is_file() {
                    continue;
                }

                let path = entry.path();
                let relative_path = path
                    .strip_prefix(base)
                    .with_context(|| format!("Failed to strip prefix from {}", path.display()))?;

                if !path_matches_filter(relative_path, normalized_filter) {
                    continue;
                }

                self.files.push(path);
            }
        }

        self.files.sort();
        self.files.dedup();

        Ok(())
    }

    /// Removes files matching the given filter under the specified base directory.
    pub fn remove(&mut self, base: impl AsRef<Path>, filter: &str) {
        let base = base.as_ref();
        let normalized_filter = filter.trim_start_matches('/');
        self.files.retain(|path| {
            let Ok(relative_path) = path.strip_prefix(base) else {
                return true;
            };

            !path_matches_filter(relative_path, normalized_filter)
        });
    }

    /// Returns the list of input files as `PathBuf`s.
    pub fn as_paths(&self) -> &[PathBuf] {
        &self.files
    }

    /// Returns an iterator over the input files as `&Path`.
    pub fn as_path_refs(&self) -> impl Iterator<Item = &Path> {
        self.files.iter().map(PathBuf::as_path)
    }
}

fn path_matches_filter(path: impl AsRef<Path>, filter: &str) -> bool {
    let path = path.as_ref();
    let normalized_filter = filter.trim_start_matches('/');
    let filter_path = Path::new(normalized_filter);

    let mut filter_components = filter_path.iter();
    let Some(file_filter) = filter_components.next_back() else {
        return false;
    };

    let mut path_components = path.iter();
    let Some(file_name) = path_components.next_back() else {
        return false;
    };

    let file_matcher = match Glob::new(&file_filter.to_string_lossy()) {
        Ok(glob) => glob.compile_matcher(),
        Err(_) => return false,
    };

    if !file_matcher.is_match(file_name.to_string_lossy().as_ref()) {
        return false;
    }

    let filter_dirs = filter_components.collect::<Vec<_>>();
    let path_dirs = path_components.collect::<Vec<_>>();

    if filter_dirs.len() != path_dirs.len() {
        return false;
    }

    filter_dirs
        .iter()
        .zip(path_dirs.iter())
        .all(
            |(filter_dir, path_dir)| match Glob::new(&filter_dir.to_string_lossy()) {
                Ok(glob) => glob
                    .compile_matcher()
                    .is_match(path_dir.to_string_lossy().as_ref()),
                Err(_) => false,
            },
        )
}

fn filter_search_dirs(base: &Path, filter: &str) -> Result<Vec<PathBuf>> {
    let normalized_filter = filter.trim_start_matches('/');
    let mut search_dirs = vec![base.to_path_buf()];

    if let Some(parent) = Path::new(normalized_filter).parent() {
        for component in parent.iter() {
            let component = component.to_string_lossy();
            if component.is_empty() {
                continue;
            }

            let matcher = match Glob::new(&component) {
                Ok(glob) => glob.compile_matcher(),
                Err(_) => return Ok(Vec::new()),
            };

            let mut next_dirs = Vec::new();

            for dir in search_dirs {
                if !dir.exists() {
                    continue;
                }

                for entry in fs::read_dir(&dir)
                    .with_context(|| format!("Failed to read directory {}", dir.display()))?
                {
                    let entry = entry?;
                    let entry_type = entry.file_type()?;
                    if !entry_type.is_dir() {
                        continue;
                    }

                    let entry_name = entry.file_name();
                    let entry_name = entry_name.to_string_lossy();
                    if matcher.is_match(entry_name.as_ref()) {
                        next_dirs.push(entry.path());
                    }
                }
            }

            search_dirs = next_dirs;

            if search_dirs.is_empty() {
                return Ok(Vec::new());
            }
        }
    }

    Ok(search_dirs)
}

#[cfg(test)]
mod tests {
    use super::InputFiles;
    use std::path::PathBuf;

    #[test]
    fn remove_files_removes_only_matching_files_under_base() {
        let mut inputs = InputFiles {
            files: vec![
                PathBuf::from("src/main.py"),
                PathBuf::from("src/mod.rs"),
                PathBuf::from("other/main.py"),
            ],
        };

        inputs.remove("src", "*.py");

        assert_eq!(
            inputs.files,
            vec![PathBuf::from("src/mod.rs"), PathBuf::from("other/main.py"),]
        );
    }
}
