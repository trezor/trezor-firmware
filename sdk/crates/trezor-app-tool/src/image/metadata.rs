//! Reads and validates an app's `[package.metadata.trezor]` fields from its
//! `Cargo.toml`.

use std::collections::{HashMap, HashSet};

use anyhow::{Context, Result, ensure};
use cargo_metadata::{DependencyKind, Metadata, MetadataCommand, Node, Package, PackageId};

/// Upper bound on an app's IPC inbox, mirroring the kernel's
/// `IPC_MAX_BUFFER_SIZE` (`core/embed/sys/ipc/inc/sys/ipc.h`). `ipc_register`
/// refuses anything larger.
pub const IPC_BUFFER_MAX_SIZE: u64 = 64 * 1024;

/// Smallest inbox we accept. Anything below this cannot hold even a single
/// API reply plus framing, so it is always a mistake.
pub const IPC_BUFFER_MIN_SIZE: u64 = 256;

/// Inbox size used when an app does not declare `ipc-buffer-size` (or sets it
/// to 0).
///
/// Sized off the fixed API traffic, not off wire messages: the largest reply
/// Core sends back over IPC is the 111-byte xpub from
/// `CryptoV1::get_xpub`, and UI replies are a handful of bytes each. With the
/// 12-byte `ipc_queue_item_t` header that is ~128 bytes for the biggest single
/// message, so 1 KiB leaves 8x headroom for queued replies.
///
/// An app that receives host wire messages through the same inbox needs more
/// than this and must say so explicitly -- there is no way to guess how large
/// its protocol messages get.
pub const IPC_BUFFER_DEFAULT_SIZE: u64 = 1024;

/// Retrieves the app version from the package metadata.
pub fn app_version(package: &Package) -> String {
    package.version.to_string()
}

/// Retrieves the app identifier from the package metadata.
pub fn app_identifier(package: &Package) -> Result<String> {
    metadata_string(package, "id")
}

/// Retrieve the app name from the package metadata.
pub fn app_name(package: &Package) -> Result<String> {
    metadata_string(package, "name")
}

/// Retrieve the vendor name from the package metadata.
pub fn vendor_name(package: &Package) -> Result<String> {
    metadata_string(package, "vendor")
}

/// Retrieves the stack size from the package metadata
pub fn stack_size(package: &Package) -> Result<u32> {
    let stack_size = metadata_number(package, "stack-size")?;

    ensure!(
        stack_size <= 256 * 1024,
        "Stack size {} is too large (max 256kB)",
        stack_size
    );

    Ok(stack_size as u32)
}

/// Retrieve the heap size from the package metadata
pub fn heap_size(package: &Package) -> Result<u32> {
    let heap_size = metadata_number(package, "heap-size")?;

    ensure!(
        heap_size <= 256 * 1024,
        "Heap size {} is too large (max 256kB)",
        heap_size
    );

    Ok(heap_size as u32)
}

/// Retrieve the IPC inbox size, in bytes, from the package metadata.
///
/// The key is optional; a missing entry or an explicit 0 means "no opinion"
/// and yields [`IPC_BUFFER_DEFAULT_SIZE`].
pub fn ipc_buffer_size(package: &Package) -> Result<u32> {
    let size = match optional_metadata_number(package, "ipc-buffer-size")? {
        None | Some(0) => IPC_BUFFER_DEFAULT_SIZE,
        Some(size) => size,
    };
    validate_ipc_buffer_size(size)
}

/// The inbox is allocated as `[usize]`, so its byte size has to be a multiple
/// of `size_of::<usize>()`: 4 on the ARM target, 8 on the emulators. A
/// multiple of 8 covers both.
fn validate_ipc_buffer_size(size: u64) -> Result<u32> {
    ensure!(
        size >= IPC_BUFFER_MIN_SIZE,
        "IPC buffer size {} is too small (min {} bytes)",
        size,
        IPC_BUFFER_MIN_SIZE
    );

    ensure!(
        size <= IPC_BUFFER_MAX_SIZE,
        "IPC buffer size {} is too large (max {} bytes)",
        size,
        IPC_BUFFER_MAX_SIZE
    );

    ensure!(
        size % 8 == 0,
        "IPC buffer size {} must be a multiple of 8",
        size
    );

    Ok(size as u32)
}

/// Retrieves the app ring from the package metadata
pub fn app_ring(package: &Package) -> Result<u8> {
    let ring = metadata_number(package, "app-ring")?;

    ensure!(
        ring <= 2,
        "App ring {} is invalid (must be 0, 1, or 2)",
        ring
    );

    Ok(ring as u8)
}

/// Retrieves the curves from the package metadata
/// (array of strings, e.g. ["secp256k1", "ed25519"])
pub fn curves(package: &Package) -> Result<Vec<String>> {
    metadata_string_array(package, "curves")
}

