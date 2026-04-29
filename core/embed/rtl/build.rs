use xbuild::{Result, WrapErr, bail, ensure};

use std::{path::PathBuf, process::Command};

fn main() -> Result<()> {
    xbuild::build(|lib| {
        lib.import_lib("models")?;

        lib.add_include("inc");

        lib.add_define("SCM_REVISION_SHORT_INIT", Some(&get_scm_revision_short()?));

        lib.add_sources([
            "cli.c",
            "error_handling.c",
            "scm_revision.c",
            "strutils.c",
            "unit_test.c",
        ]);

        if cfg!(not(feature = "production")) {
            lib.add_source("printf.c");
        }

        add_crypto(lib)?;

        add_uzlib(lib);

        Ok(())
    })
}

/// Extracts the first four bytes of the Git revision and formats them
/// as a C initializer list, e.g. {0x12, 0x34, 0x56, 0x78}.
fn get_scm_revision_short() -> Result<String> {
    let git_output = Command::new("git")
        .args(["rev-parse", "HEAD"])
        .output()
        .context("Failed to execute git command")?;

    ensure!(
        git_output.status.success(),
        "Git command failed: {}",
        String::from_utf8_lossy(&git_output.stderr)
    );

    let git_hash = String::from_utf8_lossy(&git_output.stdout);
    let git_hash = git_hash.trim();

    ensure!(
        git_hash.len() >= 8 && git_hash.chars().all(|c| c.is_ascii_hexdigit()),
        "Unexpected git hash format: {}",
        git_hash
    );

    let init_val = git_hash.as_bytes()[..4]
        .chunks(2)
        .map(|chunk| {
            format!(
                "0x{},",
                std::str::from_utf8(chunk).expect("git hash must be valid ASCII")
            )
        })
        .collect::<String>();

    Ok(format!("{{{}}}", init_val))
}

