use std::{
    env,
    fs::File,
    io::{BufRead, BufReader, Write},
    iter::once,
    path::{Path, PathBuf},
};

use xbuild::{CLibrary, InputFiles, Result, WrapErr, bail, bail_unsupported, ensure};

fn main() -> Result<()> {
    xbuild::build(|lib| {
        let mpy_dir = "../../vendor/micropython";

        lib.import_lib("io")?;

        if cfg!(feature = "emulator") {
            // There are two mpconfigport.h files in both ports/unix and projects/unix.
            // The first one has precedence and is used for compilation.
            lib.add_include("../projects/unix");
            lib.add_include(PathBuf::from(mpy_dir).join("ports/unix"));
        } else if cfg!(feature = "mcu_stm32") {
            lib.add_include("../projects/firmware");
        } else {
            bail_unsupported!();
        }

        lib.add_include(mpy_dir);

        if cfg!(feature = "universal_fw") {
            lib.add_define("BITCOIN_ONLY", Some("0"));
        } else {
            lib.add_define("BITCOIN_ONLY", Some("1"));
        }

        if cfg!(feature = "layout_bolt") {
            lib.add_define("UI_LAYOUT_BOLT", None);
        } else if cfg!(feature = "layout_caesar") {
            lib.add_define("UI_LAYOUT_CAESAR", None);
        } else if cfg!(feature = "layout_delizia") {
            lib.add_define("UI_LAYOUT_DELIZIA", None);
        } else if cfg!(feature = "layout_eckhart") {
            lib.add_define("UI_LAYOUT_ECKHART", None);
        } else {
            bail_unsupported!();
        }

        if cfg!(feature = "thp") {
            lib.add_define("USE_THP", None);
        }

        if cfg!(feature = "serial_number") {
            lib.add_define("USE_SERIAL_NUMBER", Some("1"));
        }

        if cfg!(feature = "disable_animation") {
            lib.add_define("DISABLE_ANIMATION", Some("1"));
        }

        if cfg!(feature = "log_stack_usage") {
            lib.add_define("LOG_STACK_USAGE", Some("1"));
        }

        if cfg!(feature = "memperf") {
            lib.add_define("MICROPY_TREZOR_MEMPERF", Some("1"));
        }

        if cfg!(feature = "n4w1") {
            lib.add_define("USE_N4W1", Some("1"));
        }

        lib.add_define(
            "MICROPY_ENABLE_SOURCE_LINE",
            Some(if cfg!(feature = "enable_source_lines") {
                "1"
            } else {
                "0"
            }),
        );

        if cfg!(feature = "pyopt") {
            lib.add_define("PYOPT", Some("1"));
            lib.add_private_define("MICROPY_OOM_CALLBACK", Some("0"));
        } else {
            lib.add_define("PYOPT", Some("0"));
            // This is needed to compile modtrezorutils-meminfo.h that
            // calls STATIC functions in other modules
            lib.add_private_defines([("STATIC", Some("")), ("MICROPY_OOM_CALLBACK", Some("1"))]);
        }

        // TODO: remove this hack (causing cyclic dependence) by moving micropython
        // related code from trezor_lib into upymod.
        lib.add_private_include("../rust");

        lib.add_sources([
            "modutime.c",
            "rustmods.c",
            "trezorobj.c",
            "modtrezorapp/modtrezorapp.c",
            "modtrezorconfig/modtrezorconfig.c",
            "modtrezorcrypto/modtrezorcrypto.c",
            "modtrezorcrypto/crc.c",
            "modtrezorio/modtrezorio.c",
            "modtrezorui/modtrezorui.c",
            "modtrezorutils/modtrezorutils.c",
        ]);

        if cfg!(feature = "sd_card") {
            lib.add_sources(["modtrezorio/ff.c", "modtrezorio/ffunicode.c"]);
        }

        let attrs =
            cfg!(not(feature = "emulator")).then(|| xbuild::CompileAttrs::new().with_flag("-O3"));

        lib.add_sources_from_folder_with_attrs(
            mpy_dir,
            ["py/gc.c", "py/pystack.c", "py/vm.c"],
            attrs,
        );

        lib.add_sources_from_folder(
            mpy_dir,
            [
                "extmod/modubinascii.c",
                "extmod/moductypes.c",
                "extmod/moduheapq.c",
                "extmod/modutimeq.c",
                "extmod/utime_mphal.c",
                "shared/timeutils/timeutils.c",
                "py/argcheck.c",
                "py/asmarm.c",
                "py/asmbase.c",
                "py/asmthumb.c",
                "py/asmx64.c",
                "py/asmx86.c",
                "py/asmxtensa.c",
                "py/bc.c",
                "py/binary.c",
                "py/builtinevex.c",
                "py/builtinhelp.c",
                "py/builtinimport.c",
                "py/compile.c",
                "py/emitbc.c",
                "py/emitcommon.c",
                "py/emitglue.c",
                "py/emitinlinethumb.c",
                "py/emitnarm.c",
                "py/emitnative.c",
                "py/emitnthumb.c",
                "py/formatfloat.c",
                "py/frozenmod.c",
                "py/lexer.c",
                "py/malloc.c",
                "py/map.c",
                "py/modarray.c",
                "py/modbuiltins.c",
                "py/modcmath.c",
                "py/modcollections.c",
                "py/modgc.c",
                "py/modio.c",
                "py/modmath.c",
                "py/modmicropython.c",
                "py/modstruct.c",
                "py/modsys.c",
                "py/modthread.c",
                "py/moduerrno.c",
                "py/mpprint.c",
                "py/mpstate.c",
                "py/mpz.c",
                "py/nativeglue.c",
                "py/obj.c",
                "py/objarray.c",
                "py/objattrtuple.c",
                "py/objbool.c",
                "py/objboundmeth.c",
                "py/objcell.c",
                "py/objclosure.c",
                "py/objcomplex.c",
                "py/objdeque.c",
                "py/objdict.c",
                "py/objenumerate.c",
                "py/objexcept.c",
                "py/objfilter.c",
                "py/objfloat.c",
                "py/objfun.c",
                "py/objgenerator.c",
                "py/objgetitemiter.c",
                "py/objint.c",
                "py/objint_longlong.c",
                "py/objint_mpz.c",
                "py/objlist.c",
                "py/objmap.c",
                "py/objmodule.c",
                "py/objnamedtuple.c",
                "py/objnone.c",
                "py/objobject.c",
                "py/objpolyiter.c",
                "py/objproperty.c",
                "py/objrange.c",
                "py/objreversed.c",
                "py/objset.c",
                "py/objsingleton.c",
                "py/objslice.c",
                "py/objstr.c",
                "py/objstringio.c",
                "py/objstrunicode.c",
                "py/objtuple.c",
                "py/objtype.c",
                "py/objzip.c",
                "py/opmethods.c",
                "py/parse.c",
                "py/parsenum.c",
                "py/parsenumbase.c",
                "py/persistentcode.c",
                "py/qstr.c",
                "py/reader.c",
                "py/repl.c",
                "py/runtime.c",
                "py/runtime_utils.c",
                "py/scheduler.c",
                "py/scope.c",
                "py/sequence.c",
                "py/showbc.c",
                "py/smallint.c",
                "py/stackctrl.c",
                "py/stream.c",
                "py/unicode.c",
                "py/vstr.c",
                "py/warning.c",
            ],
        );

        if cfg!(feature = "emulator") {
            lib.add_defines([("MP_CONFIGFILE", Some("\"mpconfigport.h\""))]);

            if cfg!(feature = "frozen") {
                lib.add_define("TREZOR_EMULATOR_FROZEN", None);
            }

            // TODO: refactor modtrezorutils-meminfo.h to avoid this
            //
            // The hack is needed to compile modtrezorutils-meminfo.h that
            // calls STATIC functions in other modules
            lib.add_private_define("STATIC", Some(""));

            lib.add_sources_from_folder(
                mpy_dir,
                [
                    "extmod/vfs_posix_file.c",
                    "extmod/moduos.c",
                    "py/emitnx64.c",
                    "py/emitnx86.c",
                    "py/nlr.c",
                    "py/nlraarch64.c",
                    "py/nlrsetjmp.c",
                    "py/nlrthumb.c",
                    "py/nlrx64.c",
                    "py/nlrx86.c",
                    "py/profile.c",
                    "ports/unix/alloc.c",
                    "ports/unix/gccollect.c",
                    "ports/unix/input.c",
                    "ports/unix/unix_mphal.c",
                    "shared/runtime/gchelper_generic.c",
                    "shared/readline/readline.c",
                ],
            );
        } else if cfg!(feature = "mcu_stm32") {
            lib.add_sources_from_folder("../projects/firmware", ["mphalport.c", "nlrthumb.c"]);

            lib.add_sources_from_folder(
                mpy_dir,
                [
                    "ports/stm32/gccollect.c",
                    "shared/libc/abort_.c",
                    "shared/libc/printf.c",
                    "shared/runtime/gchelper_native.c",
                    "shared/runtime/interrupt_char.c",
                    "shared/runtime/pyexec.c",
                    "shared/runtime/stdout_helpers.c",
                    // "shared/runtime/gchelper_m3.s", // This file is added later
                ],
            );
        } else {
            bail_unsupported!();
        }

        // Include OUT_DIR for so the code can use #include <genhdr/xxx.h>
        lib.add_include(PathBuf::from(env::var("OUT_DIR").unwrap()));

        // Defines SCM_REVISION_INIT
        let scm_revision_xor2 = define_scm_revision(lib)?;

        // Build content of genhdr folder
        let mpy_builder = MpyBuilder::new(lib, scm_revision_xor2);
        let qstr_preprocessed = mpy_builder.build_genhdr()?;

        if cfg!(feature = "frozen") {
            // Build frozen_mpy.c if frozen modules are enabled
            let mpy_frozen_c = mpy_builder.build_frozen_modules(&qstr_preprocessed)?;
            lib.add_source(mpy_frozen_c);
        }

        if cfg!(not(feature = "emulator")) {
            // This file must not be preprocessed in MpyBuilder so it is added here
            // after the build_genhdr step
            lib.add_sources_from_folder(mpy_dir, ["shared/runtime/gchelper_m3.s"]);
        }

        Ok(())
    })
}

