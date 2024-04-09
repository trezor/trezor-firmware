mod unix_ffi {
    const STDOUT_FILENO: cty::c_int = 1;

    extern "C" {
        pub fn write(fd: cty::c_int, buf: *const u8, count: cty::size_t) -> cty::ssize_t;
    }

    pub fn print(to_log: &str) {
        unsafe {
            write(STDOUT_FILENO, to_log.as_ptr(), to_log.len() as cty::size_t);
        }
    }
}

#[cfg(feature = "micropython")]
use crate::micropython::print::print;
#[cfg(not(feature = "micropython"))]
pub use unix_ffi::print;

pub struct DebugConsole;

impl ufmt::uWrite for DebugConsole {
    type Error = core::convert::Infallible;

    fn write_str(&mut self, s: &str) -> Result<(), Self::Error> {
        print(s);
        Ok(())
    }
}