/// Retrieves the allowed paths from the package metadata
pub fn paths(package: &Package) -> Result<Vec<String>> {
    metadata_string_array(package, "paths")
}

/// Retrieves the SDK version of the `trezor-app-sdk` dependency
/// from the package metadata.
pub fn sdk_version(package: &Package) -> Result<String> {
    let sdk = dependency_package(package, "trezor-app-sdk")?;
    metadata_string(&sdk, "sdk-version")
}

/// Retrieves the ABI version used by the app.
pub fn abi_version() -> Result<u8> {
    std::env::var("TREZOR_APP_TOOLING_ABI_VERSION").map_or(Ok(1), |v| {
        v.parse::<u8>().context("Failed to parse ABI version")
    })
}

fn metadata_string(package: &Package, key: &str) -> Result<String> {
    let value = package
        .metadata
        .get("trezor")
        .and_then(|m| m.get(key))
        .and_then(|v| v.as_str())
        .ok_or_else(|| anyhow::anyhow!("{} not found in Cargo.toml", key))?;

    Ok(value.to_string())
}

fn metadata_string_array(package: &Package, key: &str) -> Result<Vec<String>> {
    let values = package
        .metadata
        .get("trezor")
        .and_then(|m| m.get(key))
        .and_then(|v| v.as_array())
        .ok_or_else(|| anyhow::anyhow!("{} not found in Cargo.toml", key))?;

    values
        .iter()
        .map(|v| {
            v.as_str()
                .map(str::to_string)
                .ok_or_else(|| anyhow::anyhow!("{key} must be an array of strings"))
        })
        .collect()
}

/// Like [`metadata_number`], but returns `None` instead of failing when the
/// key is absent.
fn optional_metadata_number(package: &Package, key: &str) -> Result<Option<u64>> {
    if package
        .metadata
        .get("trezor")
        .and_then(|m| m.get(key))
        .is_none()
    {
        return Ok(None);
    }
    metadata_number(package, key).map(Some)
}

fn metadata_number(package: &Package, key: &str) -> Result<u64> {
    let value = package
        .metadata
        .get("trezor")
        .and_then(|m| m.get(key))
        .ok_or_else(|| anyhow::anyhow!("{} not found in Cargo.toml", key))?;

    if let Some(value) = value.as_u64() {
        return Ok(value);
    }

    value
        .as_str()
        .ok_or_else(|| anyhow::anyhow!("{} must be a number in Cargo.toml", key))?
        .parse::<u64>()
        .with_context(|| format!("Failed to parse {key}"))
}

/// Returns the [`Package`] of `package`'s dependency called `name`, so its
/// version and `[package.metadata]` can be read.
///
/// The `Package` values handled by this tool come from a `no_deps` metadata
/// query, which lists workspace members only, so the dependency graph is
/// resolved here for the package's manifest. Fails unless exactly one `name`
/// package is linked into `package`, see [`unique_linked_package`].
pub fn dependency_package(package: &Package, name: &str) -> Result<Package> {
    ensure!(
        package.dependencies.iter().any(|dep| dep.name == name),
        "Dependency {name} not found in Cargo.toml"
    );

    let metadata = MetadataCommand::new()
        .manifest_path(&package.manifest_path)
        .exec()
        .context("Failed to read cargo metadata")?;

    unique_linked_package(&metadata, &package.id, name).cloned()
}

