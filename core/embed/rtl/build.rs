use xbuild::{Result, WrapErr, bail};

use std::{path::PathBuf, process::Command};

fn main() -> Result<()> {
    xbuild::build(|lib| {
        lib.import_lib("models")?;

        lib.add_include("inc");

        // !@# can we leave SCM_REVISION in kernel/secmon?
        lib.add_define("SCM_REVISION_INIT", Some(&get_scm_revision()?));

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

fn get_scm_revision() -> Result<String> {
    let git_output = Command::new("git")
        .args(["rev-parse", "HEAD"])
        .output()
        .context("Failed to execute git command")?;

    if !git_output.status.success() {
        bail!("{}", String::from_utf8_lossy(&git_output.stderr));
    }

    let git_hash = String::from_utf8_lossy(&git_output.stdout);
    let git_hash = git_hash.trim();

    if git_hash.len() != 40 && !git_hash.chars().all(|c| c.is_ascii_hexdigit()) {
        bail!("Unexpected git hash format: {}", git_hash);
    }

    let scm_revision_init = git_hash
        .as_bytes()
        .chunks(2)
        .map(|chunk| {
            format!(
                "0x{},",
                std::str::from_utf8(chunk).expect("git hash must be valid ASCII")
            )
        })
        .collect::<String>();

    Ok(format!("{{{}}}", scm_revision_init))
}

fn add_crypto(lib: &mut xbuild::CLibrary) -> Result<()> {
    let crypto_path = "../../vendor/trezor-crypto";

    lib.add_include(crypto_path);

    lib.add_define("USE_BIP32_CACHE", Some("0")); // TODO!@# conditional??

    lib.add_defines([
        ("AES_128", None),
        ("AES_192", None),
        ("USE_KECCAK", Some("1")),
    ]);

    let val = cfg!(feature = "universal_fw");
    let val = Some(if val { "1" } else { "0" });
    lib.add_defines([
        ("USE_ETHEREUM", val),
        ("USE_MONERO", val),
        ("USE_CARDANO", val),
    ]);

    let val = cfg!(feature = "universal_fw") && cfg!(feature = "model_t2t1");
    let val = Some(if val { "1" } else { "0" });
    lib.add_defines([("USE_NEM", val), ("USE_EOS", val)]);

    let mut crypto_attrs = xbuild::CompileAttrs::default();
    crypto_attrs.add_flag("-ftrivial-auto-var-init=zero");

    if cfg!(feature = "ed25519_no_precomp") {
        lib.add_define("ED25519_NO_PRECOMP", None);
    }

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
        Some(crypto_attrs),
    );

    if cfg!(feature = "universal_fw") {
        lib.add_sources_from_folder(
            crypto_path,
            [
                "cardano.c",
                "monero/base58.c",
                "monero/serialize.c",
                "monero/xmr.c",
            ],
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

        lib.add_sources_from_folder(crypto_path, ["aes/gf128mul.c", "aes/aesgcm.c"]);
    }

    if cfg!(feature = "noise") {
        lib.add_sources_from_folder(crypto_path, ["noise.c"]);
    }

    if cfg!(feature = "secp256k1_zkp") {
        let secp256k1_path = "../../vendor/secp256k1-zkp";

        lib.add_defines([
            ("USE_SECP256K1_ZKP", None),
            ("USE_SECP256K1_ZKP_ECDSA", None),
            ("USE_ASM_ARM", None),      // !@# hw only
            ("USE_EXTERNAL_ASM", None), // !@# hw only
            ("USE_EXTERNAL_DEFAULT_CALLBACKS", None),
            ("ECMULT_GEN_PREC_BITS", Some("2")),
            ("ECMULT_WINDOW_SIZE", Some("2")),
            ("ENABLE_MODULE_GENERATOR", None),
            ("ENABLE_MODULE_RECOVERY", None),
            ("ENABLE_MODULE_SCHNORRSIG", None),
            ("ENABLE_MODULE_EXTRAKEYS", None),
            ("ENABLE_MODULE_ECDH", None),
        ]);

        lib.add_include(PathBuf::from(secp256k1_path).join("include"));

        if cfg!(feature = "emulator") {
            lib.add_define("SECP256K1_CONTEXT_SIZE", Some("208"));

            lib.add_sources_from_folder(crypto_path, ["rand_insecure.c"]);
        } else {
            lib.add_define("SECP256K1_CONTEXT_SIZE", Some("180"));

            lib.add_sources_from_folder(secp256k1_path, ["src/asm/field_10x26_arm.s"]);
        }

        let mut secp256k1_attrs = xbuild::CompileAttrs::default();
        secp256k1_attrs.add_flag("-Wno-unused-function"); // !@# is this really needed

        lib.add_sources_from_folder_with_attrs(
            secp256k1_path,
            [
                "src/secp256k1.c",
                "src/precomputed_ecmult.c",
                "src/precomputed_ecmult_gen.c",
            ],
            Some(secp256k1_attrs),
        );

        lib.add_sources_from_folder(
            crypto_path,
            ["zkp_context.c", "zkp_ecdsa.c", "zkp_bip340.c"],
        );
    }

    if cfg!(feature = "sphincsplus") {
        let sphincsplus_path = "../../vendor/sphincsplus/ref";

        lib.add_include(sphincsplus_path);

        lib.add_define("PARAMS", Some("sphincs-sha2-128s"));

        let mut sphicsplus_attrs = xbuild::CompileAttrs::default();
        sphicsplus_attrs.add_flag("-Wno-incompatible-pointer-types");

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
            Some(sphicsplus_attrs),
        );
    }

    if cfg!(feature = "mldsa") {
        let mldsa_path = "../../vendor/mldsa-native/mldsa";

        lib.add_include(mldsa_path);

        lib.add_sources_from_folder(
            mldsa_path,
            [
                "fips202/fips202.c",
                "fips202/fips202x4.c",
                "fips202/keccakf1600.c",
                "ntt.c",
                "packing.c",
                "poly.c",
                "polyvec.c",
                "sign.c",
            ],
        );
    }

    Ok(())
}

fn add_uzlib(lib: &mut xbuild::CLibrary) {
    let uzlib_path = "../../vendor/micropython/lib/uzlib";

    lib.add_include(uzlib_path);

    lib.add_sources_from_folder(uzlib_path, ["adler32.c", "crc32.c", "tinflate.c"]);
}
