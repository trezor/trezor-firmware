#[cfg(feature = "test")]
use std::ffi::OsStr;
use std::{env, path::PathBuf, process::Command};

fn main() {
    #[cfg(feature = "micropython")]
    generate_qstr_bindings();
    #[cfg(feature = "micropython")]
    generate_micropython_bindings();
    generate_trezorhal_bindings();
    #[cfg(feature = "test")]
    link_core_objects();
}

fn mcu_type() -> String {
    match env::var("MCU_TYPE") {
        Ok(mcu) => mcu,
        Err(_) => String::from("STM32F427xx"),
    }
}

fn model() -> String {
    match env::var("TREZOR_MODEL") {
        Ok(model) => model,
        Err(_) => String::from("T"),
    }
}

fn board() -> String {
    if !is_firmware() {
        return String::from("boards/board-unix.h");
    }

    match env::var("TREZOR_BOARD") {
        Ok(board) => {
            format!("boards/{}", board)
        }
        Err(_) => String::from("boards/trezor_t.h"),
    }
}

/// Generates Rust module that exports QSTR constants used in firmware.
#[cfg(feature = "micropython")]
fn generate_qstr_bindings() {
    let out_path = env::var("OUT_DIR").unwrap();

    // Tell cargo to invalidate the built crate whenever the header changes.
    println!("cargo:rerun-if-changed=qstr.h");

    bindgen::Builder::default()
        .header("qstr.h")
        // Build the Qstr enum as a newtype so we can define method on it.
        .default_enum_style(bindgen::EnumVariation::NewType { is_bitfield: false })
        // Pass in correct include paths.
        .clang_args(&[
            "-I",
            if is_firmware() {
                "../../build/firmware"
            } else {
                "../../build/unix"
            },
        ])
        // Customize the standard types.
        .use_core()
        .ctypes_prefix("cty")
        .size_t_is_usize(true)
        // Tell cargo to invalidate the built crate whenever any of the
        // included header files change.
        .parse_callbacks(Box::new(bindgen::CargoCallbacks))
        .generate()
        .expect("Unable to generate Rust QSTR bindings")
        .write_to_file(PathBuf::from(out_path).join("qstr.rs"))
        .unwrap();
}

fn prepare_bindings() -> bindgen::Builder {
    let mut bindings = bindgen::Builder::default();

    // Common include paths and defines
    bindings = bindings.clang_args([
        "-I../../../crypto",
        "-I../../../storage",
        "-I../../vendor/micropython",
        "-I../../vendor/micropython/lib/uzlib",
        "-I../lib",
        "-I../trezorhal",
        "-I../models",
        format!("-D{}", mcu_type()).as_str(),
        format!("-DTREZOR_MODEL_{}", model()).as_str(),
        format!("-DTREZOR_BOARD=\"{}\"", board()).as_str(),
    ]);

    // Pass in correct include paths and defines.
    if is_firmware() {
        let mut clang_args: Vec<&str> = Vec::new();

        let includes = env::var("RUST_INCLUDES").unwrap();
        let args = includes.split(';');

        for arg in args {
            clang_args.push(arg);
        }
        clang_args.push("-nostdinc");
        clang_args.push("-I../firmware");
        clang_args.push("-I../../build/firmware");
        clang_args.push("-I../../vendor/micropython/lib/cmsis/inc");
        clang_args.push("-DUSE_HAL_DRIVER");
        bindings = bindings.clang_args(&clang_args);

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
        bindings = bindings.clang_args(&[
            "-I../unix",
            "-I../trezorhal/unix",
            "-I../../build/unix",
            "-I../../vendor/micropython/ports/unix",
            "-DTREZOR_EMULATOR",
        ]);
    }

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
        .parse_callbacks(Box::new(bindgen::CargoCallbacks))
}

