//! Post-build step that turns the app binaries in the artifacts directory
//! into the app tree that apps are loaded from
//! ([`crate::helpers::artifacts_serialized_dir`]):
//! - `<id>/<version>/*.tapp`: the apps, serialized as JSON chunks
//! - `<id>/<version>/*.proof`: Merkle proof of each app in its ring's tree
//! - `root-packets/*.tmr`: dev-signed RootPackets with the ring roots
//! - `index.v1.json` and `<id>/index.v1.json`: main and per-app indices
//!
//! Serialized apps left from earlier builds are kept and included.

use anyhow::{Context, Result, ensure};
use base64::prelude::{BASE64_STANDARD, Engine};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use crate::image::{self, AppHeader, EXT_APP};
use crate::merkle::{self, MerkleTree};
use crate::root_packet::{MAX_RINGS, NUM_SIGNATURES, RootPacket};
use crate::{artifacts, helpers};

// Development seeds for deterministic ML-DSA-44 dev-key generation
const DEV_MLDSA_SEEDS: [[u8; 32]; NUM_SIGNATURES] = [[0x71; 32], [0x72; 32]];

const EXT_PROOF: &str = "proof";
const EXT_ROOTPACKET: &str = "tmr";
const INDEX_FILENAME: &str = "index.v1.json";
const ROOT_PACKET_DIR: &str = "root-packets";
const ROOT_PACKETS: [(&str, &[u8]); 2] =
    [("rootpacket_ring0", &[0]), ("rootpacket_ring12", &[1, 2])];

/// Generates the app tree from all app binaries in the artifacts directory.
pub fn generate() -> Result<()> {
    let apps = artifacts::artifact_with_ext("bin")?;
    ensure!(!apps.is_empty(), "No generated app images found");
    let artifacts_serialized_dir = helpers::artifacts_serialized_dir()?;
    println!("app-tool: Building app proofs and dev-signed RootPacket");

    // Serialize apps as JSON
    for app in &apps {
        serialize_app_as_json(app, &artifacts_serialized_dir)?;
    }

    let timestamp = i64::try_from(
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .context("System clock is set before 1970")?
            .as_secs(),
    )?;

    // Take all serialized apps (even previously created ones)
    let app_infos = list_serialized_apps(&artifacts_serialized_dir)?;

    // Create app proofs
    let mut ring_roots: [Option<[u8; 32]>; MAX_RINGS] = [None; MAX_RINGS];
    for (app_ring, ring_root) in ring_roots.iter_mut().enumerate() {
        let ring_apps: Vec<&AppInfo> = app_infos
            .iter()
            .filter(|app| usize::from(app.header.app_ring()) == app_ring)
            .collect();
        let Some(tree) = MerkleTree::new(ring_apps.iter().map(|app| app.digest)) else {
            continue;
        };
        create_proofs(&ring_apps, &tree)?;
        *ring_root = Some(tree.root_hash());
    }

    // Create rootpackets
    let root_packet_dir = artifacts_serialized_dir.join(ROOT_PACKET_DIR);
    helpers::ensure_directory(&root_packet_dir)?;
    for (name, rings) in ROOT_PACKETS {
        let path = root_packet_dir.join(format!("{name}.{EXT_ROOTPACKET}"));
        write_root_packet(&path, rings, &ring_roots, timestamp)?;
    }

    // Create app indices
    let app_ids = create_app_indices(&artifacts_serialized_dir, &app_infos)?;

    // Create main index
    write_main_index(&artifacts_serialized_dir, &app_ids)?;
    Ok(())
}

// Fields are written to JSON in declaration order
#[derive(Serialize, Deserialize)]
struct SerializedApp {
    header: String,
    chunks: Vec<(String, String)>,
}

fn serialize_app_as_json(app: &Path, out_dir: &Path) -> Result<()> {
    let app_data = fs::read(app).with_context(|| format!("Failed to read {}", app.display()))?;

    let (header, payload) = AppHeader::parse(&app_data)?;
    let header_bytes = &app_data[..header.header_size()];
    ensure!(
        payload.len() == header.code_size(),
        "Payload is {} bytes, but the header says {}",
        payload.len(),
        header.code_size()
    );

    let hashes = image::hash_chain(payload, header.chunk_size());
    ensure!(
        hashes[0] == header.chunk_hash(),
        "Payload hash does not match the header"
    );

    let chunks: Vec<(String, String)> = payload
        .chunks(header.chunk_size())
        .zip(&hashes[1..])
        .map(|(chunk, hash)| (to_hex(hash), BASE64_STANDARD.encode(chunk)))
        .collect();

    let out = SerializedApp {
        header: BASE64_STANDARD.encode(header_bytes),
        chunks,
    };
    let dest = image::serialized_app_path(app, out_dir)?;
    fs::create_dir_all(
        dest.parent()
            .context("Serialized app path has no parent directory")?,
    )?;
    fs::write(&dest, serde_json::to_string_pretty(&out)?)
        .with_context(|| format!("Failed to write {}", dest.display()))?;
    Ok(())
}

