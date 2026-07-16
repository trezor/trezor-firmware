use anyhow::{Context, Result, ensure};
use cargo_metadata::Package;

pub const APP_ID_MAX_LEN: usize = 32;
pub const APP_NAME_MAX_LEN: usize = 32;
pub const APP_VENDOR_MAX_LEN: usize = 32;

/// Retrieves the app version from the package metadata and converts it into a 4-byte array.
pub fn app_version(package: &Package) -> Result<[u8; 4]> {
    let ver = package.version.clone();
    Ok([
        ver.major
            .try_into()
            .context("Failed to convert major version to u8")?,
        ver.minor
            .try_into()
            .context("Failed to convert minor version to u8")?,
        ver.patch
            .try_into()
            .context("Failed to convert patch version to u8")?,
        0,
    ])
}

/// Retrieves the app identifier from the package metadata.
pub fn app_identifier(package: &Package) -> Result<[u8; APP_ID_MAX_LEN]> {
    let id = get_metadata_string(package, "id")?;
    let id_bytes = id.as_bytes();

    ensure!(
        id_bytes.len() <= APP_ID_MAX_LEN,
        "App identifier '{}' is too long (max {} bytes)",
        id,
        APP_ID_MAX_LEN
    );

    let mut result = [0u8; APP_ID_MAX_LEN];
    result[..id_bytes.len()].copy_from_slice(id_bytes);

    Ok(result)
}

/// Retrieve the app name from the package metadata.
pub fn app_name(package: &Package) -> Result<[u8; APP_NAME_MAX_LEN]> {
    let name = get_metadata_string(package, "name")?;
    let name_bytes = name.as_bytes();

    ensure!(
        name_bytes.len() <= APP_NAME_MAX_LEN,
        "App name '{}' is too long (max {} bytes)",
        name,
        APP_NAME_MAX_LEN
    );

    let mut result = [0u8; APP_NAME_MAX_LEN];
    result[..name_bytes.len()].copy_from_slice(name_bytes);

    Ok(result)
}

/// Retrieve the vendor name from the package metadata.
pub fn vendor_name(package: &Package) -> Result<[u8; APP_VENDOR_MAX_LEN]> {
    let vendor = get_metadata_string(package, "vendor")?;
    let vendor_bytes = vendor.as_bytes();

    ensure!(
        vendor_bytes.len() <= APP_VENDOR_MAX_LEN,
        "Vendor name '{}' is too long (max {} bytes)",
        vendor,
        APP_VENDOR_MAX_LEN
    );

    let mut result = [0u8; APP_VENDOR_MAX_LEN];
    result[..vendor_bytes.len()].copy_from_slice(vendor_bytes);

    Ok(result)
}

/// Retrieves the stack size from the package metadata
pub fn stack_size(package: &Package) -> Result<u32> {
    let stack_size = get_metadata_number(package, "stack-size")?;

    ensure!(
        stack_size <= 256 * 1024,
        "Stack size {} is too large (max 256kB)",
        stack_size
    );

    Ok(stack_size as u32)
}

/// Retrieve the heap size from the package metadata
pub fn heap_size(package: &Package) -> Result<u32> {
    let heap_size = get_metadata_number(package, "heap-size")?;

    ensure!(
        heap_size <= 256 * 1024,
        "Heap size {} is too large (max 256kB)",
        heap_size
    );

    Ok(heap_size as u32)
}

/// Retrieves the app ring from the package metadata
pub fn app_ring(package: &Package) -> Result<u8> {
    let ring = get_metadata_number(package, "app-ring")?;

    ensure!(
        ring <= 2,
        "App ring {} is invalid (must be 0, 1, or 2)",
        ring
    );

    Ok(ring as u8)
}

fn get_metadata_string(package: &Package, key: &str) -> Result<String> {
    let value = package
        .metadata
        .get("trezor")
        .and_then(|m| m.get(key))
        .and_then(|v| v.as_str())
        .ok_or_else(|| anyhow::anyhow!("{} not found in Cargo.toml", key))?;

    Ok(value.to_string())
}

fn get_metadata_number(package: &Package, key: &str) -> Result<u64> {
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
