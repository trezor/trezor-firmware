use xbuild::{CLibrary, CompileAttrs, Result, bail};

use std::path::PathBuf;

mod build_legacy;

const CRYPTO_PATH: &str = "../../vendor/trezor-crypto";
const SECP256K1_PATH: &str = "../../vendor/secp256k1-zkp";
const SPHINCSPLUS_PATH: &str = "../../vendor/sphincsplus/ref";
const MLDSA_PATH: &str = "../../vendor/mldsa-native/mldsa";

fn main() -> Result<()> {
    if cfg!(not(feature = "with_new_crates")) {
        build_legacy::legacy_main();
        return Ok(());
    }

    xbuild::build(|lib| {
        lib.import_lib("rtl")?;

        lib.add_include("inc");

        let attrs = CompileAttrs::new()
            .with_flag("-ftrivial-auto-var-init=zero")
            .with_flag("-ffreestanding");

        add_crypto_base(lib, &attrs)?;

        if cfg!(feature = "insecure_prng") {
            add_insecure_prng(lib)?;
        }

        if cfg!(feature = "aes_gcm") {
            add_aes_gcm(lib, &attrs)?;
        }

        if cfg!(feature = "noise") {
            add_noise(lib, &attrs)?;
        }

        if cfg!(feature = "secp256k1_zkp") {
            add_secp256k1_zkp(lib, &attrs)?;
        }

        if cfg!(feature = "sphincsplus") {
            add_sphincsplus(lib, &attrs)?;
        }

        if cfg!(feature = "mldsa") {
            add_mldsa(lib, &attrs)?;
        }

        if cfg!(feature = "test") {
            lib.add_source("src/test_setup.c");
        }

        Ok(())
    })
}

