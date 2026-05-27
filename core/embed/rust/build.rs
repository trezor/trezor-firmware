#[cfg(feature = "test")]
use std::ffi::OsStr;
use std::{env, path::PathBuf, process::Command};

fn main() {
    println!("cargo:rustc-env=BUILD_DIR={}", build_dir());
    #[cfg(feature = "micropython")]
    generate_qstr_bindings();
    generate_trezorhal_bindings();
    #[cfg(feature = "test")]
    link_core_objects();
}

fn build_dir() -> String {
    let build_dir_str = env::var("BUILD_DIR").unwrap_or(String::from("../../build/unix"));
    PathBuf::from(build_dir_str)
        .canonicalize()
        .unwrap()
        .to_str()
        .unwrap()
        .to_string()
}

const DEFAULT_BINDGEN_MACROS_COMMON: &[&str] = &[
    "-I../projects/bootloader",
    "-I../projects/unix",
    "-I../../build/unix",
    "-I../../vendor/micropython/ports/unix",
    "-I../../../crypto",
    "-I../../../storage",
    "-I../../vendor/micropython",
    "-I../../vendor/micropython/lib/uzlib",
    "-I../../vendor/",
    "-I../rtl/inc",
    "-I../io/gfx/inc",
    "-I../io/ble/inc",
    "-I../io/button/inc",
    "-I../io/display/inc",
    "-I../io/haptic/inc",
    "-I../io/nrf/inc",
    "-I../io/touch/inc",
    "-I../io/power_manager/inc",
    "-I../io/rgb_led/inc",
    "-I../io/suspend/inc",
    "-I../io/translations/inc",
    "-I../io/usb/inc",
    "-I../sec/storage/inc",
    "-I../sys/dbg/inc",
    "-I../sys/inc",
    "-I../sys/time/inc",
    "-I../sys/task/inc",
    "-I../sys/irq/inc",
    "-I../sys/flash/inc",
    "-I../models",
    "-DTREZOR_EMULATOR",
    "-DUSE_BUTTON",
    "-DUSE_TOUCH",
    "-DUSE_HAPTIC",
    "-DUSE_RGB_LED",
    "-DUSE_BLE",
    "-DUSE_POWER_MANAGER",
    "-DUSE_NRF",
    "-DUSE_HW_JPEG_DECODER",
    "-DUSE_STORAGE",
    "-DUSE_DBG_CONSOLE",
    "-DBOOTLOADER",
];

fn add_bindgen_macros<'a>(
    clang_args: &mut Vec<String>,
    envvar: Option<&'a str>,
    test_envvar: Option<&'a str>,
) {
    if let Some(envvar) = envvar {
        clang_args.extend(envvar.split(',').map(String::from));
        return;
    }
    clang_args.extend(DEFAULT_BINDGEN_MACROS_COMMON.iter().map(|s| s.to_string()));
    if let Some(envvar) = test_envvar {
        clang_args.extend(envvar.split(',').map(String::from));
        return;
    }

    let mut model_dirs: Vec<&str> = vec![];
    // always include Bolt as the baseline
    model_dirs.push("../models/T2T1");
    #[cfg(feature = "layout_caesar")]
    model_dirs.push("../models/T3B1");
    #[cfg(feature = "layout_delizia")]
    model_dirs.push("../models/T3T1");
    #[cfg(feature = "layout_eckhart")]
    model_dirs.push("../models/T3W1");
    for model_dir in model_dirs {
        let macros = PathBuf::from(model_dir).join("test_bindgen_macros.txt");
        let contents = std::fs::read_to_string(&macros)
            .unwrap_or_else(|_| panic!("Failed to read {:?}", macros));
        clang_args.extend(contents.split(",\n").map(String::from));
    }
}