/// Extracts the Git revision, obfuscates it, and defines
/// SCM_REVISION_INIT together with two per-build XOR key bytes.
fn define_scm_revision(lib: &mut CLibrary) -> Result<u8> {
    let git_output = std::process::Command::new("git")
        .args(["rev-parse", "HEAD"])
        .output()
        .context("Failed to execute git command")?;

    ensure!(
        git_output.status.success(),
        "Git command failed: {}",
        String::from_utf8_lossy(&git_output.stderr)
    );

    let revision = String::from_utf8_lossy(&git_output.stdout);
    let revision = revision.trim();

    let mut revision = revision.as_bytes()[..4]
        .chunks_exact(2)
        .map(|chunk| {
            let hex = std::str::from_utf8(chunk).expect("git hash must be ASCII hex");
            u8::from_str_radix(hex, 16).expect("valid hex")
        })
        .collect::<Vec<u8>>();

    // Derive the XOR bytes from a standard FNV-1 hash of the whole revision.
    let fnv_hash = revision.iter().fold(0x811C9DC5u32, |hash, &byte| {
        hash.wrapping_mul(0x01000193) ^ u32::from(byte)
    });
    let hash_bytes = fnv_hash.to_le_bytes();
    let xor1 = hash_bytes[0] ^ hash_bytes[2];
    let xor2 = hash_bytes[1] ^ hash_bytes[3];

    // Apply both XOR keys in an alternating pattern to obfuscate the revision.
    for (index, byte) in revision.iter_mut().enumerate() {
        *byte ^= if index % 2 == 0 { xor1 } else { xor2 };
    }

    // Format the obfuscated revision and XOR values as an array of hex bytes.
    let scm_rev_init = revision
        .iter()
        .map(|byte| format!("0x{:02x},", byte))
        .collect::<String>();

    lib.add_private_defines([
        (
            "SCM_REVISION_LONG_INIT",
            Some(format!("{{{}}}", scm_rev_init)),
        ),
        ("SCM_REVISION_XOR1", Some(format!("0x{:02x}", xor1))),
        ("SCM_REVISION_XOR2", Some(format!("0x{:02x}", xor2))),
    ]);

    Ok(xor2)
}

