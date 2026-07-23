#[cfg(feature = "debug")]
use alloc::vec::Vec;
use core::ops::Deref;

#[derive(Clone)]
pub struct ErrorTrace<E> {
    pub error: E,
    #[cfg(feature = "debug")]
    pub trace: Vec<&'static str>,
}

impl<E> ErrorTrace<E> {
    pub fn new(error: E) -> Self {
        Self {
            error,
            #[cfg(feature = "debug")]
            trace: Vec::new(),
        }
    }

    #[allow(unused_variables)]
    pub fn trace(&mut self, context: &'static str) {
        #[cfg(feature = "debug")]
        self.trace.push(context);
    }

    pub fn into_inner(self) -> E {
        self.error
    }
}

impl<E> From<E> for ErrorTrace<E> {
    fn from(error: E) -> Self {
        Self::new(error)
    }
}

impl<E> Deref for ErrorTrace<E> {
    type Target = E;

    fn deref(&self) -> &Self::Target {
        &self.error
    }
}

#[cfg(feature = "debug")]
impl<E: ufmt::uDebug> ufmt::uDebug for ErrorTrace<E> {
    fn fmt<W>(&self, w: &mut ufmt::Formatter<'_, W>) -> core::result::Result<(), W::Error>
    where
        W: ufmt::uWrite + ?Sized,
    {
        self.error.fmt(w)?;
        w.write_str("\nCaused by:\n")?;
        for context in self.trace.iter().rev() {
            w.write_str("  ")?;
            w.write_str(context)?;
            w.write_str("\n")?;
        }
        Ok(())
    }
}

pub type Result<T, E> = core::result::Result<T, ErrorTrace<E>>;

pub trait ResultExt<T, E> {
    fn context(self, context: &'static str) -> Result<T, E>;
}

impl<T, E> ResultExt<T, E> for Result<T, E> {
    fn context(self, context: &'static str) -> Result<T, E> {
        self.map_err(|mut e| {
            e.trace(context);
            e
        })
    }
}
