// Copyright (c) 2026 Trezor Company s.r.o.
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

use bindgen::EnumVariation;
use std::env;
use std::path::PathBuf;
use std::process::Command;
use xbuild::Result;

fn main() {
    // println!("cargo:rustc-env=BUILD_DIR={}", build_dir());
    generate_bindings();
    build_lib().unwrap();
}

fn build_dir() -> String {
    env::var("BUILD_DIR").unwrap_or(String::from("../../build/unix"))
}

const DEFAULT_BINDGEN_MACROS_COMMON: &[&str] = &[
    "-I../../../crypto",
    "-I../rtl/inc",
    "-I../sys/time/inc",
    "-I../sys/task/inc",
    "-I../sys/mpu/inc",
    "-I../sys/ipc/inc",
    "-DUSE_IPC",
];

fn prepare_bindings() -> bindgen::Builder {
    let mut bindings = bindgen::Builder::default();

    let build_dir_include = format!("-I{}", build_dir());

    let mut clang_args: Vec<String> = Vec::new();

    clang_args.extend(DEFAULT_BINDGEN_MACROS_COMMON.iter().map(|s| s.to_string()));

    clang_args.push(build_dir_include);

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
        .ctypes_prefix("core::ffi")
        .size_t_is_usize(true)
        // Disable the layout tests. They spew out a lot of code-style bindings, and are not too
        // relevant for our use-case.
        .layout_tests(false)
        // Tell cargo to invalidate the built crate whenever any of the
        // included header files change.
        .parse_callbacks(Box::new(bindgen::CargoCallbacks::new()))
}

fn generate_bindings() {
    let out_path = env::var("OUT_DIR").unwrap();

    let bindings = prepare_bindings()
        .header("trezor_api.h")
        .use_core()
        .no_debug(".*")
        .no_copy(".*")
        .derive_default(true)
        .default_enum_style(EnumVariation::Rust {
            non_exhaustive: false,
        })
        .raw_line("#![allow(non_snake_case)]")
        .raw_line("#![allow(non_camel_case_types)]")
        .raw_line("#![allow(non_upper_case_globals)]")
        .raw_line("#![allow(dead_code)]")
        .allowlist_type("trezor_api_v1_t")
        .allowlist_type("trezor_api_getter_t")
        .allowlist_type("sysevents_t")
        .allowlist_type("syshandle_mask_t")
        .allowlist_var("SYSHANDLE__IPC0");

    // Write the bindings to a file in the OUR_DIR.
    bindings
        .generate()
        .expect("Unable to generate bindings")
        .write_to_file(PathBuf::from(out_path).join("api.rs"))
        .unwrap();
}

fn build_lib() -> Result<()> {
    xbuild::build(|lib| {
        lib.add_source("trezor_api_v1_impl.c");
        lib.add_define("USE_IPC", Some("1"));
        lib.add_includes([
            ".",
            "../../../crypto",
            "../rtl/inc",
            "../sys/time/inc",
            "../sys/task/inc",
            "../sys/mpu/inc",
            "../sys/ipc/inc",
        ]);

        Ok(())
    })
}
