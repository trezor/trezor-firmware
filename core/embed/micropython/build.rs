use std::env;
#[cfg(feature = "test")]
use std::ffi::OsStr;
use std::path::PathBuf;
use std::process::Command;

fn main() {
    println!("cargo:rustc-env=BUILD_DIR={}", build_dir());
    generate_micropython_bindings();
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

fn prepare_bindings() -> bindgen::Builder {
    let mut bindings = bindgen::Builder::default();

    let build_dir_include = format!("-I{}", build_dir());
    let port_include =
        env::var("MPCONFIG_PORT_INCLUDE").unwrap_or(env::var("CARGO_MANIFEST_DIR").unwrap());

    let mut clang_args: Vec<String> = Vec::new();

    clang_args.push(format!("-I{}", port_include));
    clang_args.push(build_dir_include);
    clang_args.push("-Iinc".to_string());

    // Pass in correct include paths and defines.
    if env::var("CARGO_CFG_TARGET_OS").unwrap() == "none" {
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

fn generate_micropython_bindings() {
    let out_path = env::var("OUT_DIR").unwrap();

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
        .allowlist_function("mp_obj_get_type_str")
        .allowlist_function("mp_call_function_n_kw")
        // buffer
        .allowlist_function("mp_get_buffer")
        .allowlist_var("MP_BUFFER_READ")
        .allowlist_var("MP_BUFFER_WRITE")
        .allowlist_var("mp_type_str")
        .allowlist_var("mp_type_bytes")
        .allowlist_var("mp_type_bytearray")
        .allowlist_var("mp_type_memoryview")
        // debug
        .allowlist_function("mp_print_strn")
        .allowlist_function("str_modulo_format")
        .allowlist_var("mp_plat_print")
        // dict
        .allowlist_type("mp_obj_dict_t")
        .allowlist_function("mp_obj_new_dict")
        .allowlist_var("mp_type_dict")
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
        .allowlist_var("mp_type_RuntimeError")
        .allowlist_var("mp_type_NotImplementedError")
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
        // int
        .allowlist_type("mp_obj_int_t")
        .allowlist_var("mp_type_int")
        .allowlist_type("mpz_t")
        .allowlist_function("mpz_as_bytes")
        .allowlist_var("MICROPY_DIG_SIZE")
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
        // module
        .allowlist_type("mp_obj_module_t")
        .allowlist_var("mp_type_module")
        // qstr
        .allowlist_function("qstr_data")
        .allowlist_function("qstr_compute_hash")
        // str
        .allowlist_type("mp_obj_str_t")
        // time
        .allowlist_function("mp_hal_ticks_ms")
        .allowlist_function("mp_hal_delay_ms")
        // tuple
        .allowlist_type("mp_obj_tuple_t")
        // typ
        .allowlist_var("mp_type_type")
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
}
