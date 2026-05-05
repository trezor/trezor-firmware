use xbuild::{CLibrary, Result, bail_unsupported};

use std::path::PathBuf;

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("tropic/inc");

    lib.add_define("USE_TROPIC", Some("1"));

    let tropic_dir = PathBuf::from("../../vendor/libtropic");

    if cfg!(feature = "emulator") {
        lib.add_sources(["tropic/unix/tropic01.c"]);

        lib.add_sources_from_folder(&tropic_dir, ["hal/posix/tcp/libtropic_port_posix_tcp.c"]);

        lib.add_define("ABAB", Some("1"));
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_sources(["tropic/stm32/tropic01.c"]);

        lib.add_define("ACAB", Some("1"));
    } else {
        bail_unsupported!();
    }

    lib.add_sources(["tropic/tropic.c"]);

    lib.add_sources_from_folder(
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
        tropic_dir.join("TROPIC01_fw_update_files/boot_v_2_0_1/fw_v_1_0_0"),
    ]);

    lib.add_defines([
        ("LT_USE_TREZOR_CRYPTO", Some("1")),
        ("LT_HELPERS", Some("1")),
    ]);

    Ok(())
}