/// Generates Rust module that exports QSTR constants used in firmware.
#[cfg(feature = "micropython")]
fn generate_qstr_bindings() {
    let out_path = env::var("OUT_DIR").unwrap();

    // Tell cargo to invalidate the built crate whenever the header changes.
    println!("cargo:rerun-if-changed=qstr.h");

    let dest_file = PathBuf::from(out_path).join("qstr.rs");

    let enum_size = if is_firmware() {
        "-fshort-enums"
    } else {
        "-fno-short-enums"
    };

    bindgen::Builder::default()
        .header("qstr.h")
        // Build the Qstr enum as a newtype so we can define method on it.
        .default_enum_style(bindgen::EnumVariation::NewType {
            is_bitfield: false,
            is_global: false,
        })
        // Pass in correct include paths.
        .clang_args(&["-I", &build_dir()])
        .clang_arg(enum_size)
        // Customize the standard types.
        .use_core()
        .ctypes_prefix("cty")
        .size_t_is_usize(true)
        // Tell cargo to invalidate the built crate whenever any of the
        // included header files change.
        .parse_callbacks(Box::new(bindgen::CargoCallbacks::new()))
        .generate()
        .expect("Unable to generate Rust QSTR bindings")
        .write_to_file(&dest_file)
        .unwrap();

    // rewrite the file to change internal representation of the qstr newtype
    let qstr_generated = std::fs::read_to_string(&dest_file).unwrap();

    let qstr_enum_type = if is_firmware() { "c_ushort" } else { "c_uint" };

    let qstr_modified = qstr_generated.replace(
        &format!("pub struct Qstr(pub cty::{});", qstr_enum_type),
        "pub struct Qstr(pub usize);",
    );

    assert_ne!(qstr_generated, qstr_modified, "Failed to rewrite type of Qstr in qstr.rs file.\nThis indicates that the generated file has changed. Please update the rewriting code.");
    std::fs::write(&dest_file, qstr_modified).unwrap();
}

fn prepare_bindings() -> bindgen::Builder {
    let mut bindings = bindgen::Builder::default();

    let build_dir_include = format!("-I{}", build_dir());

    let mut clang_args: Vec<String> = Vec::new();

    let bindgen_macros_env = env::var("BINDGEN_MACROS").ok();
    let test_macros_env = env::var("TEST_BINDGEN_MACROS").ok();
    add_bindgen_macros(
        &mut clang_args,
        bindgen_macros_env.as_deref(),
        test_macros_env.as_deref(),
    );

    #[cfg(feature = "framebuffer")]
    {
        bindings = bindings.clang_args(&["-DFRAMEBUFFER"]);
    }

    clang_args.push(build_dir_include);

    // Pass in correct include paths and defines.
    if is_firmware() {
        clang_args.push("-nostdinc".to_string());
        clang_args.push("-fshort-enums".to_string()); // Make sure enums use the same size as in C

        // Append gcc-arm-none-eabi's include paths.
        let cc_output = Command::new("arm-none-eabi-gcc")
            .arg("-E")
            .arg("-Wp,-v")
            .arg("-")
            .output()
            .expect("arm-none-eabi-gcc failed to execute");
        if !cc_output.status.success() {
            panic!("arm-none-eabi-gcc failed");
        }
        let include_paths =
            String::from_utf8(cc_output.stderr).expect("arm-none-eabi-gcc returned invalid output");
        let include_args = include_paths
            .lines()
            .skip_while(|s| !s.contains("search starts here:"))
            .take_while(|s| !s.contains("End of search list."))
            .filter(|s| s.starts_with(' '))
            .map(|s| format!("-I{}", s.trim()));

        bindings = bindings.clang_args(include_args);
    } else {
        clang_args.push("-fno-short-enums".to_string());
    }

    bindings = bindings.clang_args(&clang_args);

    bindings
        // Customize the standard types.
        .use_core()
        .ctypes_prefix("cty")
        .size_t_is_usize(true)
        // Disable the layout tests. They spew out a lot of code-style bindings, and are not too
        // relevant for our use-case.
        .layout_tests(false)
        // Tell cargo to invalidate the built crate whenever any of the
        // included header files change.
        .parse_callbacks(Box::new(bindgen::CargoCallbacks::new()))
}