struct MpyBuilder<'a> {
    lib: &'a CLibrary,
    crate_dir: PathBuf,
    mpy_dir: PathBuf,
    out_dir: PathBuf,
    genhdr_dir: PathBuf,
    py_src_dir: PathBuf,
    scm_revision_xor2: u8,
}

impl<'a> MpyBuilder<'a> {
    fn new(lib: &'a CLibrary, scm_revision_xor2: u8) -> Self {
        let crate_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
        let mpy_dir = crate_dir.join("../../vendor/micropython");
        let py_src_dir = crate_dir.join("../../src");
        let out_dir = PathBuf::from(env::var("OUT_DIR").unwrap());
        let genhdr_dir = out_dir.join("genhdr");

        Self {
            lib,
            crate_dir,
            mpy_dir,
            out_dir,
            genhdr_dir,
            py_src_dir,
            scm_revision_xor2,
        }
    }

    fn build_genhdr(&self) -> Result<PathBuf> {
        // Generate mpversion.h containing MPY_VERSION and MPY_GIT_TAG
        // macros based on Git metadata and the version in mpy_dir
        self.build_mpversion_header()?;

        // Extract all strings from protobuf .proto files and generate
        // qstrdefs.protobuf.h with corresponding Q(xxx) definitions.
        self.build_protobuf_headers()?;

        // Additional sourcess that do not live in the /upymod folder.
        // TODO: remove this hack by moving these sources (or part of them)
        // into upymod.
        let extra_sources = if cfg!(feature = "emulator") {
            [self.crate_dir.join("../projects/unix/main.c")]
        } else if cfg!(feature = "mcu_stm32") {
            [self.crate_dir.join("../projects/firmware/main.c")]
        } else {
            bail_unsupported!();
        };

        // Run the C preprocessor on all sources + extra_sources and store
        // the preprocessed output in corresponding .upydef files next to
        // each object file.
        let upydefs = self.lib.process_sources(
            "upydef",
            Some(&["-E", "-DNO_QSTR", "-DN_X64", "-DN_X86", "-DN_THUMB"]),
            Some(&extra_sources),
        )?;

        // Extract all MP_QSTR_xxx entries from preprocessed .upydef files
        // and store them in qstrdefs.collected.h as Q(xxx).
        let qstr_collected = self.build_qstrdefs_collected(&upydefs)?;

        // Extract all MP_REGISTER_MODULE entries from preprocessed .upydef
        // files and store them in moduledefs.collected.h.
        let moduledefs_collected = self.build_moduledefs_collected(&upydefs)?;

        // Generate MicroPython module definitions from
        // moduledefs.collected.h and store them in moduledefs.h, which can
        // be included directly in firmware.
        self.build_moduledefs(&moduledefs_collected)?;

        // Combine qstrdefs.collected.h with additional headers into
        // qstrdefs.combined.h. During this process, Q(xxx) is converted to
        // "Q(xxx)" so it passes through the next C preprocessing step
        // unchanged.
        let qstr_combined = self.build_qstrdefs_combined(&qstr_collected)?;

        // Run the C preprocessor on qstrdefs.combined.h and store the result
        // in qstrdefs.preprocessed.raw.h.
        let qstr_preprocessed_raw = self.build_qstrdefs_preprocessed_raw(&qstr_combined)?;

        // Process qstrdefs.preprocessed.raw.h to remove quotes around Q(xxx)
        // and store the result in qstrdefs.preprocessed.h.
        let qstr_preprocessed = self.build_qstrdefs_preprocessed(&qstr_preprocessed_raw)?;

        // Run makeqstrdata.py on qstrdefs.preprocessed.h to generate
        // qstrdefs.generated.h, which contains qstr definitions in a format
        // that can be included directly in firmware.
        let qstr_generated = self.build_qstrdefs_generated(&qstr_preprocessed)?;

        // Extract all MP_COMPRESSED_ROM_TEXT("xxx") entries from preprocessed
        // .upydef files and store them in compressed.collected.h as one value
        // per line.
        let compressed_collected = self.build_compressed_collected(&upydefs)?;

        // Run makecompresseddata.py on compressed.collected.h to generate
        // compressed.data.h with compressed data definitions in a format that
        // can be included directly in firmware.
        self.build_compressed_data(&compressed_collected)?;

        // Generate protobuf blobs based on .proto for Rust code.
        self.build_protobuf_blobs(&qstr_generated)?;

        Ok(qstr_preprocessed)
    }