struct AppInfo {
    path: PathBuf,
    header: AppHeader,
    digest: [u8; 32],
    sha256: [u8; 32],
}

impl AppInfo {
    fn from_serialized_app(path: &Path) -> Result<Self> {
        let app_json = fs::read_to_string(path)
            .with_context(|| format!("Failed to read {}", path.display()))?;
        let app: SerializedApp = serde_json::from_str(&app_json)
            .with_context(|| format!("Failed to parse {}", path.display()))?;
        let header_bytes = BASE64_STANDARD
            .decode(&app.header)
            .with_context(|| format!("Invalid header encoding in {}", path.display()))?;

        let (header, _) = AppHeader::parse(&header_bytes)
            .with_context(|| format!("Invalid header in {}", path.display()))?;
        ensure!(
            header_bytes.len() == header.header_size(),
            "Header in {} is {} bytes, expected {}",
            path.display(),
            header_bytes.len(),
            header.header_size()
        );
        let expected_path = image::serialized_app_relative_path(&header)
            .with_context(|| format!("Invalid header in {}", path.display()))?;
        ensure!(
            path.ends_with(&expected_path),
            "App {} should be at {}, as given by its header",
            path.display(),
            expected_path.display()
        );
        ensure!(
            usize::from(header.app_ring()) < MAX_RINGS,
            "App {} has an invalid app ring {}",
            path.display(),
            header.app_ring()
        );
        check_chunks(
            &app.chunks,
            header.chunk_size(),
            header.code_size(),
            header.chunk_hash(),
        )
        .with_context(|| format!("Invalid chunks in {}", path.display()))?;

        Ok(AppInfo {
            path: path.to_path_buf(),
            header,
            digest: Sha256::digest(&header_bytes).into(),
            sha256: Sha256::digest(app_json.as_bytes()).into(),
        })
    }
}

/// Checks that the chunks of a serialized app are cut by `chunk_size`, add up
/// to `code_size` bytes, and match the hash chain starting at `chunk_hash`.
fn check_chunks(
    chunks: &[(String, String)],
    chunk_size: usize,
    code_size: usize,
    chunk_hash: [u8; 32],
) -> Result<()> {
    let mut payload = Vec::new();
    for (index, (_, chunk)) in chunks.iter().enumerate() {
        let chunk = BASE64_STANDARD
            .decode(chunk)
            .with_context(|| format!("Chunk {index} is not valid base64"))?;
        let is_last = index + 1 == chunks.len();
        let valid_size = if is_last {
            (1..=chunk_size).contains(&chunk.len())
        } else {
            chunk.len() == chunk_size
        };
        ensure!(
            valid_size,
            "Chunk {index} has an invalid size {}",
            chunk.len()
        );
        payload.extend_from_slice(&chunk);
    }
    ensure!(
        payload.len() == code_size,
        "Payload is {} bytes, but the header says {code_size}",
        payload.len()
    );

    let hashes = image::hash_chain(&payload, chunk_size);
    ensure!(
        hashes[0] == chunk_hash,
        "Payload hash does not match the header"
    );
    for (index, ((stored_hash, _), hash)) in chunks.iter().zip(&hashes[1..]).enumerate() {
        ensure!(
            *stored_hash == to_hex(hash),
            "Hash of chunk {index} does not match the payload"
        );
    }
    Ok(())
}

/// Lists all serialized apps, failing with every invalid one if there are any.
fn list_serialized_apps(dir: &Path) -> Result<Vec<AppInfo>> {
    let mut apps = Vec::new();
    let mut errors = Vec::new();
    for app_dir in subdirectories(dir)? {
        for version_dir in subdirectories(&app_dir)? {
            for entry in fs::read_dir(&version_dir)
                .with_context(|| format!("Failed to read {}", version_dir.display()))?
            {
                let path = entry?.path();
                if path.is_file() && path.extension().is_some_and(|ext| ext == EXT_APP) {
                    match AppInfo::from_serialized_app(&path) {
                        Ok(app) => apps.push(app),
                        Err(err) => errors.push(format!("{err:#}")),
                    }
                }
            }
        }
    }
    errors.sort();
    ensure!(
        errors.is_empty(),
        "{} serialized app(s) are invalid:\n  {}",
        errors.len(),
        errors.join("\n  ")
    );
    apps.sort_by(|a, b| a.path.cmp(&b.path));
    Ok(apps)
}

