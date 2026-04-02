use std::path::Path;

use color_eyre::{
    Result,
    eyre::{WrapErr, bail},
};

use super::CLibrary;
use crate::dep_tracking::{run_command, run_if_changed};
use crate::helpers::{derive_output_path, ensure_parent_directory, path_from_env};

use zlib_rs::{DeflateConfig, ReturnCode, compress_bound, compress_slice};

impl CLibrary {
    /// Embeds a binary file into the library by converting it into an object
    /// file with symbols.
    ///
    /// The binary data will be accessible in C code via symbols named
    /// `<section>_start`, `<section>_end` and `<section>_size`.
    pub fn embed_binary(&mut self, binary_path: impl AsRef<Path>, section: &str) -> Result<()> {
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

        let mut cmd = std::process::Command::new("arm-none-eabi-objcopy");

        cmd.args(["-I", "binary"])
            .args(["-O", "elf32-littlearm"])
            .args(["-B", "arm"])
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
        let binary_path = binary_path.as_ref();

        let base_dir = path_from_env("CARGO_MANIFEST_DIR")?;
        let out_dir = path_from_env("OUT_DIR")?;
        let compressed_path = derive_output_path(&base_dir, binary_path, &out_dir, "z");

        run_if_changed([binary_path], [&compressed_path], None, None, || {
            self.compress_file(binary_path, &compressed_path)
        })?;

        self.embed_binary(compressed_path, section)
    }

    /// Compresses a file using zlib and write the compressed data to an output file.
    fn compress_file(&self, input: impl AsRef<Path>, output: impl AsRef<Path>) -> Result<()> {
        let input = input.as_ref();
        let output = output.as_ref();

        ensure_parent_directory(output)?;

        let data_in = std::fs::read(input)
            .with_context(|| format!("Failed to read binary `{}`", input.display()))?;

        let mut data_out = vec![0u8; compress_bound(data_in.len())];

        let config = DeflateConfig::best_compression();
        let (compressed, code) = compress_slice(&mut data_out, &data_in, config);

        if code != ReturnCode::Ok {
            bail!(
                "Failed to compress binary `{}`: {:?}",
                input.display(),
                code
            );
        }

        std::fs::write(output, compressed).with_context(|| {
            format!(
                "Failed to write compressed binary to `{}`",
                output.display()
            )
        })?;

        Ok(())
    }
}
