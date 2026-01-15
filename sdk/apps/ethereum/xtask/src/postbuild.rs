use crate::{
    args::{Language, Model},
    helpers,
};
use anyhow::{Context, Ok, Result};
use std::path::Path;

pub use crate::tools::zero_symnames;

/// Publishes a built binary by copying it to the `published` directory with a name that includes
pub fn publish_artifact(
    binary: &Path,
    app: &str,
    model: Model,
    lang: Language,
    emulator: bool,
) -> Result<()> {
    let dir = helpers::artifacts_dir(model, lang, emulator)?;
    helpers::ensure_directory(&dir)?;

    let name = format!("{}.elf", app);

    std::fs::copy(binary, dir.join(&name)).with_context(|| {
        format!(
            "Failed to copy `{}` to `{}`",
            binary.display(),
            dir.join(&name).display()
        )
    })?;

    Ok(())
}