fn add_crypto_base(lib: &mut CLibrary, common_attrs: &CompileAttrs) -> Result<()> {
    lib.add_include(CRYPTO_PATH);

    lib.add_defines([
        ("AES_128", None),
        ("AES_192", None),
        ("USE_KECCAK", Some("1")),
        ("USE_BIP32_CACHE", Some("0")),
    ]);

    if cfg!(feature = "ed25519_no_precomp") {
        lib.add_define("ED25519_NO_PRECOMP", None);
    }

    lib.add_sources_in_dir_with_attrs(
        CRYPTO_PATH,
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
            "consteq.c",
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
        Some(common_attrs.clone()),
    );

    let val = cfg!(feature = "universal_fw");
    let val = Some(if val { "1" } else { "0" });
    lib.add_defines([
        ("USE_ETHEREUM", val),
        ("USE_MONERO", val),
        ("USE_CARDANO", val),
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

    if cfg!(feature = "universal_fw") {
        lib.add_sources_in_dir_with_attrs(
            CRYPTO_PATH,
            [
                "cardano.c",
                "monero/base58.c",
                "monero/serialize.c",
                "monero/xmr.c",
            ],
            Some(common_attrs.clone()),
        );
    }

    lib.add_rust_bindings(|builder| {
        Ok(builder
            .header(format!("{CRYPTO_PATH}/ed25519-donna/ed25519.h"))
            .header(format!("{CRYPTO_PATH}/elligator2.h"))
            .header(format!("{CRYPTO_PATH}/hmac.h"))
            .header(format!("{CRYPTO_PATH}/sha2.h"))
            // curve25519
            .allowlist_function("curve25519_scalarmult")
            .allowlist_function("curve25519_scalarmult_basepoint")
            // ed25519
            .allowlist_type("ed25519_signature")
            .allowlist_type("ed25519_public_key")
            .allowlist_function("ed25519_cosi_combine_publickeys")
            .allowlist_function("ed25519_sign_open")
            // elligator2
            .allowlist_function("map_to_curve_elligator2_curve25519")
            // hmac
            .allowlist_type("HMAC_SHA256_CTX")
            .no_copy("HMAC_SHA256_CTX")
            .allowlist_function("hmac_sha256_Init")
            .allowlist_function("hmac_sha256_Update")
            .allowlist_function("hmac_sha256_Final")
            // sha256
            .allowlist_var("SHA256_DIGEST_LENGTH")
            .allowlist_type("SHA256_CTX")
            .no_copy("SHA256_CTX")
            .allowlist_function("sha256_Init")
            .allowlist_function("sha256_Update")
            .allowlist_function("sha256_Final")
            // sha512
            .allowlist_var("SHA512_DIGEST_LENGTH")
            .allowlist_type("SHA512_CTX")
            .no_copy("SHA512_CTX")
            .allowlist_function("sha512_Init")
            .allowlist_function("sha512_Update")
            .allowlist_function("sha512_Final"))
    })?;

    Ok(())
}

fn add_insecure_prng(lib: &mut CLibrary) -> Result<()> {
    if cfg!(feature = "production") {
        if !xbuild::is_rust_analyzer() {
            bail!("insecure_prng cannot be enabled in production builds");
        }
    }
    lib.add_define("USE_INSECURE_PRNG", Some("1"));
    lib.add_source(PathBuf::from(CRYPTO_PATH).join("rand_insecure.c"));

    Ok(())
}

fn add_aes_gcm(lib: &mut CLibrary, attrs: &CompileAttrs) -> Result<()> {
    lib.add_defines([("AES_VAR", None), ("USE_AES_GCM", Some("1"))]);

    lib.add_sources_in_dir_with_attrs(
        CRYPTO_PATH,
        ["aes/gf128mul.c", "aes/aesgcm.c"],
        Some(attrs.clone()),
    );

    lib.add_rust_bindings(|builder| {
        Ok(builder
            .header(format!("{CRYPTO_PATH}/aes/aesgcm.h"))
            .allowlist_type("gcm_ctx")
            .no_copy("gcm_ctx")
            .allowlist_function("gcm_init_and_key")
            .allowlist_function("gcm_init_message")
            .allowlist_function("gcm_encrypt")
            .allowlist_function("gcm_decrypt")
            .allowlist_function("gcm_auth_header")
            .allowlist_function("gcm_compute_tag"))
    })?;

    Ok(())
}

fn add_noise(lib: &mut CLibrary, attrs: &CompileAttrs) -> Result<()> {
    lib.add_sources_in_dir_with_attrs(CRYPTO_PATH, ["noise.c"], Some(attrs.clone()));

    Ok(())
}

fn add_secp256k1_zkp(lib: &mut CLibrary, _attrs: &CompileAttrs) -> Result<()> {
    // let attrs = attrs.clone().with_flag("-Wno-unused-function");
    let attrs = CompileAttrs::new()
        .with_flag("-ffreestanding")
        .with_flag("-Wno-unused-function");

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
    // lib.add_include(PathBuf::from(SECP256K1_PATH).join("include"));
    lib.add_include("../.."); // points to vendor folder

    if cfg!(feature = "emulator") {
        lib.add_define("SECP256K1_CONTEXT_SIZE", Some("208"));
    } else {
        lib.add_define("SECP256K1_CONTEXT_SIZE", Some("180"));
        lib.add_define("USE_EXTERNAL_ASM", None);
        lib.add_sources_in_dir(SECP256K1_PATH, ["src/asm/field_10x26_arm.s"]);
    }

    lib.add_sources_in_dir_with_attrs(
        SECP256K1_PATH,
        [
            "src/secp256k1.c",
            "src/precomputed_ecmult.c",
            "src/precomputed_ecmult_gen.c",
        ],
        Some(attrs.clone()),
    );

    lib.add_sources_in_dir_with_attrs(
        CRYPTO_PATH,
        ["zkp_context.c", "zkp_ecdsa.c", "zkp_bip340.c"],
        Some(attrs.clone()),
    );
    Ok(())
}

fn add_sphincsplus(lib: &mut CLibrary, attrs: &CompileAttrs) -> Result<()> {
    lib.add_include(SPHINCSPLUS_PATH);

    lib.add_define("PARAMS", Some("sphincs-sha2-128s"));

    let attrs = attrs.clone().with_flag("-Wno-incompatible-pointer-types");

    lib.add_sources_in_dir_with_attrs(
        SPHINCSPLUS_PATH,
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
    Ok(())
}

fn add_mldsa(lib: &mut CLibrary, attrs: &CompileAttrs) -> Result<()> {
    lib.add_include(MLDSA_PATH);

    lib.add_defines([
        ("MLD_CONFIG_NAMESPACE_PREFIX", Some("mldsa")),
        ("MLD_CONFIG_NO_RANDOMIZED_API", Some("1")),
    ]);

    lib.add_sources_in_dir_with_attrs(
        MLDSA_PATH,
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
        Some(attrs.clone()),
    );

    Ok(())
}