#[cfg(feature = "micropython")]
fn generate_micropython_bindings() {
    let out_path = env::var("OUT_DIR").unwrap();

    // Tell cargo to invalidate the built crate whenever the header changes.
    println!("cargo:rerun-if-changed=micropython.h");

    let bindings = prepare_bindings()
        .header("micropython.h")
        // obj
        .new_type_alias("mp_obj_t")
        .allowlist_type("mp_obj_type_t")
        .allowlist_type("mp_obj_base_t")
        .allowlist_function("mp_obj_new_int")
        .allowlist_function("mp_obj_new_int_from_ll")
        .allowlist_function("mp_obj_new_int_from_ull")
        .allowlist_function("mp_obj_new_int_from_uint")
        .allowlist_function("mp_obj_new_bytes")
        .allowlist_function("mp_obj_new_str")
        .allowlist_function("mp_obj_new_tuple")
        .allowlist_function("mp_obj_get_int_maybe")
        .allowlist_function("mp_obj_is_true")
        .allowlist_function("mp_call_function_n_kw")
        .allowlist_function("trezor_obj_get_ll_checked")
        .allowlist_function("trezor_obj_str_from_rom_text")
        // buffer
        .allowlist_function("mp_get_buffer")
        .allowlist_var("MP_BUFFER_READ")
        .allowlist_var("MP_BUFFER_WRITE")
        .allowlist_var("mp_type_str")
        .allowlist_var("mp_type_bytes")
        .allowlist_var("mp_type_bytearray")
        .allowlist_var("mp_type_memoryview")
        // dict
        .allowlist_type("mp_obj_dict_t")
        .allowlist_function("mp_obj_new_dict")
        .allowlist_var("mp_type_dict")
        // fun
        .allowlist_type("mp_obj_fun_builtin_fixed_t")
        .allowlist_var("mp_type_fun_builtin_0")
        .allowlist_var("mp_type_fun_builtin_1")
        .allowlist_var("mp_type_fun_builtin_2")
        .allowlist_var("mp_type_fun_builtin_3")
        .allowlist_type("mp_obj_fun_builtin_var_t")
        .allowlist_var("mp_type_fun_builtin_var")
        // gc
        .allowlist_function("gc_alloc")
        // iter
        .allowlist_type("mp_obj_iter_buf_t")
        .allowlist_function("mp_getiter")
        .allowlist_function("mp_iternext")
        // list
        .allowlist_type("mp_obj_list_t")
        .allowlist_function("mp_obj_new_list")
        .allowlist_function("mp_obj_list_append")
        .allowlist_function("mp_obj_list_get")
        .allowlist_function("mp_obj_list_set_len")
        .allowlist_var("mp_type_list")
        // map
        .allowlist_type("mp_map_elem_t")
        .allowlist_function("mp_map_init")
        .allowlist_function("mp_map_init_fixed_table")
        .allowlist_function("mp_map_lookup")
        // exceptions
        .allowlist_function("nlr_jump")
        .allowlist_function("mp_obj_new_exception")
        .allowlist_function("mp_obj_new_exception_args")
        .allowlist_function("trezor_obj_call_protected")
        .allowlist_var("mp_type_AttributeError")
        .allowlist_var("mp_type_IndexError")
        .allowlist_var("mp_type_KeyError")
        .allowlist_var("mp_type_MemoryError")
        .allowlist_var("mp_type_OverflowError")
        .allowlist_var("mp_type_ValueError")
        .allowlist_var("mp_type_TypeError")
        // time
        .allowlist_function("mp_hal_ticks_ms")
        .allowlist_function("mp_hal_delay_ms")
        // debug
        .allowlist_function("mp_print_strn")
        .allowlist_var("mp_plat_print")
        // typ
        .allowlist_var("mp_type_type")
        // module
        .allowlist_type("mp_obj_module_t")
        .allowlist_var("mp_type_module")
        // qstr
        .allowlist_function("qstr_data")
        // `ffi::mp_map_t` type is not allowed to be `Clone` or `Copy` because we tie it
        // to the data lifetimes with the `MapRef` type, see `src/micropython/map.rs`.
        // TODO: We should disable `Clone` and `Copy` for all types and only allow-list
        // the specific cases we require.
        .no_copy("_mp_map_t");

    // Write the bindings to a file in the OUR_DIR.
    bindings
        .generate()
        .expect("Unable to generate bindings")
        .write_to_file(PathBuf::from(out_path).join("micropython.rs"))
        .unwrap();
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
        // common
        .allowlist_var("HW_ENTROPY_DATA")
        // secbool
        .allowlist_type("secbool")
        .must_use_type("secbool")
        .allowlist_var("sectrue")
        .allowlist_var("secfalse")
        // flash
        .allowlist_function("flash_init")
        // storage
        .allowlist_var("EXTERNAL_SALT_SIZE")
        .allowlist_function("storage_init")
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
        // display
        .allowlist_function("display_offset")
        .allowlist_function("display_refresh")
        .allowlist_function("display_backlight")
        .allowlist_function("display_text")
        .allowlist_function("display_text_render_buffer")
        .allowlist_function("display_text_width")
        .allowlist_function("display_pixeldata")
        .allowlist_function("display_pixeldata_dirty")
        .allowlist_function("display_set_window")
        .allowlist_function("display_sync")
        .allowlist_function("display_get_fb_addr")
        .allowlist_function("display_get_wr_addr")
        .allowlist_var("DISPLAY_DATA_ADDRESS")
        .allowlist_var("DISPLAY_FRAMEBUFFER_WIDTH")
        .allowlist_var("DISPLAY_FRAMEBUFFER_HEIGHT")
        .allowlist_var("DISPLAY_FRAMEBUFFER_OFFSET_X")
        .allowlist_var("DISPLAY_FRAMEBUFFER_OFFSET_Y")
        .allowlist_var("DISPLAY_RESX")
        .allowlist_var("DISPLAY_RESY")
        .allowlist_type("toif_format_t")
        // fonts
        .allowlist_function("font_height")
        .allowlist_function("font_max_height")
        .allowlist_function("font_baseline")
        .allowlist_function("font_get_glyph")
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
        .allowlist_function("random_uniform")
        // rgb led
        .allowlist_function("rgb_led_set_color")
        // time
        .allowlist_function("hal_delay")
        .allowlist_function("hal_ticks_ms")
        // dma2d
        .allowlist_function("dma2d_setup_const")
        .allowlist_function("dma2d_setup_4bpp")
        .allowlist_function("dma2d_setup_16bpp")
        .allowlist_function("dma2d_setup_4bpp_over_4bpp")
        .allowlist_function("dma2d_setup_4bpp_over_16bpp")
        .allowlist_function("dma2d_start")
        .allowlist_function("dma2d_start_blend")
        .allowlist_function("dma2d_start_const")
        .allowlist_function("dma2d_start_const_multiline")
        .allowlist_function("dma2d_wait_for_transfer")
        //buffers
        .allowlist_function("buffers_get_line_16bpp")
        .allowlist_function("buffers_free_line_16bpp")
        .allowlist_function("buffers_get_line_4bpp")
        .allowlist_function("buffers_free_line_4bpp")
        .allowlist_function("buffers_get_text")
        .allowlist_function("buffers_free_text")
        .allowlist_function("buffers_get_jpeg")
        .allowlist_function("buffers_free_jpeg")
        .allowlist_function("buffers_get_jpeg_work")
        .allowlist_function("buffers_free_jpeg_work")
        .allowlist_function("buffers_get_blurring")
        .allowlist_function("buffers_free_blurring")
        .allowlist_var("TEXT_BUFFER_HEIGHT")
        .no_copy("buffer_line_16bpp_t")
        .no_copy("buffer_line_4bpp_t")
        .no_copy("buffer_text_t")
        .no_copy("buffer_jpeg_t")
        .no_copy("buffer_jpeg_work_t")
        .no_copy("buffer_blurring_t")
        //usb
        .allowlist_function("usb_configured")
        // touch
        .allowlist_function("touch_read")
        // button
        .allowlist_function("button_read");

    // Write the bindings to a file in the OUR_DIR.
    bindings
        .generate()
        .expect("Unable to generate bindings")
        .write_to_file(PathBuf::from(out_path).join("trezorhal.rs"))
        .unwrap();
}

fn is_firmware() -> bool {
    let target = env::var("TARGET").unwrap();
    target.starts_with("thumbv7")
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

    println!("cargo:rustc-link-lib=SDL2");
    println!("cargo:rustc-link-lib=SDL2_image");
}