fn generate_trezorhal_bindings() {
    let out_path = env::var("OUT_DIR").unwrap();

    // Tell cargo to invalidate the built crate whenever the header changes.
    println!("cargo:rerun-if-changed=trezorhal.h");

    let bindings = prepare_bindings()
        .header("trezorhal.h")
        // model
        .allowlist_var("MODEL_INTERNAL_NAME")
        .allowlist_var("MODEL_FULL_NAME")
        // secbool
        .allowlist_type("secbool")
        .must_use_type("secbool")
        .allowlist_var("sectrue")
        .allowlist_var("secfalse")
        // storage
        .allowlist_var("EXTERNAL_SALT_SIZE")
        .allowlist_function("storage_setup")
        .allowlist_function("storage_wipe")
        .allowlist_function("storage_is_unlocked")
        .allowlist_function("storage_lock")
        .allowlist_function("storage_unlock")
        .allowlist_function("storage_has_pin")
        .allowlist_function("storage_get_pin_rem")
        .allowlist_function("storage_change_pin")
        .allowlist_function("storage_ensure_not_wipe_code")
        .allowlist_function("storage_has")
        .allowlist_function("storage_get")
        .allowlist_function("storage_set")
        .allowlist_function("storage_delete")
        .allowlist_function("storage_set_counter")
        .allowlist_function("storage_next_counter")
        .allowlist_function("translations_read")
        .allowlist_function("translations_write")
        .allowlist_function("translations_erase")
        .allowlist_function("translations_area_bytesize")
        .allowlist_type("storage_unlock_result_t")
        .rustified_enum("storage_unlock_result_t")
        .allowlist_type("storage_pin_change_result_t")
        .rustified_enum("storage_pin_change_result_t")
        // display
        .allowlist_function("display_refresh")
        .allowlist_function("display_set_backlight")
        .allowlist_function("display_get_backlight")
        .allowlist_function("display_wait_for_sync")
        .allowlist_var("DISPLAY_RESX_")
        .allowlist_var("DISPLAY_RESY_")
        .allowlist_type("display_fb_info_t")
        .allowlist_function("display_get_frame_buffer")
        .allowlist_function("display_fill")
        .allowlist_function("display_copy_rgb565")
        .allowlist_function("display_is_recording")
        .allowlist_function("display_record_screen")
        // gfx_bitblt
        .allowlist_type("gfx_bitblt_t")
        .allowlist_function("gfx_rgb565_fill")
        .allowlist_function("gfx_rgb565_copy_mono4")
        .allowlist_function("gfx_rgb565_copy_rgb565")
        .allowlist_function("gfx_rgb565_blend_mono4")
        .allowlist_function("gfx_rgb565_blend_mono8")
        .allowlist_function("gfx_rgba8888_fill")
        .allowlist_function("gfx_rgba8888_copy_mono4")
        .allowlist_function("gfx_rgba8888_copy_rgb565")
        .allowlist_function("gfx_rgba8888_copy_rgba8888")
        .allowlist_function("gfx_rgba8888_blend_mono4")
        .allowlist_function("gfx_rgba8888_blend_mono8")
        .allowlist_function("gfx_mono8_fill")
        .allowlist_function("gfx_mono8_copy_mono1p")
        .allowlist_function("gfx_mono8_copy_mono4")
        .allowlist_function("gfx_mono8_blend_mono1p")
        .allowlist_function("gfx_mono8_blend_mono4")
        .allowlist_function("gfx_bitblt_wait")
        // uzlib
        .allowlist_function("uzlib_uncompress_init")
        .allowlist_function("uzlib_uncompress")
        // bip39
        .allowlist_function("mnemonic_word_completion_mask")
        .allowlist_var("BIP39_WORDLIST_ENGLISH")
        .allowlist_var("BIP39_WORD_COUNT")
        // slip39
        .allowlist_function("slip39_word_completion_mask")
        .allowlist_function("button_sequence_to_word")
        .allowlist_var("SLIP39_WORDLIST")
        .allowlist_var("SLIP39_WORD_COUNT")
        // random
        .allowlist_function("random_buffer")
        .allowlist_function("random_uniform")
        // rgb led
        .allowlist_type("rgb_led_effect_type_t")
        .allowlist_function("rgb_led_set_color")
        .allowlist_function("rgb_led_effect_start")
        .allowlist_function("rgb_led_effect_stop")
        .allowlist_function("rgb_led_effect_ongoing")
        .allowlist_function("rgb_led_effect_get_type")
        // systick
        .allowlist_function("systick_delay_ms")
        .allowlist_function("systick_ms")
        .allowlist_function("systick_us")
        // toif
        .allowlist_type("toif_format_t")
        //usb
        .allowlist_type("usb_event_t")
        .allowlist_function("usb_get_state")
        // ble
        .allowlist_var("BLE_MAX_BONDS")
        .allowlist_var("BLE_PAIRING_CODE_LEN")
        .allowlist_var("BLE_RX_PACKET_SIZE")
        .allowlist_var("BLE_TX_PACKET_SIZE")
        .allowlist_var("BLE_ADV_NAME_LEN")
        .allowlist_function("ble_get_state")
        .allowlist_function("ble_get_event")
        .allowlist_function("ble_switch_on")
        .allowlist_function("ble_switch_off")
        .allowlist_function("ble_enter_pairing_mode")
        .allowlist_function("ble_disconnect")
        .allowlist_function("ble_set_name")
        .allowlist_function("ble_erase_bonds")
        .allowlist_function("ble_allow_pairing")
        .allowlist_function("ble_reject_pairing")
        .allowlist_function("ble_start")
        .allowlist_function("ble_write")
        .allowlist_function("ble_read")
        .allowlist_function("ble_set_name")
        .allowlist_function("ble_unpair")
        .allowlist_function("ble_get_bond_list")
        .allowlist_function("ble_set_high_speed")
        .allowlist_function("ble_set_enabled")
        .allowlist_function("ble_get_enabled")
        .allowlist_type("ble_command_t")
        .allowlist_type("ble_state_t")
        .allowlist_type("ble_event_t")
        .allowlist_type("bt_le_addr_t")
        // touch
        .allowlist_function("touch_get_event")
        // button
        .allowlist_type("button_t")
        .allowlist_type("button_event_t")
        .allowlist_function("button_get_event")
        // haptic
        .allowlist_type("haptic_effect_t")
        .allowlist_function("haptic_play")
        .allowlist_function("haptic_play_custom")
        // jpegdec
        .allowlist_var("JPEGDEC_RGBA8888_BUFFER_SIZE")
        .allowlist_var("JPEGDEC_MONO8_BUFFER_SIZE")
        .allowlist_type("jpegdec_state_t")
        .allowlist_type("jpegdec_image_t")
        .allowlist_type("jpegdec_image_format_t")
        .allowlist_type("jpegdec_slice_t")
        .allowlist_function("jpegdec_open")
        .allowlist_function("jpegdec_close")
        .allowlist_function("jpegdec_process")
        .allowlist_function("jpegdec_get_info")
        .allowlist_function("jpegdec_get_slice_rgba8888")
        .allowlist_function("jpegdec_get_slice_mono8")
        // sysevent
        .allowlist_type("syshandle_t")
        .allowlist_type("sysevents_t")
        .allowlist_function("sysevents_poll")
        // power manager
        .allowlist_type("pm_event_t")
        .allowlist_function("pm_get_events")
        .allowlist_function("pm_get_state")
        .allowlist_function("pm_suspend")
        .allowlist_function("pm_hibernate")
        .allowlist_function("pm_charging_enable")
        .allowlist_function("pm_charging_disable")
        // irq
        .allowlist_function("irq_lock_fn")
        .allowlist_function("irq_unlock_fn")
        // nrf
        .allowlist_function("nrf_send_uart_data")
        // syslog
        .allowlist_function("syslog_start_record")
        .allowlist_function("syslog_write_chunk")
        .allowlist_type("log_source_t")
        .allowlist_type("log_level_t")
        .allowlist_var("LOG_LEVEL_DBG")
        .allowlist_var("LOG_LEVEL_INF")
        .allowlist_var("LOG_LEVEL_WARN")
        .allowlist_var("LOG_LEVEL_ERR")
        // c_layout
        .allowlist_type("c_layout_t")
        .allowlist_function("bootloader_process_ble")
        .allowlist_function("bootloader_process_usb")
        .allowlist_function("debuglink_process")
        .allowlist_function("debuglink_notify_layout_change");

    // Write the bindings to a file in the OUR_DIR.
    bindings
        .generate()
        .expect("Unable to generate bindings")
        .write_to_file(PathBuf::from(out_path).join("trezorhal.rs"))
        .unwrap();
}