    fn build_mpversion_header(&self) -> Result<()> {
        let output = self.genhdr_dir.join("mpversion.h");

        let mut cmd = std::process::Command::new("python3");
        let tool = self.mpy_dir.join("py/makeversionhdr.py");
        cmd.arg(&tool).arg(&output);

        xbuild::run_command(&mut cmd, &[tool], &[output]).context("Failed to build mpversion.h")?;

        Ok(())
    }

    fn collect_protobuf_inputs(&self, protob_dir: &Path) -> Result<InputFiles> {
        let mut inputs = InputFiles::new();

        inputs
            .add(protob_dir, "*.proto")
            .context("Failed to collect protobuf sources")?;

        inputs.remove(protob_dir, "messages-bootloader.proto");

        if cfg!(not(feature = "thp")) {
            inputs.remove(protob_dir, "messages-thp.proto");
        }

        if cfg!(feature = "pyopt") {
            inputs.remove(protob_dir, "messages-debug.proto");
        }

        Ok(inputs)
    }

    fn build_protobuf_headers(&self) -> Result<PathBuf> {
        let protob_dir = self.crate_dir.join("../../../common/protob");
        let output = self.genhdr_dir.join("qstrdefs.protobuf.h");
        let inputs = self.collect_protobuf_inputs(&protob_dir)?;
        let pb2py_path = protob_dir.join("pb2py");

        let mut cmd = std::process::Command::new(&pb2py_path);
        cmd.args(inputs.as_paths())
            .arg("--qstr-out")
            .arg(&output)
            .arg(format!(
                "--bitcoin-only={}",
                if cfg!(feature = "universal_fw") {
                    "0"
                } else {
                    "1"
                }
            ));

        let inputs = inputs.as_path_refs().chain(once(pb2py_path.as_path()));

        xbuild::run_command(&mut cmd, inputs, [&output])
            .context("Failed to build protobuf headers")?;

        Ok(output)
    }

    fn build_protobuf_blobs(&self, qstrdefs_generated: &Path) -> Result<()> {
        let protob_dir = self.crate_dir.join("../../../common/protob");

        let inputs = self.collect_protobuf_inputs(&protob_dir)?;
        let pb2py_path = protob_dir.join("pb2py");

        let blobs_dir = self.out_dir.join("protob_blobs");
        let outputs = [
            blobs_dir.join("proto_enums.data"),
            blobs_dir.join("proto_msgs.data"),
            blobs_dir.join("proto_names.data"),
            blobs_dir.join("proto_wire.data"),
        ];

        println!("cargo::metadata=protob_blobs_dir={}", blobs_dir.display());

        let mut cmd = std::process::Command::new(&pb2py_path);
        cmd.arg(format!(
            "--bitcoin-only={}",
            if cfg!(feature = "universal_fw") {
                "0"
            } else {
                "1"
            }
        ))
        .arg("--blob-outdir")
        .arg(&blobs_dir)
        .args(inputs.as_paths())
        .arg("--qstr-defs")
        .arg(qstrdefs_generated);

        let inputs = inputs
            .as_path_refs()
            .chain(once(qstrdefs_generated))
            .chain(once(pb2py_path.as_path()));

        xbuild::run_command(&mut cmd, inputs, &outputs)
            .context("Failed to build protobuf blobs")?;

        Ok(())
    }

