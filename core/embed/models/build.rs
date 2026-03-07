fn model_to_num(model: &str) -> u32 {
    let model_bytes = model.as_bytes();
    (model_bytes[3] as u32) << 24
        | (model_bytes[2] as u32) << 16
        | (model_bytes[1] as u32) << 8
        | (model_bytes[0] as u32)
}

fn main() {
    let mut lib = cbuild::CLibrary::new();

    lib.add_public_include(".");

    if cfg!(feature = "mcu_stm32u5") {
        lib.add_public_flags(&[
            "-nostdlib",
            "-std=gnu11",
            // "-Werror",
            "-Wno-sequence-point",
            "-Wdouble-promotion",
            "-Wpointer-arith",
            "-Wno-missing-braces",
            "-fno-common",
            "-fsingle-precision-constant",
            "-ffreestanding",
            "-fstack-protector-strong",
        ]);

        if cfg!(feature = "secure_mode") {
            lib.add_public_flag("-mcmse");
        }
    } else if cfg!(feature = "mcu_stm32f4") {
        lib.add_public_flags(&[
            "-nostdlib",
            "-std=gnu11",
            //"-Werror",
            "-Wno-sequence-point",
            "-Wdouble-promotion",
            "-Wpointer-arith",
            "-Wno-missing-braces",
            "-fno-common",
            "-fsingle-precision-constant",
            "-ffreestanding",
            "-fstack-protector-strong",
        ]);
    }

    if cfg!(feature = "kernel_mode") {
        lib.add_public_define("KERNEL_MODE", Some("1"));
    }

    if cfg!(feature = "secure_mode") {
        lib.add_public_define("SECURE_MODE", Some("1"));
    }

    if cfg!(feature = "boardloader") {
        lib.add_public_define("BOARDLOADER", None);
    }

    if cfg!(feature = "bootloader") {
        lib.add_public_define("BOOTLOADER", None);
    }

    if cfg!(feature = "secmon") {
        lib.add_public_define("SECMON", None);
    }

    if cfg!(feature = "kernel") {
        lib.add_public_define("KERNEL", None);
    }

    if cfg!(feature = "prodtest") {
        lib.add_public_define("TREZOR_PRODTEST", None);
    }

    if cfg!(feature = "mcu_emulator") {
        lib.add_public_define("TREZOR_EMULATOR", None);

        // HACK: include the project directory to find profile.h
        // (needed by flash, display)
        lib.add_public_include("../projects/unix");
    }

    if cfg!(feature = "lockable_bootloader") {
        lib.add_public_define("LOCKABLE_BOOTLOADER", None);
    }

    if cfg!(feature = "model_t3w1") {
        let board_header = if cfg!(feature = "mcu_emulator") {
            "\"T3W1/boards/t3w1-unix.h\""
        } else {
            "\"T3W1/boards/trezor_t3w1_revC.h\""
        };

        lib.add_public_defines(&[
            ("TREZOR_MODEL_T3W1", None),
            ("TREZOR_BOARD", Some(board_header)),
            ("MODEL_HEADER", Some("\"T3W1/model_T3W1.h\"")),
            ("VERSIONS_HEADER", Some("\"T3W1/versions.h\"")),
            ("HW_MODEL", Some(model_to_num("T3W1").to_string().as_str())),
            ("HW_REVISION", Some("1")),
            ("HSE_VALUE", Some("32000000")),
            ("LSI_VALUE", Some("250")),
            ("USE_HSE", Some("1")),
            ("USE_LSE", Some("1")),
            ("USE_LSI", Some("1")),
            ("USE_STORAGE_HWKEY", Some("1")),
            ("USE_OEM_KEYS_CHECK", Some("1")),
        ]);

        if cfg!(feature = "secmon-layout") {
            lib.add_public_define("USE_SECMON_LAYOUT", Some("1"));
        }
    } else if cfg!(feature = "model_t3t1") {
        let board_header = if cfg!(feature = "mcu_emulator") {
            "\"T3T1/boards/t3t1_unix.h\""
        } else {
            "\"T3T1/boards/trezor_t3t1_revE.h\""
        };

        lib.add_public_defines(&[
            ("TREZOR_MODEL_T3T1", None),
            ("TREZOR_BOARD", Some(board_header)),
            ("MODEL_HEADER", Some("\"T3T1/model_T3T1.h\"")),
            ("VERSIONS_HEADER", Some("\"T3T1/versions.h\"")),
            ("HW_MODEL", Some(model_to_num("T3T1").to_string().as_str())),
            ("HW_REVISION", Some("0")),
            ("USE_STORAGE_HWKEY", Some("1")),
            ("USE_OEM_KEYS_CHECK", Some("1")),
        ]);
    } else if cfg!(feature = "model_t3b1") {
        let board_header = if cfg!(feature = "mcu_emulator") {
            "\"T3B1/boards/t3b1_unix.h\""
        } else {
            "\"T3B1/boards/trezor_t3b1_revB.h\""
        };

        lib.add_public_defines(&[
            ("TREZOR_MODEL_T3B1", None),
            ("TREZOR_BOARD", Some(board_header)),
            ("MODEL_HEADER", Some("\"T3B1/model_T3B1.h\"")),
            ("VERSIONS_HEADER", Some("\"T3B1/versions.h\"")),
            ("HW_MODEL", Some(model_to_num("T3B1").to_string().as_str())),
            ("HW_REVISION", Some("0")),
            ("USE_STORAGE_HWKEY", Some("1")),
            ("USE_OEM_KEYS_CHECK", Some("1")),
        ]);
    } else if cfg!(feature = "model_t2t1") {
        let board_header = if cfg!(feature = "mcu_emulator") {
            "\"T2T1/boards/t2t1-unix.h\""
        } else {
            "\"T2T1/boards/trezor_t.h\""
        };

        lib.add_public_defines(&[
            ("TREZOR_MODEL_T2T1", None),
            ("TREZOR_BOARD", Some(board_header)),
            ("MODEL_HEADER", Some("\"T2T1/model_T2T1.h\"")),
            ("VERSIONS_HEADER", Some("\"T2T1/versions.h\"")),
            ("HW_MODEL", Some(model_to_num("T2T1").to_string().as_str())),
            ("HW_REVISION", Some("0")),
            ("HSE_VALUE", Some("8000000")),
            ("USE_HSE", Some("1")),
        ]);
    } else if cfg!(feature = "model_t2b1") {
        let board_header = if cfg!(feature = "mcu_emulator") {
            "\"T2B1/boards/t2b1-unix.h\""
        } else {
            "\"T2B1/boards/trezor_r_v10.h\""
        };

        lib.add_public_defines(&[
            ("TREZOR_MODEL_T2B1", None),
            ("TREZOR_BOARD", Some(board_header)),
            ("MODEL_HEADER", Some("\"T2B1/model_T2B1.h\"")),
            ("VERSIONS_HEADER", Some("\"T2B1/versions.h\"")),
            ("HW_MODEL", Some(model_to_num("T2B1").to_string().as_str())),
            ("HW_REVISION", Some("10")),
            ("HSE_VALUE", Some("8000000")),
            ("USE_HSE", Some("1")),
        ]);
    } else {
        unimplemented!();
    }

    lib.add_sources(&["_dummy.c"]);

    lib.build();
}