#[derive(Serialize)]
struct SerializedProof {
    root: String,
    proof: Vec<String>,
}

fn create_proofs(apps: &[&AppInfo], tree: &MerkleTree) -> Result<()> {
    for app in apps {
        let proof = tree
            .proof(&app.digest)
            .with_context(|| format!("App {} not found in the Merkle tree", app.path.display()))?;
        ensure!(
            merkle::evaluate_proof(&app.digest, proof) == tree.root_hash(),
            "Proof of app {} does not evaluate to the Merkle root",
            app.path.display()
        );
        let out = SerializedProof {
            root: to_hex(&tree.root_hash()),
            proof: proof.iter().map(|entry| to_hex(entry)).collect(),
        };
        let dest = app.path.with_extension(EXT_PROOF);
        fs::write(&dest, serde_json::to_string_pretty(&out)?)
            .with_context(|| format!("Failed to write {}", dest.display()))?;
    }
    Ok(())
}

#[derive(Serialize)]
struct SerializedRootPacket {
    // For humans only, e.g. "1793895710 (2026-11-05 16:21:50+00:00)"
    timestamp: String,
    root_rings: Vec<String>,
    root_packet: String,
}

/// Writes the rootpacket covering `rings` to `path`. If none of the rings has
/// any apps, the rootpacket is not needed and a stale one is removed instead.
fn write_root_packet(
    path: &Path,
    rings: &[u8],
    ring_roots: &[Option<[u8; 32]>; MAX_RINGS],
    timestamp: i64,
) -> Result<()> {
    if rings
        .iter()
        .all(|&ring| ring_roots[usize::from(ring)].is_none())
    {
        return remove_file_if_exists(path);
    }

    // A ring without apps gets an all-zero root, so the rootpacket size does
    // not depend on which rings have apps.
    let root_rings: Vec<(u8, [u8; 32])> = rings
        .iter()
        .map(|&ring| (ring, ring_roots[usize::from(ring)].unwrap_or([0; 32])))
        .collect();
    let mut packet = RootPacket::new(&root_rings, timestamp);
    packet.sign(&DEV_MLDSA_SEEDS)?;

    let out = SerializedRootPacket {
        timestamp: format!("{timestamp} ({})", format_utc(timestamp)),
        root_rings: packet
            .root_rings()
            .iter()
            .map(|root| to_hex(root))
            .collect(),
        root_packet: BASE64_STANDARD.encode(packet.to_bytes()),
    };
    fs::write(path, serde_json::to_string_pretty(&out)?)
        .with_context(|| format!("Failed to write {}", path.display()))?;
    println!(
        "Dev-signed RootPacket (timestamp {timestamp}) written to {}",
        path.display()
    );
    Ok(())
}

// Version, SDK version and rootpacket path of a release
type ReleaseKey = ([u8; 4], [u8; 4], String);

