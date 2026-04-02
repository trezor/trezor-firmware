use xbuild::{CLibrary, Result, bail_unsupported};

fn main() -> Result<()> {
    xbuild::build(|lib| {
        lib.add_include(".");

        //TODO!@# check this: -ftrivial-auto-var-init

        if cfg!(feature = "emulator") {
            lib.add_flags([
                "-std=gnu11",
                "-Wall",
                "-Werror",
                "-Wuninitialized", // !@# why we don't catch this in stm32 builds?
                "-Wno-sequence-point",
                "-Wno-missing-braces",
                //TODO!@# bootloader_emu/prodtest/unix have different sets of warnings, unify and enable more
            ]);
        } else if cfg!(feature = "mcu_stm32u5") {
            lib.add_flags([
                "-nostdlib",
                "-std=gnu11",
                "-Wall",
                "-Werror",
                "-Wno-sequence-point",
                "-Wdouble-promotion",
                "-Wpointer-arith",
                "-Wno-missing-braces",
                "-fno-common",
                "-fsingle-precision-constant",
                //"-ffreestanding",  // TODO! this block built-in functions...
                "-fstack-protector-strong",
            ]);

            if cfg!(feature = "secure_mode") {
                lib.add_flag("-mcmse");
            }
        } else if cfg!(feature = "mcu_stm32f4") {
            lib.add_flags([
                "-nostdlib",
                "-std=gnu11",
                "-Wall",
                "-Werror",
                "-Wno-sequence-point",
                "-Wdouble-promotion",
                "-Wpointer-arith",
                "-Wno-missing-braces",
                "-fno-common",
                "-fsingle-precision-constant",
                //"-ffreestanding",
                "-fstack-protector-strong",
            ]);
        } else {
            bail_unsupported!();
        }

        if cfg!(feature = "kernel_mode") {
            lib.add_define("KERNEL_MODE", Some("1"));
        }

        if cfg!(feature = "secure_mode") {
            lib.add_define("SECURE_MODE", Some("1"));
        }

        if cfg!(feature = "secmon_layout") {
            lib.add_define("USE_SECMON_LAYOUT", Some("1"));
        }

        if cfg!(feature = "production") {
            lib.add_define("PRODUCTION", None);
        }

        if cfg!(feature = "boardloader") {
            lib.add_define("BOARDLOADER", None);
        }

        if cfg!(feature = "bootloader") {
            lib.add_define("BOOTLOADER", None);
        }

        if cfg!(feature = "secmon") {
            lib.add_define("SECMON", None);
        }

        if cfg!(feature = "kernel") {
            lib.add_define("KERNEL", None);
        }

        if cfg!(feature = "prodtest") {
            lib.add_define("TREZOR_PRODTEST", None);
        }

        if cfg!(feature = "emulator") {
            lib.add_define("TREZOR_EMULATOR", None);

            lib.add_define("KERNEL", None); // !@# temp hack for including applet.h

            // HACK: include the project directory to find profile.h
            // (needed by flash, display)
            lib.add_include("../projects/unix");

            if cfg!(feature = "asan") {
                lib.add_flags([
                    "-fsanitize=address,undefined",
                    "-fno-omit-frame-pointer",
                    "-fno-optimize-sibling-calls",
                ]);
            }
        }

        if cfg!(feature = "model_t2t1") {
            define_model_t2t1(lib);
        } else if cfg!(feature = "model_t2b1") {
            define_model_t2b1(lib);
        } else if cfg!(feature = "model_t3b1") {
            define_model_t3b1(lib);
        } else if cfg!(feature = "model_t3t1") {
            define_model_t3t1(lib);
        } else if cfg!(feature = "model_t3w1") {
            define_model_t3w1(lib);
        } else {
            bail_unsupported!();
        }

        // Compile some dummy source file to ensure the library is created
        // (=> metadata are passed to higher-level crates)
        lib.add_source("_dummy.c");

        Ok(())
    })
}

fn model_to_num(model: &str) -> u32 {
    let model_bytes = model.as_bytes();
    (model_bytes[3] as u32) << 24
        | (model_bytes[2] as u32) << 16
        | (model_bytes[1] as u32) << 8
        | (model_bytes[0] as u32)
}

fn define_model_t3w1(lib: &mut CLibrary) {
    let board_header = if cfg!(feature = "emulator") {
        "\"T3W1/boards/t3w1-unix.h\""
    } else {
        "\"T3W1/boards/trezor_t3w1_revC.h\""
    };

    lib.add_defines([
        ("TREZOR_MODEL_T3W1", None),
        ("TREZOR_BOARD", Some(board_header)),
        ("MODEL_HEADER", Some("\"T3W1/model_T3W1.h\"")),
        ("VERSIONS_HEADER", Some("\"T3W1/versions.h\"")),
        ("OTP_LAYOUT_HEADER", Some("\"T3W1/otp_layout.h\"")),
        (
            "UNIT_PROPERTIES_CONTENT_HEADER",
            Some("\"T3W1/unit_properties_content.h\""),
        ),
        ("HW_MODEL", Some(model_to_num("T3W1").to_string().as_str())),
        ("HW_REVISION", Some("1")),
        ("USE_BOOTARGS_RSOD", Some("1")),
        ("HSE_VALUE", Some("32000000")),
        ("LSI_VALUE", Some("250")),
        ("USE_HSE", Some("1")),
        ("USE_LSE", Some("1")),
        ("USE_LSI", Some("1")),
        ("USE_OEM_KEYS_CHECK", Some("1")),
    ]);
}

