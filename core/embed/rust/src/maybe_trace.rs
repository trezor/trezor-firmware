#[cfg(feature = "ui_debug")]
mod maybe_trace_private {
    use crate::trace::Trace;

    pub trait MaybeTrace: Trace {}
    impl<T> MaybeTrace for T where T: Trace {}
}

#[cfg(not(feature = "ui_debug"))]
mod maybe_trace_private {
    pub trait MaybeTrace {}
    impl<T> MaybeTrace for T {}
}

pub use maybe_trace_private::MaybeTrace;
