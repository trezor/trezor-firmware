mod attrs;
mod clibrary;
mod dep_tracking;
mod helpers;
mod input_files;
mod parallel;
mod trezor;

pub use attrs::CompileAttrs;
pub use clibrary::CLibrary;
pub use input_files::InputFiles;

pub use dep_tracking::format_command_error;
pub use dep_tracking::needs_rebuild;
pub use dep_tracking::run_command;
pub use dep_tracking::run_command_to_file;
pub use dep_tracking::run_if_changed;

pub use helpers::derive_output_path;
pub use helpers::emit_rerun_if_changed;
pub use helpers::rust_analyser_is_running;

pub use parallel::optimal_parallel_job_count;
pub use parallel::run_parallel;

pub use trezor::build;
pub use trezor::build_and_link;
pub use trezor::current_model_id;
pub use trezor::vendor_header_path;

// Re-exports from color_eyre
pub use color_eyre::Result;
pub use color_eyre::eyre::WrapErr;
pub use color_eyre::eyre::bail;
pub use color_eyre::eyre::ensure;

/// Return early with an error.
///
/// This macro is equivalent to `return Err(eyre!("Unsupported Configuration"))`.
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
/// A helper macro like `build_mods!` that uses bracketed, comma-separated syntax.
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