#[derive(Serialize)]
struct AppIndex {
    id: String,
    releases: Vec<Release>,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct Release {
    version: [u8; 4],
    sdk_version: [u8; 4],
    root_packet: String,
    builds: Vec<Build>,
}

#[derive(Serialize)]
struct Build {
    abi: Abi,
    model: String,
    language: String,
    file: String,
    proof: String,
    sha256: String,
    fingerprint: String,
}

#[derive(Serialize)]
struct Abi {
    platform: String,
    version: u8,
}

/// Writes `<id>/index.v1.json` for every app id with serialized apps, and
/// removes the index of app directories that no longer have any. Returns the
/// sorted ids of the written indices.
fn create_app_indices(serialized_dir: &Path, app_infos: &[AppInfo]) -> Result<Vec<String>> {
    // App id -> release -> builds, both kept sorted
    let mut indices: BTreeMap<String, BTreeMap<ReleaseKey, Vec<Build>>> = BTreeMap::new();
    for app in app_infos {
        let header = &app.header;
        let app_dir = serialized_dir.join(header.id()?);
        let release = (
            header.version(),
            header.sdk_version(),
            format!(
                "../{ROOT_PACKET_DIR}/{}",
                root_packet_file(header.app_ring())?
            ),
        );
        let build = Build {
            abi: Abi {
                platform: header.target_arch()?.name().to_string(),
                version: header.abi_version(),
            },
            model: header.model()?.to_string(),
            language: header.language()?.name().to_string(),
            file: index_path(&app.path, &app_dir)?,
            proof: index_path(&app.path.with_extension(EXT_PROOF), &app_dir)?,
            sha256: to_hex(&app.sha256),
            fingerprint: to_hex(&app.digest),
        };
        indices
            .entry(header.id()?.to_string())
            .or_default()
            .entry(release)
            .or_default()
            .push(build);
    }

    for app_dir in subdirectories(serialized_dir)? {
        let has_apps = app_dir
            .file_name()
            .and_then(|name| name.to_str())
            .is_some_and(|id| indices.contains_key(id));
        if !has_apps {
            remove_file_if_exists(&app_dir.join(INDEX_FILENAME))?;
        }
    }

    let app_ids = indices.keys().cloned().collect();
    for (id, releases) in indices {
        let releases = releases
            .into_iter()
            .map(|((version, sdk_version, root_packet), mut builds)| {
                // By model, then device before emulator builds, then ABI and language
                builds.sort_by(|a, b| {
                    (&a.model, &a.abi.platform, a.abi.version, &a.language).cmp(&(
                        &b.model,
                        &b.abi.platform,
                        b.abi.version,
                        &b.language,
                    ))
                });
                Release {
                    version,
                    sdk_version,
                    root_packet,
                    builds,
                }
            })
            .collect();
        let path = serialized_dir.join(&id).join(INDEX_FILENAME);
        let out = AppIndex { id, releases };
        fs::write(&path, serde_json::to_string_pretty(&out)?)
            .with_context(|| format!("Failed to write {}", path.display()))?;
    }
    Ok(app_ids)
}

#[derive(Serialize)]
struct MainIndex {
    apps: BTreeMap<String, String>,
}

/// Writes the main `index.v1.json`, pointing to the index of each app.
fn write_main_index(serialized_dir: &Path, app_ids: &[String]) -> Result<()> {
    let out = MainIndex {
        apps: app_ids
            .iter()
            .map(|id| (id.clone(), format!("{id}/{INDEX_FILENAME}")))
            .collect(),
    };
    let path = serialized_dir.join(INDEX_FILENAME);
    fs::write(&path, serde_json::to_string_pretty(&out)?)
        .with_context(|| format!("Failed to write {}", path.display()))
}

fn root_packet_file(app_ring: u8) -> Result<String> {
    let (name, _) = ROOT_PACKETS
        .iter()
        .find(|(_, rings)| rings.contains(&app_ring))
        .with_context(|| format!("No rootpacket covers app ring {app_ring}"))?;
    Ok(format!("{name}.{EXT_ROOTPACKET}"))
}

// `path` relative to `dir`, with `/` separators on every platform
fn index_path(path: &Path, dir: &Path) -> Result<String> {
    let relative = path
        .strip_prefix(dir)
        .with_context(|| format!("{} is not in {}", path.display(), dir.display()))?;
    let parts = relative
        .components()
        .map(|part| {
            part.as_os_str()
                .to_str()
                .with_context(|| format!("Path {} is not valid UTF-8", path.display()))
        })
        .collect::<Result<Vec<_>>>()?;
    Ok(parts.join("/"))
}

fn remove_file_if_exists(path: &Path) -> Result<()> {
    match fs::remove_file(path) {
        Err(err) if err.kind() == std::io::ErrorKind::NotFound => Ok(()),
        result => result.with_context(|| format!("Failed to remove {}", path.display())),
    }
}

fn subdirectories(dir: &Path) -> Result<Vec<PathBuf>> {
    let mut dirs = Vec::new();
    for entry in fs::read_dir(dir).with_context(|| format!("Failed to read {}", dir.display()))? {
        let path = entry?.path();
        if path.is_dir() {
            dirs.push(path);
        }
    }
    Ok(dirs)
}

fn to_hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

/// Formats a Unix timestamp as a UTC date, e.g. `2026-11-05 16:21:50+00:00`.
fn format_utc(timestamp: i64) -> String {
    let (year, month, day) = civil_from_days(timestamp.div_euclid(86400));
    let seconds = timestamp.rem_euclid(86400);
    format!(
        "{year:04}-{month:02}-{day:02} {:02}:{:02}:{:02}+00:00",
        seconds / 3600,
        seconds % 3600 / 60,
        seconds % 60
    )
}

/// Converts days since 1970-01-01 into a (year, month, day) date, using
/// Howard Hinnant's `civil_from_days` algorithm
/// (https://howardhinnant.github.io/date_algorithms.html#civil_from_days).
fn civil_from_days(days: i64) -> (i64, i64, i64) {
    // Shift the epoch to 0000-03-01, so that the leap day ends a year
    let days = days + 719468;
    let era = days.div_euclid(146097);
    let day_of_era = days.rem_euclid(146097);
    let year_of_era =
        (day_of_era - day_of_era / 1460 + day_of_era / 36524 - day_of_era / 146096) / 365;
    let day_of_year = day_of_era - (365 * year_of_era + year_of_era / 4 - year_of_era / 100);
    let month_from_march = (5 * day_of_year + 2) / 153;
    let day = day_of_year - (153 * month_from_march + 2) / 5 + 1;
    let month = if month_from_march < 10 {
        month_from_march + 3
    } else {
        month_from_march - 9
    };
    let year = era * 400 + year_of_era + i64::from(month <= 2);
    (year, month, day)
}

#[cfg(test)]
mod tests {
    use super::*;
    use fips204::ml_dsa_44;
    use fips204::traits::{KeyGen, SerDes};

