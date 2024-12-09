mod blob;
pub mod flash;
mod generated;
#[cfg(feature = "micropython")]
mod obj;
mod public_keys;
mod translated_string;

pub use blob::Translations;
pub use translated_string::TranslatedString as TR;

pub const DEFAULT_LANGUAGE: &str = "en-US";
