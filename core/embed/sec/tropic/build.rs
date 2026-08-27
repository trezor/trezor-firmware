use std::env;
use std::path::PathBuf;

use xbuild::{CLibrary, Result, bail, bail_unsupported, cargo_out};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("tropic/inc");

    lib.add_define("USE_TROPIC", Some("1"));

    let tropic_dir = PathBuf::from("../../vendor/libtropic");

    if cfg!(feature = "emulator") {
        lib.add_sources(["tropic/unix/tropic01.c", "tropic/unix/tropic_mock.c"]);

        lib.add_sources_in_dir(&tropic_dir, ["hal/posix/tcp/libtropic_port_posix_tcp.c"]);
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_sources(["tropic/stm32/tropic01.c"]);
    } else {
        bail_unsupported!();
    }

    cargo_out::rerun_if_env_changed("TROPIC_SILICON_REVISION");
    let rev = env::var("TROPIC_SILICON_REVISION").unwrap_or_else(|_| "ACAB".into());
    let (rev_define, fw_dir) = match rev.as_str() {
        "ABAB" => ("LT_SILICON_REV_ABAB", "boot_v_1_0_1"),
        "ACAB" => ("LT_SILICON_REV_ACAB", "boot_v_2_0_1"),
        other => bail!("Unsupported TROPIC_SILICON_REVISION={other}"),
    };
    lib.add_define(rev_define, Some("1"));

    lib.add_sources(["tropic/tropic.c", "tropic/config/tropic_configs.c"]);

    lib.add_sources_in_dir(
        &tropic_dir,
        [
            "cal/trezor_crypto/lt_trezor_crypto_aesgcm.c",
            "cal/trezor_crypto/lt_trezor_crypto_common.c",
            "cal/trezor_crypto/lt_trezor_crypto_hmac_sha256.c",
            "cal/trezor_crypto/lt_trezor_crypto_sha256.c",
            "cal/trezor_crypto/lt_trezor_crypto_x25519.c",
            "src/libtropic.c",
            "src/libtropic_l2.c",
            "src/libtropic_l3.c",
            "src/lt_asn1_der.c",
            "src/lt_crc16.c",
            "src/lt_hkdf.c",
            "src/lt_l1.c",
            "src/lt_l2_frame_check.c",
            "src/lt_l3_process.c",
            "src/lt_port_wrap.c",
            "src/lt_tr01_attrs.c",
        ],
    );

    lib.add_includes([
        tropic_dir.join("include"),
        tropic_dir.join("src"),
        tropic_dir
            .join("TROPIC01_fw_update_files")
            .join(fw_dir)
            .join("fw_v_2_1_0"),
    ]);

    lib.add_defines([
        ("LT_USE_TREZOR_CRYPTO", Some("1")),
        ("LT_HELPERS", Some("1")),
        ("LT_L1_READ_RETRY_DELAY_MS", Some("1")),
        ("LT_L1_READ_MAX_TRIES", Some("1250")),
    ]);

    if cfg!(feature = "tropic_logging") {
        lib.add_defines([
            ("LT_LOG_ENABLE_ERROR", Some("1")),
            ("USE_TROPIC_LOGGING", Some("1")),
        ]);
    }

    Ok(())
}