fn define_model_t3t1(lib: &mut CLibrary) {
    let board_header = if cfg!(feature = "emulator") {
        "\"T3T1/boards/t3t1-unix.h\""
    } else {
        "\"T3T1/boards/trezor_t3t1_revE.h\""
    };

    lib.add_defines([
        ("TREZOR_MODEL_T3T1", None),
        ("TREZOR_BOARD", Some(board_header)),
        ("MODEL_HEADER", Some("\"T3T1/model_T3T1.h\"")),
        ("VERSIONS_HEADER", Some("\"T3T1/versions.h\"")),
        ("OTP_LAYOUT_HEADER", Some("\"T3T1/otp_layout.h\"")),
        (
            "UNIT_PROPERTIES_CONTENT_HEADER",
            Some("\"T3T1/unit_properties_content.h\""),
        ),
        ("HW_MODEL", Some(model_to_num("T3T1").to_string().as_str())),
        ("HW_REVISION", Some("0")),
        ("USE_OEM_KEYS_CHECK", Some("1")),
    ]);
}

fn define_model_t3b1(lib: &mut CLibrary) {
    let board_header = if cfg!(feature = "emulator") {
        "\"T3B1/boards/t3b1-unix.h\""
    } else {
        "\"T3B1/boards/trezor_t3b1_revB.h\""
    };

    lib.add_defines([
        ("TREZOR_MODEL_T3B1", None),
        ("TREZOR_BOARD", Some(board_header)),
        ("MODEL_HEADER", Some("\"T3B1/model_T3B1.h\"")),
        ("VERSIONS_HEADER", Some("\"T3B1/versions.h\"")),
        ("OTP_LAYOUT_HEADER", Some("\"T3B1/otp_layout.h\"")),
        (
            "UNIT_PROPERTIES_CONTENT_HEADER",
            Some("\"T3B1/unit_properties_content.h\""),
        ),
        ("HW_MODEL", Some(model_to_num("T3B1").to_string().as_str())),
        ("HW_REVISION", Some("0")),
        ("USE_OEM_KEYS_CHECK", Some("1")),
    ]);
}

fn define_model_t2t1(lib: &mut CLibrary) {
    let board_header = if cfg!(feature = "emulator") {
        "\"T2T1/boards/t2t1-unix.h\""
    } else {
        "\"T2T1/boards/trezor_t.h\""
    };

    lib.add_defines([
        ("TREZOR_MODEL_T2T1", None),
        ("TREZOR_BOARD", Some(board_header)),
        ("MODEL_HEADER", Some("\"T2T1/model_T2T1.h\"")),
        ("VERSIONS_HEADER", Some("\"T2T1/versions.h\"")),
        ("OTP_LAYOUT_HEADER", Some("\"T2T1/otp_layout.h\"")),
        (
            "UNIT_PROPERTIES_CONTENT_HEADER",
            Some("\"T2T1/unit_properties_content.h\""),
        ),
        ("HW_MODEL", Some(model_to_num("T2T1").to_string().as_str())),
        ("HW_REVISION", Some("0")),
        ("HSE_VALUE", Some("8000000")),
        ("USE_HSE", Some("1")),
    ]);
}

fn define_model_t2b1(lib: &mut CLibrary) {
    let board_header = if cfg!(feature = "emulator") {
        "\"T2B1/boards/t2b1-unix.h\""
    } else {
        "\"T2B1/boards/trezor_r_v10.h\""
    };

    lib.add_defines([
        ("TREZOR_MODEL_T2B1", None),
        ("TREZOR_BOARD", Some(board_header)),
        ("MODEL_HEADER", Some("\"T2B1/model_T2B1.h\"")),
        ("VERSIONS_HEADER", Some("\"T2B1/versions.h\"")),
        ("OTP_LAYOUT_HEADER", Some("\"T2B1/otp_layout.h\"")),
        (
            "UNIT_PROPERTIES_CONTENT_HEADER",
            Some("\"T2B1/unit_properties_content.h\""),
        ),
        ("HW_MODEL", Some(model_to_num("T2B1").to_string().as_str())),
        ("HW_REVISION", Some("10")),
        ("HSE_VALUE", Some("8000000")),
        ("USE_HSE", Some("1")),
    ]);
}
