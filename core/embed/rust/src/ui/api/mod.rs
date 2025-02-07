pub mod common_c;

#[cfg(feature = "bootloader")]
pub mod bootloader_c;

#[cfg(feature = "micropython")]
pub mod firmware_micropython;

#[cfg(feature = "prodtest")]
pub mod prodtest_c;