/// Returns the only package called `name` that `root` links, directly or
/// transitively, through normal or build dependencies.
///
/// Packages used only by other workspace members, or only as dev-dependencies,
/// are not part of `root`'s build and are ignored. More than one match, e.g.
/// two `trezor-app-sdk` versions or sources, is an error.
fn unique_linked_package<'a>(
    metadata: &'a Metadata,
    root: &PackageId,
    name: &str,
) -> Result<&'a Package> {
    let resolve = metadata
        .resolve
        .as_ref()
        .context("cargo metadata has no dependency graph")?;
    let nodes: HashMap<&PackageId, &Node> = resolve.nodes.iter().map(|n| (&n.id, n)).collect();

    let mut linked = HashSet::new();
    let mut pending = vec![root];
    while let Some(id) = pending.pop() {
        if !linked.insert(id) {
            continue;
        }
        let node = nodes
            .get(id)
            .with_context(|| format!("Package {id} missing from the dependency graph"))?;
        // `root`'s dev-dependencies are only resolved for its tests
        let linked_deps = node.deps.iter().filter(|dep| {
            dep.dep_kinds.is_empty()
                || dep
                    .dep_kinds
                    .iter()
                    .any(|kind| kind.kind != DependencyKind::Development)
        });
        pending.extend(linked_deps.map(|dep| &dep.pkg));
    }

    let mut matches = metadata
        .packages
        .iter()
        .filter(|p| p.name.as_str() == name && linked.contains(&p.id));
    let found = matches
        .next()
        .with_context(|| format!("Package {name} not found in the dependency graph"))?;
    let others: Vec<_> = matches.collect();
    if !others.is_empty() {
        let list = std::iter::once(found)
            .chain(others)
            .map(|p| match &p.source {
                Some(source) => format!("{} ({source})", p.version),
                None => format!("{} ({})", p.version, p.manifest_path),
            })
            .collect::<Vec<_>>()
            .join(", ");
        anyhow::bail!("The build pulls in more than one {name} package: {list}");
    }
    Ok(found)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ipc_buffer_size_accepts_multiples_of_8() {
        assert_eq!(validate_ipc_buffer_size(12 * 1024).unwrap(), 12 * 1024);
        assert_eq!(validate_ipc_buffer_size(IPC_BUFFER_MIN_SIZE).unwrap(), 256);
        assert_eq!(
            validate_ipc_buffer_size(IPC_BUFFER_MAX_SIZE).unwrap(),
            65536
        );
    }

    /// Writes a throwaway tree of path-only crates (`dir`, `Cargo.toml`) and
    /// returns `app`'s package from a `no_deps` query, as the tool sees it.
    fn app_in_tree(test: &str, crates: &[(&str, String)]) -> (std::path::PathBuf, Package) {
        let root = std::env::temp_dir().join(format!("app-tool-{test}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        for (dir, manifest) in crates {
            let dir = root.join(dir);
            std::fs::create_dir_all(dir.join("src")).unwrap();
            std::fs::write(dir.join("Cargo.toml"), manifest).unwrap();
            std::fs::write(dir.join("src/lib.rs"), "").unwrap();
        }
        let metadata = MetadataCommand::new()
            .manifest_path(root.join("ws/app/Cargo.toml"))
            .no_deps()
            .exec()
            .unwrap();
        let app = metadata
            .packages
            .into_iter()
            .find(|p| p.name.as_str() == "app")
            .unwrap();
        (root, app)
    }

    fn manifest(name: &str, version: &str, deps: &str) -> String {
        format!("[package]\nname = \"{name}\"\nversion = \"{version}\"\nedition = \"2021\"\n{deps}")
    }

    fn sdk_crates() -> Vec<(&'static str, String)> {
        vec![
            ("sdk1", manifest("trezor-app-sdk", "0.1.0", "")),
            ("sdk2", manifest("trezor-app-sdk", "0.2.0", "")),
            (
                "mid",
                manifest(
                    "mid",
                    "0.1.0",
                    "[dependencies]\ntrezor-app-sdk = { path = \"../sdk2\" }\n",
                ),
            ),
        ]
    }

    #[test]
    fn dependency_package_ignores_other_members_and_dev_deps() {
        let mut crates = sdk_crates();
        crates.push((
            "ws",
            "[workspace]\nmembers = [\"app\", \"other\"]\nresolver = \"2\"\n".into(),
        ));
        crates.push((
            "ws/app",
            manifest(
                "app",
                "0.1.0",
                "[dependencies]\ntrezor-app-sdk = { path = \"../../sdk1\" }\n\
                 [dev-dependencies]\nmid = { path = \"../../mid\" }\n",
            ),
        ));
        crates.push((
            "ws/other",
            manifest(
                "other",
                "0.1.0",
                "[dependencies]\nmid = { path = \"../../mid\" }\n",
            ),
        ));
        let (root, app) = app_in_tree("single", &crates);

        let sdk = dependency_package(&app, "trezor-app-sdk").unwrap();
        assert_eq!(sdk.version.to_string(), "0.1.0");
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn dependency_package_rejects_two_linked_sdks() {
        let mut crates = sdk_crates();
        crates.push((
            "ws",
            "[workspace]\nmembers = [\"app\"]\nresolver = \"2\"\n".into(),
        ));
        crates.push((
            "ws/app",
            manifest(
                "app",
                "0.1.0",
                "[dependencies]\ntrezor-app-sdk = { path = \"../../sdk1\" }\n\
                 mid = { path = \"../../mid\" }\n",
            ),
        ));
        let (root, app) = app_in_tree("double", &crates);

        let error = dependency_package(&app, "trezor-app-sdk")
            .unwrap_err()
            .to_string();
        assert!(error.contains("more than one trezor-app-sdk"), "{error}");
        assert!(
            error.contains("0.1.0") && error.contains("0.2.0"),
            "{error}"
        );
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn ipc_buffer_size_rejects_invalid() {
        assert!(validate_ipc_buffer_size(12 * 1024 + 4).is_err());
        assert!(validate_ipc_buffer_size(IPC_BUFFER_MIN_SIZE - 8).is_err());
        assert!(validate_ipc_buffer_size(IPC_BUFFER_MAX_SIZE + 8).is_err());
    }
}
