use std::path::Path;

use color_eyre::Result;
use color_eyre::eyre::{WrapErr, ensure};
use zlib_rs::{DeflateConfig, ReturnCode, compress_bound, compress_slice};

use super::CLibrary;
use crate::dep_tracking::{run_command, run_if_changed};
use crate::helpers::{derive_output_path, ensure_parent_directory, path_from_env};
use crate::is_rust_analyzer;

/// The `objcopy` and output format for the target currently being built.
///
/// `embed_binary` turns a raw file into an object file, and that object has to
/// carry the architecture of whatever will link it. Device builds cross-compile
/// with `arm-none-eabi-objcopy`; an emulator build links a host binary and
/// needs the host's, so the choice comes from `CARGO_CFG_TARGET_ARCH` rather
/// than being fixed. Unknown architectures fail loudly here: a wrong object is
/// a link error that names the file and not the cause.
fn objcopy_for_target() -> Result<(&'static str, &'static str, &'static str)> {
    let arch = std::env::var("CARGO_CFG_TARGET_ARCH").unwrap_or_default();
    match arch.as_str() {
        "arm" => Ok(("arm-none-eabi-objcopy", "elf32-littlearm", "arm")),
        "x86_64" => Ok(("objcopy", "elf64-x86-64", "i386:x86-64")),
        "aarch64" => Ok(("objcopy", "elf64-littleaarch64", "aarch64")),
        other => Err(color_eyre::eyre::eyre!(
            "embed_binary does not know which object format to emit for target \
             architecture `{other}` -- add it to objcopy_for_target"
        )),
    }
}

impl CLibrary {
    /// Embeds a binary file into the library by converting it into an object
    /// file with symbols.
    ///
    /// The binary data will be accessible in C code via symbols named
    /// `<section>_start`, `<section>_end` and `<section>_size`.
    pub fn embed_binary(&mut self, binary_path: impl AsRef<Path>, section: &str) -> Result<()> {
        if is_rust_analyzer() && !binary_path.as_ref().exists() {
            // Prevent errors due to missing binary files when running rust-analyser.
            return Ok(());
        }

        let binary_path = binary_path.as_ref();

        let redefine_sym = |suffix: &str| {
            let src = format!(
                "_binary_{}_{}",
                binary_path
                    .to_string_lossy()
                    .replace("/", "_")
                    .replace(".", "_")
                    .replace("-", "_"),
                suffix
            );
            let dst = format!("{}_{}", section, suffix);
            ["--redefine-sym".to_string(), format!("{src}={dst}")]
        };

        let base_dir = path_from_env("CARGO_MANIFEST_DIR")?;
        let out_dir = path_from_env("OUT_DIR")?;
        let output = derive_output_path(&base_dir, binary_path, &out_dir, "o");

        // The object has to match the target being linked, not the device we
        // usually build for: an emulator links a HOST binary, and an ARM object
        // in it fails at link time with "incompatible with elf64-x86-64" --
        // which reads as a corrupt file rather than the wrong architecture.
        let (objcopy, output_format, binary_arch) = objcopy_for_target()?;

        let mut cmd = std::process::Command::new(objcopy);

        cmd.args(["-I", "binary"])
            .args(["-O", output_format])
            .args(["-B", binary_arch])
            .args(["--rename-section", &format!(".data=.{section}")])
            .args(redefine_sym("start"))
            .args(redefine_sym("end"))
            .args(redefine_sym("size"))
            .arg(binary_path)
            .arg(&output);

        run_command(&mut cmd, [binary_path], [&output])
            .context(format!("Failed to build {}", output.display()))?;

        self.add_object(output);
        Ok(())
    }

    /// Embeds a binary file into the library by compressing it and then
    /// embedding the compressed data.
    ///
    /// The compressed data will be accessible in C code via symbols named
    /// `<section>_start`, `<section>_end` and `<section>_size`.
    pub fn embed_compressed_binary(
        &mut self,
        binary_path: impl AsRef<Path>,
        section: &str,
    ) -> Result<()> {
        if is_rust_analyzer() && !binary_path.as_ref().exists() {
            // Prevent errors due to missing binary files when running rust-analyser.
            return Ok(());
        }

        let binary_path = binary_path.as_ref();

        let base_dir = path_from_env("CARGO_MANIFEST_DIR")?;
        let out_dir = path_from_env("OUT_DIR")?;
        let compressed_path = derive_output_path(&base_dir, binary_path, &out_dir, "z");

        run_if_changed([binary_path], [&compressed_path], None, None, || {
            self.compress_file(binary_path, &compressed_path)
        })?;

        self.embed_binary(compressed_path, section)
    }

    /// Compresses a file using zlib and write the compressed data to an output
    /// file.
    fn compress_file(&self, input: impl AsRef<Path>, output: impl AsRef<Path>) -> Result<()> {
        let input = input.as_ref();
        let output = output.as_ref();

        ensure_parent_directory(output)?;

        let data_in = std::fs::read(input)
            .with_context(|| format!("Failed to read binary `{}`", input.display()))?;

        let mut data_out = vec![0u8; compress_bound(data_in.len())];

        let config = DeflateConfig {
            // < 0 => raw deflate stream (no zlib header)
            // -10 => 1KB window
            window_bits: -10,
            ..DeflateConfig::best_compression()
        };

        let (compressed, code) = compress_slice(&mut data_out, &data_in, config);

        ensure!(
            code == ReturnCode::Ok,
            "Failed to compress binary `{}`: {:?}",
            input.display(),
            code
        );

        std::fs::write(output, compressed).with_context(|| {
            format!(
                "Failed to write compressed binary to `{}`",
                output.display()
            )
        })?;

        Ok(())
    }
}
