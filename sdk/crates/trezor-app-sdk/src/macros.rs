pub trait UnwrapOrFatalError<T> {
    fn unwrap_or_fatal_error(self, msg: &str, file: &str, line: u32) -> T;
}

impl<T> UnwrapOrFatalError<T> for Option<T> {
    fn unwrap_or_fatal_error(self, msg: &str, file: &str, line: u32) -> T {
        match self {
            Some(x) => x,
            None => crate::low_level_api::system_exit_fatal(msg, file, line as i32),
        }
    }
}

impl<T, E> UnwrapOrFatalError<T> for Result<T, E> {
    fn unwrap_or_fatal_error(self, msg: &str, file: &str, line: u32) -> T {
        match self {
            Ok(x) => x,
            Err(_) => crate::low_level_api::system_exit_fatal(msg, file, line as i32),
        }
    }
}

/// Unwraps an [`Option`] or [`Result`], triggering a fatal error on failure.
///
/// On failure calls [`system_exit_fatal`](crate::low_level_api::system_exit_fatal)
/// with the file name, line number, and an optional custom message.
///
/// # Forms
///
/// **Without message** — failure prints `"unwrap failed"`:
/// ```
/// # use trezor_app_sdk::unwrap;
/// assert_eq!(unwrap!(Ok::<i32, &str>(42)), 42);
/// assert_eq!(unwrap!(Some(7)), 7);
/// ```
///
/// **With custom message** — failure prints the given message:
/// ```
/// # use trezor_app_sdk::unwrap;
/// assert_eq!(unwrap!(Ok::<i32, &str>(42), "must be Ok"), 42);
/// assert_eq!(unwrap!(Some(7), "must be Some"), 7);
/// ```
///
/// **Failing values** trigger a fatal error — do not run in tests:
/// ```no_run
/// # use trezor_app_sdk::unwrap;
/// unwrap!(Err::<i32, &str>("oops"));           // fatal — "unwrap failed"
/// unwrap!(Err::<i32, &str>("oops"), "message"); // fatal — custom message
/// unwrap!(None::<i32>);                         // fatal — "unwrap failed"
/// ```
#[macro_export]
macro_rules! unwrap {
    ($e:expr, $msg:expr) => {{
        use $crate::macros::UnwrapOrFatalError;
        $e.unwrap_or_fatal_error($msg, file!(), line!())
    }};
    ($expr:expr) => {
        unwrap!($expr, "unwrap failed")
    };
}

/// Macro to generate handler functions.
///
/// `$codec` selects the wire serializer: a type implementing
/// [`WireDecode<$request_type>`](crate::WireDecode) and `WireEncode` for
/// whatever the handler returns. Apps own this type, so the SDK itself has
/// no dependency on any particular serializer.
#[macro_export]
macro_rules! wire_handler {
    ($handler_name:ident, $codec:ty, $request_type:ty, $response_msg:expr, $handler_fn:path) => {
        #[inline(never)]
        fn $handler_name(request_data: &[u8]) -> $crate::Result<()> {
            let request = $crate::ResultExt::c(
                <$codec as $crate::WireDecode<$request_type>>::decode(request_data),
            )?;

            match $handler_fn(request) {
                Ok(resp) => {
                    let response_bytes = <$codec as $crate::WireEncode<_>>::encode(&resp);
                    $crate::wire_respond_raw($response_msg as i32, &response_bytes)
                }
                Err(e) => $crate::wire_error_raw(&e),
            }
        }
    };
}

/// Declares `$req`'s response type and wire id for [`$crate::wire_request`],
/// so callers don't have to repeat both at every call site.
#[macro_export]
macro_rules! wire_request_type {
    ($req:ty => $resp:ty, $id:expr) => {
        impl $crate::WireRequest for $req {
            type Response = $resp;
            const ID: u16 = $id as u16;
        }
    };
}
