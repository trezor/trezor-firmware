use xbuild::{Result, WrapErr, ensure};

use std::process::Command;

fn main() -> Result<()> {
    xbuild::build(|lib| {
        lib.import_lib("models")?;

        lib.add_include("inc");

        lib.add_define("SCM_REVISION_SHORT_INIT", Some(&get_scm_revision_short()?));

        lib.add_sources([
            "cli.c",
            "error_handling.c",
            "scm_revision.c",
            "strutils.c",
            "unit_test.c",
        ]);

        if cfg!(any(feature = "sprintf", not(feature = "production"))) {
            lib.add_source("printf.c");
        }

        add_uzlib(lib);

        if cfg!(feature = "test") {
            lib.add_source("src/test_setup.c");
        }

        Ok(())
    })
}

/// Extracts the first four bytes of the Git revision and formats them
/// as a C initializer list, e.g. {0x12, 0x34, 0x56, 0x78}.
fn get_scm_revision_short() -> Result<String> {
    let git_output = Command::new("git")
        .args(["rev-parse", "HEAD"])
        .output()
        .context("Failed to execute git command")?;

    ensure!(
        git_output.status.success(),
        "Git command failed: {}",
        String::from_utf8_lossy(&git_output.stderr)
    );

    let git_hash = String::from_utf8_lossy(&git_output.stdout);
    let git_hash = git_hash.trim();

    ensure!(
        git_hash.len() >= 8 && git_hash.chars().all(|c| c.is_ascii_hexdigit()),
        "Unexpected git hash format: {}",
        git_hash
    );

    let init_val = git_hash.as_bytes()[..8]
        .chunks(2)
        .map(|chunk| {
            format!(
                "0x{},",
                std::str::from_utf8(chunk).expect("git hash must be valid ASCII")
            )
        })
        .collect::<String>();

    Ok(format!("{{{}}}", init_val))
}

fn add_uzlib(lib: &mut xbuild::CLibrary) {
    let uzlib_path = "../../vendor/micropython/lib/uzlib";

    lib.add_include(uzlib_path);

    lib.add_sources_in_dir(uzlib_path, ["adler32.c", "crc32.c", "tinflate.c"]);
}
