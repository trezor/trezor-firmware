use std::{
    env, fs,
    path::{Component, Path, PathBuf},
};

use pathdiff::diff_paths;

use color_eyre::{Result, eyre::WrapErr};

/// Checks if the parent directory of the given output path exists,
/// and creates it if it doesn't.
pub fn ensure_parent_directory(output: impl AsRef<Path>) -> Result<()> {
    let output = output.as_ref();
    if let Some(parent) = output.parent() {
        fs::create_dir_all(parent)
            .with_context(|| format!("Failed to create output directory {}", parent.display()))?;
    }
    Ok(())
}

/// Deletes the file at the given path if it exists.
pub fn delete_file_if_exists(path: impl AsRef<Path>) -> Result<()> {
    let path = path.as_ref();
    if path.exists() {
        fs::remove_file(path)
            .with_context(|| format!("Failed to remove file {}", path.display()))?;
    }
    Ok(())
}

/// Returns the library name from the `CARGO_MANIFEST_LINKS` environment variable.
///
/// This variable is set by Cargo when building a crate that has a `links` field in its `Cargo.toml`.
///
/// # Errors
///
/// Returns an error if the environment variable is not set.
pub fn links_name() -> Result<String> {
    env::var("CARGO_MANIFEST_LINKS").context("Failed to get CARGO_MANIFEST_LINKS")
}

/// Reads a `DEP_<CRATE>_PUBLIC_C_<KEY>` metadata variable exported by a dependency's build script.
pub fn library_metadata(lib_name: &str, kind: &str) -> Result<String> {
    std::env::var(format!("DEP_{}_PUBLIC_C_{}", lib_name.to_uppercase(), kind)).context(format!(
        "Failed to get public C metadata for crate `{lib_name}` and kind `{kind}`"
    ))
}

/// Measures the execution time of a closure and prints it with the given label
pub fn measure_time<T, F>(label: impl AsRef<str>, f: F) -> T
where
    F: FnOnce() -> T,
{
    let start_time = std::time::Instant::now();
    let result = f();
    let duration = start_time.elapsed();
    eprintln!("{}: {:.2?}", label.as_ref(), duration);
    result
}

/// Converts `path` to a path relative to `CARGO_MANIFEST_DIR` when possible.
///
/// Relative inputs are first interpreted as `CARGO_MANIFEST_DIR/<path>`.
/// Absolute inputs are used as-is.
///
/// If a relative path from `CARGO_MANIFEST_DIR` can be computed, it is
/// returned; otherwise the original absolute path is returned unchanged.
pub fn relative_to_manifest(path: impl AsRef<Path>) -> PathBuf {
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());

    let abs_path = if path.as_ref().is_absolute() {
        normalize_path(path)
    } else {
        join_paths_lexically(&manifest_dir, path)
    };

    let rel_path = diff_paths(&abs_path, &manifest_dir).unwrap_or(abs_path);

    if rel_path.as_os_str().is_empty() {
        PathBuf::from(".")
    } else {
        rel_path
    }
}

/// Normalizes a path by processing its components lexically.
/// Collapses repeated separators, removes `.` components and
/// handles `..` by popping one previously collected component when possible.
pub fn normalize_path(path: impl AsRef<Path>) -> PathBuf {
    path.as_ref()
        .components()
        .fold(PathBuf::new(), |mut acc, comp| {
            match comp {
                Component::ParentDir => {
                    acc.pop();
                }
                Component::CurDir => {}
                other => acc.push(other.as_os_str()),
            }
            acc
        })
}

/// Joins `base` with `relative` and normalizes components lexically.
pub fn join_paths_lexically(base_dir: impl AsRef<Path>, relative: impl AsRef<Path>) -> PathBuf {
    normalize_path(base_dir.as_ref().join(relative.as_ref()))
}

fn starts_with_parent(path: &Path) -> bool {
    matches!(path.components().next(), Some(Component::ParentDir))
}

/// Makes an output path for a source file, placing it under `out_dir` and changing the extension.
pub fn derive_output_path(base_dir: &Path, src: &Path, out_dir: &Path, extension: &str) -> PathBuf {
    // If `src` is absolute or starts with `..`, treat it as out-of-tree and
    // place it under `OUT_DIR/__oot/...`.
    let out_of_tree = src.is_absolute() || starts_with_parent(src);

    let subpath = if out_of_tree {
        let abs_path = join_paths_lexically(base_dir, src);

        // Construct a path like `__oot/...`
        let mut path = PathBuf::from("__oot");

        let mut it = abs_path.components();

        // Skip leading components that are common with `base_dir` to
        // avoid unnecessarily long paths for in-tree files.
        for (base_comp, path_comp) in base_dir.components().zip(&mut it) {
            if base_comp != path_comp {
                path.push(path_comp.as_os_str());
                break;
            }
        }

        for comp in it {
            path.push(comp.as_os_str());
        }

        path
    } else {
        src.to_path_buf()
    };

    out_dir.join(subpath).with_extension(extension)
}

/// Gets a path from an environment variable, with error handling.
pub fn path_from_env(name: &str) -> Result<PathBuf> {
    env::var(name)
        .map(PathBuf::from)
        .with_context(|| format!("Environment variable `{name}` is required but not set"))
}