fn add_crypto(lib: &mut xbuild::CLibrary) -> Result<()> {
    let crypto_path = "../../vendor/trezor-crypto";

    lib.add_include(crypto_path);

    lib.add_defines([
        ("AES_128", None),
        ("AES_192", None),
        ("USE_KECCAK", Some("1")),
        ("USE_BIP32_CACHE", Some("0")),
    ]);

    let val = cfg!(feature = "universal_fw");
    let val = Some(if val { "1" } else { "0" });
    lib.add_defines([
        ("USE_ETHEREUM", val),
        ("USE_MONERO", val),
        ("USE_CARDANO", val),
    ]);

    let nem = cfg!(feature = "universal_fw") && cfg!(feature = "nem");
    lib.add_define("USE_NEM", Some(if nem { "1" } else { "0" }));
    let eos = cfg!(feature = "universal_fw") && cfg!(feature = "eos");
    lib.add_define("USE_EOS", Some(if eos { "1" } else { "0" }));

    if cfg!(feature = "ed25519_no_precomp") {
        lib.add_define("ED25519_NO_PRECOMP", None);
    }

    let crypto_attrs = xbuild::CompileAttrs::new().with_flag("-ftrivial-auto-var-init=zero");

    lib.add_sources_from_folder_with_attrs(
        crypto_path,
        [
            "address.c",
            "aes/aes_modes.c",
            "aes/aesccm.c",
            "aes/aescrypt.c",
            "aes/aeskey.c",
            "aes/aestab.c",
            "base32.c",
            "base58.c",
            "bignum.c",
            "bip32.c",
            "bip39.c",
            "bip39_english.c",
            "blake256.c",
            "blake2b.c",
            "blake2s.c",
            "buffer.c",
            "chacha20poly1305/chacha20poly1305.c",
            "chacha20poly1305/chacha_merged.c",
            "chacha20poly1305/poly1305-donna.c",
            "chacha20poly1305/rfc7539.c",
            "chacha_drbg.c",
            "curves.c",
            "der.c",
            "ecdsa.c",
            "ed25519-donna/curve25519-donna-32bit.c",
            "ed25519-donna/curve25519-donna-helpers.c",
            "ed25519-donna/curve25519-donna-scalarmult-base.c",
            "ed25519-donna/ed25519-donna-32bit-tables.c",
            "ed25519-donna/ed25519-donna-basepoint-table.c",
            "ed25519-donna/ed25519-donna-impl-base.c",
            "ed25519-donna/ed25519-keccak.c",
            "ed25519-donna/ed25519-sha3.c",
            "ed25519-donna/ed25519.c",
            "ed25519-donna/modm-donna-32bit.c",
            "elligator2.c",
            "groestl.c",
            "hash_to_curve.c",
            "hasher.c",
            "hmac.c",
            "hmac_drbg.c",
            "memzero.c",
            "nem.c",
            "nist256p1.c",
            "pbkdf2.c",
            "rand.c",
            "rfc6979.c",
            "ripemd160.c",
            "secp256k1.c",
            "segwit_addr.c",
            "sha2.c",
            "sha3.c",
            "shamir.c",
            "slip39.c",
            "slip39_english.c",
            "tls_prf.c",
        ],
        Some(crypto_attrs.clone()),
    );

    if cfg!(feature = "universal_fw") {
        lib.add_sources_from_folder_with_attrs(
            crypto_path,
            [
                "cardano.c",
                "monero/base58.c",
                "monero/serialize.c",
                "monero/xmr.c",
            ],
            Some(crypto_attrs.clone()),
        );
    }

    if cfg!(feature = "insecure_prng") {
        if cfg!(feature = "production") {
            bail!("insecure_prng cannot be enabled in production builds");
        }
        lib.add_define("USE_INSECURE_PRNG", Some("1"));
        lib.add_source(PathBuf::from(crypto_path).join("rand_insecure.c"));
    }

    if cfg!(feature = "aes_gcm") {
        lib.add_defines([("AES_VAR", None), ("USE_AES_GCM", Some("1"))]);

        lib.add_sources_from_folder_with_attrs(
            crypto_path,
            ["aes/gf128mul.c", "aes/aesgcm.c"],
            Some(crypto_attrs.clone()),
        );
    }

    if cfg!(feature = "noise") {
        lib.add_sources_from_folder_with_attrs(
            crypto_path,
            ["noise.c"],
            Some(crypto_attrs.clone()),
        );
    }

    if cfg!(feature = "secp256k1_zkp") {
        let secp256k1_path = "../../vendor/secp256k1-zkp";

        lib.add_defines([
            ("USE_SECP256K1_ZKP", None),
            ("USE_SECP256K1_ZKP_ECDSA", None),
            ("USE_EXTERNAL_DEFAULT_CALLBACKS", None),
            ("ECMULT_GEN_PREC_BITS", Some("2")),
            ("ECMULT_WINDOW_SIZE", Some("2")),
            ("ENABLE_MODULE_GENERATOR", None),
            ("ENABLE_MODULE_RECOVERY", None),
            ("ENABLE_MODULE_SCHNORRSIG", None),
            ("ENABLE_MODULE_EXTRAKEYS", None),
            ("ENABLE_MODULE_ECDH", None),
        ]);

        // TODO get rid of #include <vendor/... includes in crypto/zkp_*.c
        // lib.add_include(PathBuf::from(secp256k1_path).join("include"));
        lib.add_include("../.."); // points to vendor folder

        if cfg!(feature = "emulator") {
            lib.add_define("SECP256K1_CONTEXT_SIZE", Some("208"));
            lib.add_sources_from_folder(crypto_path, ["rand_insecure.c"]);
        } else {
            lib.add_define("SECP256K1_CONTEXT_SIZE", Some("180"));
            lib.add_define("USE_EXTERNAL_ASM", None);
            lib.add_sources_from_folder(secp256k1_path, ["src/asm/field_10x26_arm.s"]);
        }

        lib.add_sources_from_folder_with_attrs(
            secp256k1_path,
            [
                "src/secp256k1.c",
                "src/precomputed_ecmult.c",
                "src/precomputed_ecmult_gen.c",
            ],
            Some(crypto_attrs.clone()),
        );

        lib.add_sources_from_folder_with_attrs(
            crypto_path,
            ["zkp_context.c", "zkp_ecdsa.c", "zkp_bip340.c"],
            Some(crypto_attrs.clone()),
        );
    }

    if cfg!(feature = "sphincsplus") {
        let sphincsplus_path = "../../vendor/sphincsplus/ref";

        lib.add_include(sphincsplus_path);

        lib.add_define("PARAMS", Some("sphincs-sha2-128s"));

        let attrs = xbuild::CompileAttrs::new()
            .with_flag("-Wno-incompatible-pointer-types")
            .with_flag("-ftrivial-auto-var-init=zero");

        lib.add_sources_from_folder_with_attrs(
            sphincsplus_path,
            [
                "address.c",
                "fors.c",
                "hash_sha2.c",
                "sha2.c",
                "sign.c",
                "thash_sha2_simple.c",
                "utils.c",
                "wots.c",
            ],
            Some(attrs),
        );
    }

    if cfg!(feature = "mldsa") {
        let mldsa_path = "../../vendor/mldsa-native/mldsa";

        lib.add_include(mldsa_path);

        lib.add_defines([
            ("MLD_CONFIG_NAMESPACE_PREFIX", Some("mldsa")),
            ("MLD_CONFIG_NO_RANDOMIZED_API", Some("1")),
        ]);

        lib.add_sources_from_folder_with_attrs(
            mldsa_path,
            [
                "src/fips202/fips202.c",
                "src/fips202/fips202x4.c",
                "src/fips202/keccakf1600.c",
                "src/packing.c",
                "src/poly.c",
                "src/poly_kl.c",
                "src/polyvec.c",
                "src/sign.c",
            ],
            Some(crypto_attrs.clone()),
        );
    }

    Ok(())
}

fn add_uzlib(lib: &mut xbuild::CLibrary) {
    let uzlib_path = "../../vendor/micropython/lib/uzlib";

    lib.add_include(uzlib_path);

    lib.add_sources_from_folder(uzlib_path, ["adler32.c", "crc32.c", "tinflate.c"]);
}
