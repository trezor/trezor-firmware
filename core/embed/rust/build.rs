use std::{env, path::PathBuf, process::Command};

fn main() {
    generate_qstr_bindings();
    generate_micropython_bindings();
}

/// Generates Rust module that exports QSTR constants used in firmware.
fn generate_qstr_bindings() {
    let out_path = env::var("OUT_DIR").unwrap();
    let target = env::var("TARGET").unwrap();

    // Tell cargo to invalidate the built crate whenever the header changes.
    println!("cargo:rerun-if-changed=qstr.h");

    bindgen::Builder::default()
        .header("qstr.h")
        // Build the Qstr enum as a newtype so we can define method on it.
        .default_enum_style(bindgen::EnumVariation::NewType { is_bitfield: false })
        // Pass in correct include paths.
        .clang_args(&[
            "-I",
            if target == "thumbv7em-none-eabihf" {
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

fn generate_micropython_bindings() {
    let out_path = env::var("OUT_DIR").unwrap();
    let target = env::var("TARGET").unwrap();

    // Tell cargo to invalidate the built crate whenever the header changes.
    println!("cargo:rerun-if-changed=micropython.h");

    let mut bindings = bindgen::Builder::default()
        .header("micropython.h")
        // obj
        .new_type_alias("mp_obj_t")
        .whitelist_type("mp_obj_type_t")
        .whitelist_type("mp_obj_base_t")
        .whitelist_function("mp_obj_new_int")
        .whitelist_function("mp_obj_new_int_from_ll")
        .whitelist_function("mp_obj_new_int_from_ull")
        .whitelist_function("mp_obj_new_bytes")
        .whitelist_function("mp_obj_new_str")
        .whitelist_function("mp_obj_get_int_maybe")
        .whitelist_function("mp_obj_is_true")
        .whitelist_function("mp_call_function_n_kw")
        // buffer
        .whitelist_function("mp_get_buffer")
        .whitelist_var("MP_BUFFER_READ")
        .whitelist_var("MP_BUFFER_WRITE")
        .whitelist_var("MP_BUFFER_RW")
        // dict
        .whitelist_type("mp_obj_dict_t")
        .whitelist_function("mp_obj_new_dict")
        .whitelist_function("mp_obj_dict_store")
        .whitelist_var("mp_type_dict")
        // fun
        .whitelist_type("mp_obj_fun_builtin_fixed_t")
        .whitelist_var("mp_type_fun_builtin_1")
        .whitelist_var("mp_type_fun_builtin_2")
        .whitelist_var("mp_type_fun_builtin_3")
        // gc
        .whitelist_function("gc_alloc")
        // iter
        .whitelist_type("mp_obj_iter_buf_t")
        .whitelist_function("mp_getiter")
        .whitelist_function("mp_iternext")
        // list
        .whitelist_type("mp_obj_list_t")
        .whitelist_function("mp_obj_new_list")
        .whitelist_function("mp_obj_list_append")
        .whitelist_var("mp_type_list")
        // map
        .whitelist_type("mp_map_elem_t")
        .whitelist_type("mp_map_lookup_kind_t")
        .whitelist_function("mp_map_lookup")
        // runtime
        .whitelist_function("mp_raise_ValueError")
        // typ
        .whitelist_var("mp_type_type");

    // Pass in correct include paths and defines.
    if target == "thumbv7em-none-eabihf" {
        bindings = bindings.clang_args(&[
            "-I../firmware",
            "-I../trezorhal",
            "-I../../build/firmware",
            "-I../../vendor/micropython",
            "-I../../vendor/micropython/lib/stm32lib/STM32F4xx_HAL_Driver/Inc",
            "-I../../vendor/micropython/lib/stm32lib/CMSIS/STM32F4xx/Include",
            "-I../../vendor/micropython/lib/cmsis/inc",
            "-DTREZOR_MODEL=T",
            "-DSTM32F405xx",
            "-DUSE_HAL_DRIVER",
            "-DSTM32_HAL_H=<stm32f4xx.h>",
        ]);
        // Append gcc-arm-none-eabi's include path.
        let sysroot = Command::new("arm-none-eabi-gcc")
            .arg("-print-sysroot")
            .output()
            .expect("arm-none-eabi-gcc failed to execute");
        if !sysroot.status.success() {
            panic!("arm-none-eabi-gcc failed");
        }
        bindings = bindings.clang_arg(format!(
            "-I{}/include",
            String::from_utf8(sysroot.stdout)
                .expect("arm-none-eabi-gcc returned invalid output")
                .trim()
        ));
    } else {
        bindings = bindings.clang_args(&[
            "-I../unix",
            "-I../../build/unix",
            "-I../../vendor/micropython",
        ]);
    }

    bindings
        // Customize the standard types.
        .use_core()
        .ctypes_prefix("cty")
        .size_t_is_usize(true)
        // Tell cargo to invalidate the built crate whenever any of the
        // included header files change.
        .parse_callbacks(Box::new(bindgen::CargoCallbacks))
        // Write the bindings to a file in the OUR_DIR.
        .generate()
        .expect("Unable to generate Rust Micropython bindings")
        .write_to_file(PathBuf::from(out_path).join("micropython.rs"))
        .unwrap();
}
