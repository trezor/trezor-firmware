#[cfg(feature = "test")]
use std::ffi::OsStr;
use std::{env, path::PathBuf, process::Command};

fn main() {
    println!("cargo:rustc-env=BUILD_DIR={}", build_dir());
    #[cfg(feature = "micropython")]
    generate_qstr_bindings();
    #[cfg(feature = "micropython")]
    generate_micropython_bindings();
    generate_trezorhal_bindings();
    #[cfg(feature = "crypto")]
    generate_crypto_bindings();
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
    "-I../projects/unix",
    "-I../../build/unix",
    "-I../../vendor/micropython/ports/unix",
    "-I../../../crypto",
    "-I../../../storage",
    "-I../../vendor/micropython",
    "-I../../vendor/micropython/lib/uzlib",
    "-I../rtl/inc",
    "-I../gfx/inc",
    "-I../io/button/inc",
    "-I../io/display/inc",
    "-I../io/haptic/inc",
    "-I../io/touch/inc",
    "-I../io/rgb_led/inc",
    "-I../io/usb/inc",
    "-I../sec/entropy/inc",
    "-I../sys/time/inc",
    "-I../util/flash/inc",
    "-I../util/translations/inc",
    "-I../models",
    "-DTREZOR_EMULATOR",
    "-DUSE_BUTTON",
    "-DUSE_TOUCH",
    "-DUSE_HAPTIC",
    "-DUSE_RGB_LED",
];

#[cfg(feature = "model_tt")]
const DEFAULT_BINDGEN_MACROS_T2T1: &[&str] = &[
    "-DSTM32F427",
    "-DTREZOR_MODEL_T",
    "-DFLASH_BIT_ACCESS=1",
    "-DFLASH_BLOCK_WORDS=1",
    "-DTREZOR_BOARD=\"T2T1/boards/t2t1-unix.h\"",
];
#[cfg(not(feature = "model_tt"))]
const DEFAULT_BINDGEN_MACROS_T2T1: &[&str] = &[];

#[cfg(feature = "model_tr")]
const DEFAULT_BINDGEN_MACROS_T2B1: &[&str] = &[
    "-DSTM32F427",
    "-DTREZOR_MODEL_R",
    "-DFLASH_BIT_ACCESS=1",
    "-DFLASH_BLOCK_WORDS=1",
    "-DTREZOR_BOARD=\"T2B1/boards/t2b1-unix.h\"",
];
#[cfg(not(feature = "model_tr"))]
const DEFAULT_BINDGEN_MACROS_T2B1: &[&str] = &[];

#[cfg(feature = "model_mercury")]
const DEFAULT_BINDGEN_MACROS_T3T1: &[&str] = &[
    "-DSTM32U5",
    "-DTREZOR_MODEL_T3T1",
    "-DFLASH_BIT_ACCESS=0",
    "-DFLASH_BLOCK_WORDS=4",
    "-DTREZOR_BOARD=\"T3T1/boards/t3t1-unix.h\"",
];
#[cfg(not(feature = "model_mercury"))]
const DEFAULT_BINDGEN_MACROS_T3T1: &[&str] = &[];

fn add_bindgen_macros<'a>(clang_args: &mut Vec<&'a str>, envvar: Option<&'a str>) {
    let default_macros = DEFAULT_BINDGEN_MACROS_COMMON
        .iter()
        .chain(DEFAULT_BINDGEN_MACROS_T2T1)
        .chain(DEFAULT_BINDGEN_MACROS_T2B1)
        .chain(DEFAULT_BINDGEN_MACROS_T3T1);

    match envvar {
        Some(envvar) => clang_args.extend(envvar.split(',')),
        None => clang_args.extend(default_macros),
    }
}

/// Generates Rust module that exports QSTR constants used in firmware.
#[cfg(feature = "micropython")]
fn generate_qstr_bindings() {
    let out_path = env::var("OUT_DIR").unwrap();

    // Tell cargo to invalidate the built crate whenever the header changes.
    println!("cargo:rerun-if-changed=qstr.h");

    let dest_file = PathBuf::from(out_path).join("qstr.rs");

    bindgen::Builder::default()
        .header("qstr.h")
        // Build the Qstr enum as a newtype so we can define method on it.
        .default_enum_style(bindgen::EnumVariation::NewType {
            is_bitfield: false,
            is_global: false,
        })
        // Pass in correct include paths.
        .clang_args(&["-I", &build_dir()])
        // Customize the standard types.
        .use_core()
        .ctypes_prefix("cty")
        .size_t_is_usize(true)
        // Tell cargo to invalidate the built crate whenever any of the
        // included header files change.
        .parse_callbacks(Box::new(bindgen::CargoCallbacks))
        .generate()
        .expect("Unable to generate Rust QSTR bindings")
        .write_to_file(&dest_file)
        .unwrap();

    // rewrite the file to change internal representation of the qstr newtype
    let qstr_generated = std::fs::read_to_string(&dest_file).unwrap();
    let qstr_modified = qstr_generated.replace(
        "pub struct Qstr(pub cty::c_uint);",
        "pub struct Qstr(pub usize);",
    );
    assert_ne!(qstr_generated, qstr_modified, "Failed to rewrite type of Qstr in qstr.rs file.\nThis indicates that the generated file has changed. Please update the rewriting code.");
    std::fs::write(&dest_file, qstr_modified).unwrap();
}