    #[test]
    fn dev_seeds_match_firmware_dev_keys() {
        // SHA-256 of the dev public keys in core/embed/io/app_arena/root_packet.c
        let firmware_key_hashes = [
            "b9c0314b59bee4bca5e80cb5ee1e1ab70488d8274d44d0ae6763c8ef29a0d1d5",
            "e44dca1fbe17c3f566fe6b234c1ff2b87cfc93446c5b05840db0b6da806727a5",
        ];
        for (seed, expected) in DEV_MLDSA_SEEDS.iter().zip(firmware_key_hashes) {
            let (public_key, _) = ml_dsa_44::KG::keygen_from_seed(seed);
            assert_eq!(to_hex(&Sha256::digest(public_key.into_bytes())), expected);
        }
    }

    const CHUNK_SIZE: usize = 4;

    // Chunks of `payload` as written to a .tapp, with the matching chunk_hash
    fn serialized_chunks(payload: &[u8]) -> (Vec<(String, String)>, [u8; 32]) {
        let hashes = image::hash_chain(payload, CHUNK_SIZE);
        let chunks = payload
            .chunks(CHUNK_SIZE)
            .zip(&hashes[1..])
            .map(|(chunk, hash)| (to_hex(hash), BASE64_STANDARD.encode(chunk)))
            .collect();
        (chunks, hashes[0])
    }

    #[test]
    fn valid_chunks_pass() {
        let (chunks, chunk_hash) = serialized_chunks(b"abcdefghij");
        check_chunks(&chunks, CHUNK_SIZE, 10, chunk_hash).unwrap();
        let (chunks, chunk_hash) = serialized_chunks(b"");
        check_chunks(&chunks, CHUNK_SIZE, 0, chunk_hash).unwrap();
    }

    #[test]
    fn tampered_chunk_fails() {
        let (mut chunks, chunk_hash) = serialized_chunks(b"abcdefghij");
        chunks[1].1 = BASE64_STANDARD.encode(b"EFGH");
        assert!(check_chunks(&chunks, CHUNK_SIZE, 10, chunk_hash).is_err());
    }

    #[test]
    fn tampered_chunk_hash_fails() {
        let (mut chunks, chunk_hash) = serialized_chunks(b"abcdefghij");
        chunks[0].0 = to_hex(&[0; 32]);
        assert!(check_chunks(&chunks, CHUNK_SIZE, 10, chunk_hash).is_err());
    }

    #[test]
    fn missing_last_chunk_fails() {
        // Cut on a chunk boundary: only `code_size` notices
        let (chunks, _) = serialized_chunks(b"abcdefghij");
        let (_, truncated_hash) = serialized_chunks(b"abcdefgh");
        assert!(check_chunks(&chunks[..2], CHUNK_SIZE, 10, truncated_hash).is_err());
    }

    #[test]
    fn wrongly_cut_chunks_fail() {
        let (mut chunks, chunk_hash) = serialized_chunks(b"abcdefghij");
        chunks[0].1 = BASE64_STANDARD.encode(b"abc");
        chunks[1].1 = BASE64_STANDARD.encode(b"defgh");
        assert!(check_chunks(&chunks, CHUNK_SIZE, 10, chunk_hash).is_err());
    }
}
