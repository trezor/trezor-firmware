use ufmt;

#[cfg(feature = "micropython")]
use crate::micropython;

pub struct DebugConsole;

impl ufmt::uWrite for DebugConsole {
    type Error = core::convert::Infallible;

    fn write_str(&mut self, s: &str) -> Result<(), Self::Error> {
        #[cfg(feature = "micropython")]
        micropython::print::print(s);

        // TODO: add alternative if micropython is not available

        Ok(())
    }
}

#[macro_export]
macro_rules! dbg_println {
    ($($args:tt)*) => {
        ufmt::uwriteln!($crate::debug::DebugConsole, $($args)*).ok();
    };
}

#[macro_export]
macro_rules! dbg_print {
    ($($args:tt)*) => {
        ufmt::uwrite!($crate::debug::DebugConsole, $($args)*).ok();
    };
}
