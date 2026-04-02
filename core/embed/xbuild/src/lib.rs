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

pub use dep_tracking::needs_rebuild;
pub use dep_tracking::run_command;
pub use dep_tracking::run_command_to_file;
pub use dep_tracking::run_if_changed;

pub use helpers::derive_output_path;
pub use helpers::rust_analyser_is_running;

pub use parallel::run_parallel;

pub use trezor::build;
pub use trezor::build_and_link;
pub use trezor::current_model_id;
pub use trezor::vendor_header_path;

// Re-exports from color_eyre
pub use color_eyre::Result;
pub use color_eyre::eyre::WrapErr;
pub use color_eyre::eyre::bail;

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

/// A helper macro to define multiple modules in a concise way.
///
/// Usage:
/// ```
/// build_mods!(lib;
///    module1,
///    module2 if cfg!(feature = "some_feature"),
///    module3 if cfg!(feature = "another_feature"),
/// );
/// ```
#[macro_export]
macro_rules! build_mods {
    ($lib:expr; $( $name:ident $(if $cond:expr)? ),* $(,)?) => {
        $(
            mod $name {
                include!(concat!(stringify!($name), "/build.rs"));
            }

            if true $(&& $cond)? {
                $name::def_module($lib)?;
            }
        )*
    };
}
