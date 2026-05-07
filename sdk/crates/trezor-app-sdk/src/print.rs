mod unix_ffi {
    const STDOUT_FILENO: cty::c_int = 1;

    unsafe extern "C" {
        pub unsafe fn write(fd: cty::c_int, buf: *const u8, count: cty::size_t) -> cty::ssize_t;
    }

    pub fn print(to_log: &str) {
        // SAFETY: We're passing valid pointers and sizes.
        unsafe {
            write(STDOUT_FILENO, to_log.as_ptr(), to_log.len() as cty::size_t);
        }
    }
}

#[derive(Clone, Copy, Default)]
enum Printer {
    #[cfg(not(target_os = "none"))]
    #[cfg_attr(not(target_os = "none"), default)]
    Unix,
    #[cfg_attr(target_os = "none", default)]
    None,
    Api,
}

impl Printer {
    const fn initial() -> Self {
        #[cfg(not(target_os = "none"))]
        return Printer::Unix;
        #[cfg(target_os = "none")]
        return Printer::None;
    }

    fn print(&self, to_log: &str) {
        match self {
            #[cfg(not(target_os = "none"))]
            Printer::Unix => unix_ffi::print(to_log),
            Printer::None => (),
            Printer::Api => crate::low_level_api::dbg_console_write(to_log.as_bytes()),
        }
    }
}

impl ufmt::uWrite for Printer {
    type Error = core::convert::Infallible;

    fn write_str(&mut self, s: &str) -> Result<(), Self::Error> {
        self.print(s);
        Ok(())
    }
}

static PRINTER: spin::RwLock<Printer> = spin::RwLock::new(Printer::initial());

pub(super) fn enable_api_printer() {
    *PRINTER.try_write().unwrap() = Printer::Api;
}

pub fn printer() -> impl ufmt::uWrite {
    *PRINTER.try_read().unwrap()
}

pub fn print(to_log: &str) {
    PRINTER.try_read().unwrap().print(to_log);
}