fn is_firmware() -> bool {
    let target = env::var("TARGET").unwrap();
    target.starts_with("thumbv7") || target.starts_with("thumbv8")
}

#[cfg(feature = "test")]
fn link_core_objects() {
    let crate_path = env::var("CARGO_MANIFEST_DIR").unwrap();
    let build_path = format!("{}/../../build/unix", crate_path);

    // List of object filenames to ignore in the `embed` directory
    let embed_blocklist = [OsStr::new("main_main.o")];

    // Collect all objects that the `core` library uses, and link it in. We have to
    // make sure to avoid the object with the `_main` symbol, so we don't get any
    // duplicates.
    let mut cc = cc::Build::new();
    for obj in glob::glob(&format!("{}/embed/**/*.o", build_path)).unwrap() {
        let obj = obj.unwrap();
        if embed_blocklist.contains(&obj.file_name().unwrap()) {
            // Ignore.
        } else {
            cc.object(obj);
        }
    }

    for obj in glob::glob(&format!("{}/vendor/**/*.o", build_path)).unwrap() {
        let obj = obj.unwrap();
        cc.object(obj);
    }

    // Add frozen modules, if present.
    for obj in glob::glob(&format!("{}/*.o", build_path)).unwrap() {
        cc.object(obj.unwrap());
    }

    // Compile all the objects into a static library and link it in automatically.
    cc.compile("core_lib");

    println!("cargo:rustc-link-lib=SDL3");
    println!("cargo:rustc-link-lib=SDL3_image");

    #[cfg(any(feature = "ui_jpeg", feature = "hw_jpeg_decoder"))]
    println!("cargo:rustc-link-lib=jpeg");
}