fn prepare_bindings() -> bindgen::Builder {
    let mut bindings = bindgen::Builder::default();

    let build_dir_include = format!("-I{}", build_dir());

    let mut clang_args: Vec<&str> = Vec::new();

    let bindgen_macros_env = env::var("BINDGEN_MACROS").ok();
    add_bindgen_macros(&mut clang_args, bindgen_macros_env.as_deref());

    #[cfg(feature = "framebuffer")]
    {
        bindings = bindings.clang_args(&["-DFRAMEBUFFER"]);
    }

    clang_args.push(&build_dir_include);

    // Pass in correct include paths and defines.
    if is_firmware() {
        clang_args.push("-nostdinc");

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
        .allowlist_function("mp_obj_new_attrtuple")
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
        .allowlist_function("gc_free")
        .allowlist_var("GC_ALLOC_FLAG_HAS_FINALISER")
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
        .allowlist_var("mp_type_EOFError")
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
        // tuple
        .allowlist_type("mp_obj_tuple_t")
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
        // entropy
        .allowlist_var("HW_ENTROPY_LEN")
        .allowlist_function("entropy_get")
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
        .allowlist_function("translations_read")
        .allowlist_function("translations_write")
        .allowlist_function("translations_erase")
        .allowlist_function("translations_area_bytesize")
        // display
        .allowlist_function("display_refresh")
        .allowlist_function("display_set_backlight")
        .allowlist_function("display_get_backlight")
        .allowlist_function("display_wait_for_sync")
        .allowlist_var("DISPLAY_RESX")
        .allowlist_var("DISPLAY_RESY")
        .allowlist_type("display_fb_info_t")
        .allowlist_function("display_get_frame_buffer")
        .allowlist_function("display_fill")
        .allowlist_function("display_copy_rgb565")
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
        // fonts
        .allowlist_function("font_height")
        .allowlist_function("font_max_height")
        .allowlist_function("font_baseline")
        .allowlist_function("font_get_glyph")
        .allowlist_function("font_text_width")
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
        // systick
        .allowlist_function("systick_delay_ms")
        .allowlist_function("systick_ms")
        // toif
        .allowlist_type("toif_format_t")
        //usb
        .allowlist_function("usb_configured")
        // touch
        .allowlist_function("touch_get_event")
        // button
        .allowlist_type("button_t")
        .allowlist_function("button_get_event")
        // haptic
        .allowlist_type("haptic_effect_t")
        .allowlist_function("haptic_play")
        .allowlist_function("haptic_play_custom");

    // Write the bindings to a file in the OUR_DIR.
    bindings
        .generate()
        .expect("Unable to generate bindings")
        .write_to_file(PathBuf::from(out_path).join("trezorhal.rs"))
        .unwrap();
}

fn generate_crypto_bindings() {
    let out_path = env::var("OUT_DIR").unwrap();

    // Tell cargo to invalidate the built crate whenever the header changes.
    println!("cargo:rerun-if-changed=crypto.h");

    let bindings = prepare_bindings()
        .header("crypto.h")
        // ed25519
        .allowlist_type("ed25519_signature")
        .allowlist_type("ed25519_public_key")
        .allowlist_function("ed25519_cosi_combine_publickeys")
        // incorrect signature from bindgen, see crypto::ed25519:ffi_override
        //.allowlist_function("ed25519_sign_open")
        // sha256
        .allowlist_var("SHA256_DIGEST_LENGTH")
        .allowlist_type("SHA256_CTX")
        .no_copy("SHA256_CTX")
        .allowlist_function("sha256_Init")
        .allowlist_function("sha256_Update")
        .allowlist_function("sha256_Final");

    // Write the bindings to a file in the OUR_DIR.
    bindings
        .clang_arg("-fgnuc-version=0") // avoid weirdness with ed25519.h CONST definition
        .generate()
        .expect("Unable to generate bindings")
        .write_to_file(PathBuf::from(out_path).join("crypto.rs"))
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

    println!("cargo:rustc-link-lib=SDL2");
    println!("cargo:rustc-link-lib=SDL2_image");
}
