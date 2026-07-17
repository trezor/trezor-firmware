mod attrs;
mod clibrary;
mod dep_tracking;
mod helpers;
mod input_files;
mod parallel;
mod trezor;

pub use attrs::CompileAttrs;
pub use clibrary::CLibrary;
pub use clibrary::compile::OutputType;
// Re-exports from color_eyre
pub use color_eyre::Result;
pub use color_eyre::eyre::{WrapErr, bail, ensure};
pub use dep_tracking::{
    format_command_error, needs_rebuild, run_command, run_command_to_file, run_if_changed,
};
pub use helpers::{cargo_target_dir, derive_output_path, emit_rerun_if_changed, is_rust_analyzer};
pub use input_files::InputFiles;
pub use parallel::{optimal_parallel_job_count, run_parallel};
pub use trezor::{build, build_and_link, current_model_id, model_ids, vendor_header_path};

/// Return early with an error.
///
/// This macro is equivalent to `return Err(eyre!("Unsupported
/// Configuration"))`.
///
/// Use in situations where the current configuration or any combination
/// of features is not supported and the code cannot proceed.
#[macro_export]
macro_rules! bail_unsupported {
    () => {
        ::color_eyre::eyre::bail!("Unsupported configuration");
    };
}

#[macro_export]
/// A helper macro to define build modules in a concise way.
/// It takes a list of module names and optional conditions, and
/// calls `def_module` for each module that meets the condition (if any).
///
/// Usage:
/// ```ignore
/// use xbuild::build_mods;
/// #[path = "module1/build.rs"] mod module1;
/// #[path = "module2/build.rs"] mod module2;
/// #[path = "module3/build.rs"] mod module3;
///
/// build_mods!(lib, [
///    module1,
///    module2 if cfg!(feature = "some_feature"),
///    module3 if cfg!(feature = "another_feature"),
/// ]);
/// ```
macro_rules! build_mods {
    ($lib:expr, [ $( $name:ident $(if $cond:expr)? ),* $(,)? ]) => {
        $(
            if true $(&& $cond)? {
                $name::def_module($lib)?;
            }
        )*
    };
}