    fn build_qstrdefs_collected(&self, upydef_files: &[PathBuf]) -> Result<PathBuf> {
        let output = self.genhdr_dir.join("qstrdefs.collected.h");
        let mut cmd = std::process::Command::new("sh");
        cmd
            .arg("-c")
            .arg(r#"out="$1"; shift; cat "$@" | perl -nle 'print "Q($1)" while /MP_QSTR_(\w+)/g' > "$out""#)
            .arg("sh")
            .arg(&output)
            .args(upydef_files);

        let inputs = upydef_files.iter().collect::<Vec<_>>();
        xbuild::run_command(&mut cmd, &inputs, [&output])
            .context("Failed to build qstrdefs collected")?;

        Ok(output)
    }

    fn build_moduledefs_collected(&self, upydef_files: &[PathBuf]) -> Result<PathBuf> {
        let output = self.genhdr_dir.join("moduledefs.collected.h");
        let mut cmd = std::process::Command::new("sh");
        cmd.arg("-c")
            .arg(r#"out="$1"; shift; grep '^MP_REGISTER_MODULE' "$@" > "$out""#)
            .arg("sh")
            .arg(&output)
            .args(upydef_files);

        let inputs = upydef_files.iter().collect::<Vec<_>>();
        xbuild::run_command(&mut cmd, &inputs, [&output])
            .context("Failed to build moduledefs collected")?;

        Ok(output)
    }

    fn build_moduledefs(&self, moduledefs_collected: &Path) -> Result<PathBuf> {
        let output = self.genhdr_dir.join("moduledefs.h");

        let mut cmd = std::process::Command::new("python3");
        let tool = self.mpy_dir.join("py/makemoduledefs.py");
        cmd.arg(&tool).arg(moduledefs_collected);

        let inputs = [tool, moduledefs_collected.to_path_buf()];
        xbuild::run_command_to_file(&mut cmd, &inputs, &output)
            .context("Failed to build moduledefs")?;

        Ok(output)
    }

    fn build_qstrdefs_generated(&self, qstr_preprocessed: &Path) -> Result<PathBuf> {
        let mut cmd = std::process::Command::new("python3");
        let tool = self.mpy_dir.join("py/makeqstrdata.py");
        cmd.arg(&tool).arg(qstr_preprocessed);

        let inputs = [tool, qstr_preprocessed.to_path_buf()];
        let output = self.genhdr_dir.join("qstrdefs.generated.h");
        xbuild::run_command_to_file(&mut cmd, &inputs, &output)
            .context("Failed to build qstrdefs generated")?;

        Ok(output)
    }

    fn build_qstrdefs_combined(&self, qstrdefs_collected: &Path) -> Result<PathBuf> {
        let output = self.genhdr_dir.join("qstrdefs.combined.h");

        let inputs = [
            self.mpy_dir.join("py/qstrdefs.h"),
            self.genhdr_dir.join("qstrdefs.protobuf.h"),
            qstrdefs_collected.to_path_buf(),
            self.crate_dir.join("qstrdefsport.h"),
        ];

        xbuild::emit_rerun_if_changed(&inputs);

        if xbuild::needs_rebuild(&inputs, &[&output]) {
            let mut output_file = File::create(&output)
                .unwrap_or_else(|_| panic!("Failed to create {}", output.display()));

            for input in &inputs {
                let file = File::open(input)
                    .unwrap_or_else(|_| panic!("Failed to open {}", input.display()));
                let reader = BufReader::new(file);
                for line in reader.lines() {
                    let line = line
                        .unwrap_or_else(|_| panic!("Failed to read line from {}", input.display()));
                    if line.starts_with("Q(") {
                        writeln!(output_file, "\"{}\"", line)
                    } else {
                        writeln!(output_file, "{}", line)
                    }
                    .unwrap_or_else(|_| panic!("Failed to write to {}", output.display()));
                }
            }
        }

        Ok(output)
    }

    fn build_qstrdefs_preprocessed_raw(&self, qstrdefs_combined: &Path) -> Result<PathBuf> {
        let output = self.genhdr_dir.join("qstrdefs.preprocessed.raw.h");
        self.lib
            .preprocess_file(qstrdefs_combined, &output)
            .context("Failed to preprocess qstr definitions")?;

        Ok(output)
    }

    fn build_qstrdefs_preprocessed(&self, qstr_preprocessed_raw: &Path) -> Result<PathBuf> {
        let output = self.genhdr_dir.join("qstrdefs.preprocessed.h");

        if xbuild::needs_rebuild(&[qstr_preprocessed_raw], &[&output]) {
            let input_file = File::open(qstr_preprocessed_raw)
                .with_context(|| format!("Failed to open {}", qstr_preprocessed_raw.display()))?;

            let reader = BufReader::new(input_file);

            let mut output_file = File::create(&output)
                .with_context(|| format!("Failed to create {}", output.display()))?;

            for line in reader.lines() {
                let line = line.unwrap_or_else(|_| {
                    panic!(
                        "Failed to read line from {}",
                        qstr_preprocessed_raw.display()
                    )
                });
                let processed_line = if line.starts_with("\"Q(") && line.ends_with('"') {
                    line[1..line.len() - 1].to_string()
                } else {
                    line
                };

                writeln!(output_file, "{}", processed_line)
                    .unwrap_or_else(|_| panic!("Failed to write line to {}", output.display()));
            }
        }

        Ok(output)
    }

    fn build_compressed_collected(&self, upydef_files: &[PathBuf]) -> Result<PathBuf> {
        let output = self.genhdr_dir.join("compressed.collected.h");
        let mut cmd = std::process::Command::new("sh");
        cmd.arg("-c")
            .arg(r#"out="$1"; shift; cat "$@" | sed -nr 's/.*MP_COMPRESSED_ROM_TEXT\("(.*)"\).*/\1/p' > "$out""#)
            .arg("sh")
            .arg(&output)
            .args(upydef_files);

        let inputs = upydef_files.iter().collect::<Vec<_>>();
        xbuild::run_command(&mut cmd, &inputs, [&output])
            .context("Failed to build compressed collected")?;
        Ok(output)
    }

    fn build_compressed_data(&self, compressed_collected: &Path) -> Result<PathBuf> {
        let mut cmd = std::process::Command::new("python3");
        let tool = self.mpy_dir.join("py/makecompresseddata.py");
        cmd.arg(&tool).arg(compressed_collected);

        let output = self.genhdr_dir.join("compressed.data.h");
        let inputs = [tool, compressed_collected.to_path_buf()];
        xbuild::run_command_to_file(&mut cmd, &inputs, &output)
            .context("Failed to build compressed data")?;
        Ok(output)
    }

    fn build_mpy_cross(&self) -> Result<PathBuf> {
        // Here we build `mpy-cross` by calling make directly, so dependency
        // tracking is left entirely to the makefiles in the mpy-cross source.

        // TODO: We do not emit any `cargo:rerun-if-changed` directives for the
        // mpy-cross sources, so if they change, the build script will not be
        // rerun and the changes will not take effect.

        // Build mpy-cross in the folder common for all models and targets
        let build_dir = self.out_dir.join("../../../../../mpy-cross");
        let mpy_cross = build_dir.join("mpy-cross");
        let source_dir = self.mpy_dir.join("mpy-cross");
        let mpycross_include = self.crate_dir.join("mpycross_include");

        let parallel_job_count = xbuild::optimal_parallel_job_count(16);

        let mut cmd = std::process::Command::new("make");
        cmd.args(["-j", &parallel_job_count.to_string()])
            .args(["-C", &source_dir.to_string_lossy()])
            .arg(format!("BUILD={}", &build_dir.to_string_lossy()))
            .arg(format!("PROG={}", &mpy_cross.to_string_lossy()))
            .env("INC", format!("-I{}", &mpycross_include.to_string_lossy()));

        let cmd_output = cmd
            .output()
            .with_context(|| format!("Failed to execute {:?}", cmd))?;

        // Check if the command executed successfully
        if !cmd_output.status.success() {
            bail!(xbuild::format_command_error(&cmd, &cmd_output));
        }

        Ok(mpy_cross)
    }

    fn build_frozen_modules(&self, qstr_preprocessed: &Path) -> Result<PathBuf> {
        // Create sed script for preprocessing .py files before feeding
        // them to mpy-cross.
        let sed_scripts = self.create_sed_scripts()?;

        // Get list of .py files to be frozen, based on the features enabled.
        let py_files = self
            .get_py_files()
            .context("Failed to collect frozen module sources")?;

        assert!(!py_files.as_paths().is_empty(), "No frozen modules found");

        let mpy_cross = self.build_mpy_cross()?;

        let compile_func =
            |file: &&PathBuf| self.build_frozen_module(file, &sed_scripts, &mpy_cross);

        // Run parallel compilation of .py files to .mpy using mpy-cross
        let mut mpy_files = xbuild::run_parallel(py_files.as_paths(), compile_func)
            .context("Failed to build frozen modules")?;

        // Sort .mpy files by their path to ensure deterministic order in the generated C file
        mpy_files.sort_by_key(|mpy_file| mpy_file.display().to_string());

        // Build C file from mpy modules
        let mut cmd = std::process::Command::new("python3");
        let tool = self.mpy_dir.join("tools/mpy-tool.py");
        cmd.arg(&tool)
            .arg("-f")
            .arg("-q")
            .arg(qstr_preprocessed)
            .args(&mpy_files);

        let inputs = once(tool.as_path())
            .chain(once(qstr_preprocessed))
            .chain(mpy_files.iter().map(PathBuf::as_path));

        let output = self.out_dir.join("frozen_mpy.c");
        xbuild::run_command_to_file(&mut cmd, inputs, &output)
            .context("Failed to build frozen modules")?;

        Ok(output)
    }

    fn build_frozen_module(
        &self,
        source: &Path,
        sed_scripts: &[String],
        mpy_cross: &Path,
    ) -> Result<PathBuf> {
        // Create .i file from .py source using sed to replace conditional
        // expressions with literal True/False
        let i_file = xbuild::derive_output_path(&self.crate_dir, source, &self.out_dir, "i");
        let mut cmd = std::process::Command::new("sed");
        cmd.args(sed_scripts).arg(source);

        xbuild::run_command_to_file(&mut cmd, [source], &i_file)
            .context("Failed to build frozen module (sed step)")?;

        // Choose optimization level for mpy-cross
        let opt_flag = if cfg!(feature = "pyopt") {
            "-O3"
        } else {
            "-O0"
        };

        let opt_source_lines = if cfg!(feature = "enable_source_lines") {
            "source-lines"
        } else {
            "no-source-lines"
        };

        // Make short name that appears in mpy-cross output
        let source_name = source.strip_prefix(&self.py_src_dir).unwrap_or(source);

        // Compile .i file to .mpy using mpy-cross.
        let mpy_file = i_file.with_extension("mpy").to_path_buf();
        let mut cmd = std::process::Command::new(mpy_cross);
        cmd.arg(opt_flag)
            .args(["-X", opt_source_lines])
            .arg("-o")
            .arg(&mpy_file)
            .arg("-s")
            .arg(source_name)
            .arg(&i_file);

        xbuild::run_command(&mut cmd, [&i_file], [&mpy_file])
            .context("Failed to build frozen module (mpy-cross step)")?;

        Ok(mpy_file)
    }

    // Builds sed scripts to replace conditional expressions with literal True/False
    // in frozen modules, so the compiler can optimize out the things we don't want.
    fn create_sed_scripts(&self) -> Result<Vec<String>> {
        let py_bool = |cond: bool| if cond { "True" } else { "False" };

        let backlight = py_bool(cfg!(feature = "backlight"));
        let ble = py_bool(cfg!(feature = "ble"));
        let btc_only = py_bool(cfg!(not(feature = "universal_fw")));
        let button = py_bool(cfg!(feature = "button"));
        let emulator = py_bool(cfg!(feature = "emulator"));
        let haptic = py_bool(cfg!(feature = "haptic"));
        let mcu_attestation = py_bool(cfg!(feature = "mcu_attestation"));
        let n4w1 = py_bool(cfg!(feature = "n4w1"));
        let optiga = py_bool(cfg!(feature = "optiga"));
        let power_manager = py_bool(cfg!(feature = "power_manager"));
        let rgb_led = py_bool(cfg!(feature = "rgb_led"));
        let telemetry = py_bool(cfg!(feature = "telemetry"));
        let thp = py_bool(cfg!(feature = "thp"));
        let touch = py_bool(cfg!(feature = "touch"));
        let tropic = py_bool(cfg!(feature = "tropic"));
        let scm_revision_xor2 = self.scm_revision_xor2;

        let layout_bolt = py_bool(cfg!(feature = "layout_bolt"));
        let layout_caesar = py_bool(cfg!(feature = "layout_caesar"));
        let layout_delizia = py_bool(cfg!(feature = "layout_delizia"));
        let layout_eckhart = py_bool(cfg!(feature = "layout_eckhart"));

        let mut exprs: Vec<String> = vec![
            format!(r"s/utils\.BITCOIN_ONLY/{btc_only}/g"),
            format!(r"s/utils\.EMULATOR/{emulator}/g"),
            format!(r"s/utils\.USE_BACKLIGHT/{backlight}/g"),
            format!(r"s/utils\.USE_BLE/{ble}/g"),
            format!(r"s/utils\.USE_BUTTON/{button}/g"),
            format!(r"s/utils\.USE_HAPTIC/{haptic}/g"),
            format!(r"s/utils\.USE_N4W1/{n4w1}/g"),
            format!(r"s/utils\.USE_MCU_ATTESTATION/{mcu_attestation}/g"),
            format!(r"s/utils\.USE_OPTIGA/{optiga}/g"),
            format!(r"s/utils\.USE_POWER_MANAGER/{power_manager}/g"),
            format!(r"s/utils\.USE_RGB_LED/{rgb_led}/g"),
            format!(r"s/utils\.USE_TELEMETRY/{telemetry}/g"),
            format!(r"s/utils\.USE_THP/{thp}/g"),
            format!(r"s/utils\.USE_TOUCH/{touch}/g"),
            format!(r"s/utils\.USE_TROPIC/{tropic}/g"),
            format!(r"s/utils\.SCM_REVISION_XOR2/{scm_revision_xor2}/g"),
            format!(r#"s/utils\.UI_LAYOUT == "BOLT"/{layout_bolt}/g"#),
            format!(r#"s/utils\.UI_LAYOUT == "CAESAR"/{layout_caesar}/g"#),
            format!(r#"s/utils\.UI_LAYOUT == "DELIZIA"/{layout_delizia}/g"#),
            format!(r#"s/utils\.UI_LAYOUT == "ECKHART"/{layout_eckhart}/g"#),
            r"s/if TYPE_CHECKING/if False/".to_string(),
            r"s/import typing/# &/".to_string(),
            r"/from typing import (/,/^[[:space:]]*)/ {s/^/# /; }".to_string(),
            r"s/from typing import/# &/".to_string(),
        ];

        for model in ["T2T1", "T2B1", "T3T1", "T3B1", "T3W1"] {
            let model_matches = match model {
                "D001" => cfg!(feature = "model_d001"),
                "D002" => cfg!(feature = "model_d002"),
                "T2T1" => cfg!(feature = "model_t2t1"),
                "T2B1" => cfg!(feature = "model_t2b1"),
                "T3T1" => cfg!(feature = "model_t3t1"),
                "T3B1" => cfg!(feature = "model_t3b1"),
                "T3W1" => cfg!(feature = "model_t3w1"),
                _ => bail_unsupported!(),
            };

            let model_cond = py_bool(model_matches);
            let not_model_cond = py_bool(!model_matches);

            exprs.push(format!(
                r#"s/utils\.INTERNAL_MODEL == "{model}"/{model_cond}/g"#
            ));
            exprs.push(format!(
                r#"s/utils\.INTERNAL_MODEL != "{model}"/{not_model_cond}/g"#
            ));
        }

        Ok(exprs
            .into_iter()
            .flat_map(|expr| ["-e".to_string(), expr])
            .collect())
    }

    fn get_py_files(&self) -> Result<InputFiles> {
        let mut files = InputFiles::new();

        let src = &self.py_src_dir;

        files.add(src, "*.py")?;

        if cfg!(not(feature = "ble")) {
            files.remove(src, "ble.py");
        }

        files.add(src.join("trezor"), "*.py")?;

        if cfg!(not(feature = "sd_card")) {
            files.remove(src, "trezor/sdcard.py");
        }

        files.add(src.join("trezor/crypto"), "*.py")?;
        files.add(src.join("trezor/ui"), "*.py")?;

        files.add(src.join("trezor/ui/layouts"), "*.py")?;

        if cfg!(not(feature = "universal_fw")) {
            files.remove(src, "trezor/ui/layouts/fido.py");
        }

        let layout_dir = &if cfg!(feature = "layout_bolt") {
            src.join("trezor/ui/layouts/bolt")
        } else if cfg!(feature = "layout_caesar") {
            src.join("trezor/ui/layouts/caesar")
        } else if cfg!(feature = "layout_delizia") {
            src.join("trezor/ui/layouts/delizia")
        } else if cfg!(feature = "layout_eckhart") {
            src.join("trezor/ui/layouts/eckhart")
        } else {
            bail_unsupported!();
        };

        files.add(layout_dir, "*.py")?;

        if cfg!(not(feature = "universal_fw")) {
            files.remove(layout_dir, "fido.py");
        }

        if cfg!(feature = "thp") {
            files.add(src.join("trezor/wire/thp"), "*.py")?;
        }

        if cfg!(not(feature = "thp")) || cfg!(not(feature = "pyopt")) {
            files.add(src.join("trezor/wire/codec"), "*.py")?;
        }

        files.add(src.join("trezor/wire"), "*.py")?;

        if cfg!(feature = "pyopt") {
            files.remove(src, "trezor/wire/wire_log.py");
        }

        if cfg!(feature = "power_manager") {
            files.add(src.join("trezor/power_management"), "*.py")?;
        }

        files.add(src.join("storage"), "*.py")?;

        if cfg!(not(feature = "sd_card")) {
            files.remove(src, "storage/sd_salt.py");
        }

        if cfg!(feature = "pyopt") {
            files.remove(src, "storage/debug.py");
        }

        if cfg!(feature = "thp") {
            files.remove(src, "storage/cache_codec.py");
            files.remove(src, "storage/cache_codec_keys.py");
        } else {
            files.remove(src, "storage/cache_thp.py");
            files.remove(src, "storage/cache_thp_keys.py");
        }

        let enums = &src.join("trezor/enums");

        files.add(enums, "*.py")?;

        files.remove(enums, "Cardano*.py");
        files.remove(enums, "DebugMonero*.py");
        files.remove(enums, "DefinitionType.py");
        files.remove(enums, "Eos*.py");
        files.remove(enums, "Ethereum*.py");
        files.remove(enums, "Monero*.py");
        files.remove(enums, "NEM*.py");
        files.remove(enums, "Ripple*.py");
        files.remove(enums, "Solana*.py");
        files.remove(enums, "Stellar*.py");
        files.remove(enums, "Tezos*.py");
        files.remove(enums, "Zcash*.py");
        files.remove(enums, "Tron*.py");

        if cfg!(feature = "pyopt") {
            files.remove(enums, "Debug*.py");
        }

        if cfg!(not(feature = "thp")) {
            files.remove(enums, "Thp*.py");
        }

        files.add(src, "apps/*.py")?;
        files.add(src, "apps/common/*.py")?;

        files.remove(src, "apps/common/definitions.py");
        files.remove(src, "apps/common/definitions_constants.py");

        if cfg!(not(feature = "sd_card")) {
            files.remove(src, "apps/common/sdcard.py");
        }

        if cfg!(not(feature = "pyopt")) {
            files.add(src, "apps/debug/*.py")?;

            if cfg!(not(feature = "model_t3w1")) {
                files.remove(src, "apps/debug/n4w1_mock.py");
            }
        }

        files.add(src, "apps/homescreen/*.py")?;

        if cfg!(not(feature = "model_t3w1")) {
            files.remove(src, "apps/homescreen/device_menu.py");
        }

        files.add(src, "apps/management/*.py")?;

        if cfg!(not(feature = "sd_card")) {
            files.remove(src, "apps/management/sd_protect.py");
        }

        if cfg!(not(feature = "optiga")) {
            files.remove(src, "apps/management/authenticate_device.py");
        }

        if cfg!(not(feature = "serial_number")) {
            files.remove(src, "apps/management/get_serial_number.py");
        }

        if cfg!(not(feature = "backlight")) {
            files.remove(src, "apps/management/set_brightness.py");
        }

        files.add(src, "apps/management/*/*.py")?;

        if cfg!(not(feature = "ble")) {
            files.remove(src, "apps/management/ble/*.py");
        }

        files.add(src, "apps/misc/*.py")?;

        if cfg!(feature = "telemetry") {
            files.add(src, "apps/telemetry/*.py")?;
        }

        files.add(src, "apps/bitcoin/*.py")?;
        files.add(src, "apps/bitcoin/*/*.py")?;

        files.remove(src, "apps/bitcoin/sign_tx/decred.py");
        files.remove(src, "apps/bitcoin/sign_tx/bitcoinlike.py");
        files.remove(src, "apps/bitcoin/sign_tx/zcash_v4.py");

        files.add(src, "apps/evolu/*.py")?;

        if cfg!(not(feature = "optiga")) {
            files.remove(src, "apps/evolu/sign_registration_request.py");
        }

        if cfg!(feature = "benchmark") {
            files.add(src, "apps/benchmark/*.py")?;
        }

        if cfg!(feature = "thp") {
            files.add(src, "apps/thp/*.py")?;
        }

        if cfg!(feature = "universal_fw") {
            files.add(src, "apps/common/definitions.py")?;
            files.add(src, "apps/common/definitions_constants.py")?;
            files.add(src, "trezor/enums/DefinitionType.py")?;

            files.add(src, "apps/cardano/*.py")?;
            files.add(src, "apps/cardano/*/*.py")?;
            files.add(src, "trezor/enums/Cardano*.py")?;

            if cfg!(feature = "model_t2t1") {
                files.add(src, "apps/eos/*.py")?;
                files.add(src, "apps/eos/*/*.py")?;
                files.add(src, "trezor/enums/Eos*.py")?;
            }

            files.add(src, "apps/ethereum/*.py")?;
            files.add(src, "trezor/enums/Ethereum*.py")?;

            files.add(src, "apps/monero/*.py")?;
            files.add(src, "apps/monero/*/*.py")?;
            files.add(src, "apps/monero/*/*/*.py")?;
            files.add(src, "trezor/enums/DebugMonero*.py")?;
            files.add(src, "trezor/enums/Monero*.py")?;

            if cfg!(feature = "model_t2t1") {
                files.add(src, "apps/nem/*.py")?;
                files.add(src, "apps/nem/*/*.py")?;
                files.add(src, "trezor/enums/NEM*.py")?;
            }

            if cfg!(not(feature = "pyopt")) {
                files.add(src, "apps/nostr/*.py")?;
                files.add(src, "apps/nostr/*/*.py")?;
                files.add(src, "trezor/enums/Nostr*.py")?;
            }

            files.add(src, "apps/tron/*.py")?;
            files.add(src, "trezor/enums/Tron*.py")?;

            files.add(src, "apps/ripple/*.py")?;
            files.add(src, "trezor/enums/Ripple*.py")?;

            files.add(src, "apps/solana/*.py")?;
            files.add(src, "apps/solana/*/*.py")?;
            files.add(src, "trezor/enums/Solana*.py")?;

            files.add(src, "apps/stellar/*.py")?;
            files.add(src, "apps/stellar/*/*.py")?;
            files.add(src, "trezor/enums/Stellar*.py")?;

            files.add(src, "apps/tezos/*.py")?;
            files.add(src, "trezor/enums/Tezos*.py")?;

            files.add(src, "apps/zcash/*.py")?;

            files.add(src, "apps/webauthn/*.py")?;

            if cfg!(feature = "model_t2t1") {
                files.add(src, "apps/bitcoin/sign_tx/decred.py")?;
            }

            files.add(src, "apps/bitcoin/sign_tx/bitcoinlike.py")?;
            files.add(src, "apps/bitcoin/sign_tx/zcash_v4.py")?;
            files.add(src, "trezor/enums/Zcash*.py")?;
        }

        if cfg!(not(feature = "pyopt")) && cfg!(not(feature = "emulator")) {
            files.add(src, "prof/*.py")?;
        }

        Ok(files)
    }
}
