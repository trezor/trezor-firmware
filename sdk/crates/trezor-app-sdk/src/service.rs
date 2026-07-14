//! IPC service abstractions for communicating with the Core application.
//!
//! This module provides typed remote endpoints, utility message handling traits,
//! and a macro for declaring static IPC service instances.

use core::marker::PhantomData;

use ufmt::derive::uDebug;

use crate::ipc::{IpcInbox, IpcMessage, RemoteSysTask};
use crate::sysevent::SysEvents;
use crate::util::Timeout;

/// The remote system task identifier for the Core application service.
pub const CORE_SERVICE_REMOTE: RemoteSysTask = RemoteSysTask::CoreApp;

/// Identifies the IPC services provided by the Core application.
#[derive(uDebug, Copy, Clone, PartialEq, Eq, num_enum::IntoPrimitive, num_enum::FromPrimitive)]
#[repr(u16)]
pub enum CoreIpcService {
    WireStart = 0,
    WireContinue = 1,
    WireEnd = 2,
    WireError = 3,
    Ui = 4,
    Progress = 5,
    Crypto = 6,
    /// Catch-all variant for unrecognized service IDs.
    #[num_enum(catch_all)]
    Unknown(u16),
}

/// A typed IPC remote endpoint for sending requests and receiving responses.
///
/// `T` is the service enum type (e.g. [`CoreIpcService`]) whose variants are
/// converted to `u16` service IDs when sending messages.
pub struct IpcRemote<'a, T> {
    inbox: IpcInbox<'a>,
    _service_type: PhantomData<T>,
}

/// Errors that can occur during IPC communication.
#[derive(ufmt::derive::uDebug)]
pub enum Error<'a> {
    /// The operation timed out while waiting for a response.
    Timeout,
    /// The message could not be sent to the remote task.
    FailedToSend,
    /// A response was received from an unexpected service ID.
    UnexpectedService(IpcMessage<'a>),
    /// A response with an unexpected format or content was received.
    UnexpectedResponse(IpcMessage<'a>),
}

impl<'a> Error<'a> {
    /// Returns a static human-readable description of the error.
    pub fn message(&self) -> &'static str {
        match self {
            Self::Timeout => "timeout while waiting for response",
            Self::FailedToSend => "failed to send message",
            Self::UnexpectedService(_) => "received message from unexpected service",
            Self::UnexpectedResponse(_) => "received unexpected response message",
        }
    }
}

impl<'a, T: Into<u16> + Copy> IpcRemote<'a, T> {
    /// Creates a new [`IpcRemote`] wrapping the given [`IpcInbox`].
    pub const fn new(inbox: IpcInbox<'a>) -> Self {
        Self {
            inbox,
            _service_type: PhantomData,
        }
    }

    /// Registers this inbox with the kernel so it can receive messages.
    ///
    /// Must be called before any [`receive`](Self::receive) or [`call`](Self::call).
    pub fn start(&self) {
        self.inbox.register();
    }

    /// Waits for and returns the next incoming [`IpcMessage`].
    ///
    /// Blocks until a message is available or `timeout` expires.
    /// Returns [`Error::Timeout`] if no message arrives in time.
    pub fn receive(&self, timeout: Timeout) -> Result<IpcMessage<'a>, Error<'a>> {
        let events_ready = SysEvents::new_with_read(&[self.inbox.remote()]).poll(timeout);
        if !events_ready.read_ready(self.inbox.remote()) {
            return Err(Error::Timeout);
        }
        // this should not fail, because the kernel signalled us that a message is ready
        let message = self.inbox.try_receive().expect("Failed to receive message");
        Ok(message)
    }

    /// Sends a message to the remote service and waits for a response.
    ///
    /// # Arguments
    /// - `service` — The target service on the remote task.
    /// - `message` — The IPC message payload to send.
    /// - `timeout` — Maximum wait time per receive attempt.
    ///
    /// # Errors
    /// - [`Error::FailedToSend`] — Message could not be sent.
    /// - [`Error::Timeout`] — No response received within `timeout`.
    /// - [`Error::UnexpectedService`] — Response arrived from wrong service.
    /// - [`Error::UnexpectedResponse`] — Utility message handler rejected the message.
    pub fn call(
        &self,
        service: T,
        message: &IpcMessage,
        timeout: Timeout,
    ) -> Result<IpcMessage<'a>, Error<'a>> {
        let service_id = service.into();
        message
            .send(self.inbox.remote(), service_id)
            .map_err(|_| Error::FailedToSend)?;
        loop {
            let reply = self.receive(timeout)?;

            if reply.service() != service_id {
                return Err(Error::UnexpectedService(reply));
            } else {
                return Ok(reply);
            }
        }
    }
}

/// Declares a `static` [`IpcRemote`] instance with a statically allocated receive buffer.
///
/// # Parameters
/// - `$name` — The name of the resulting `static` variable.
/// - `$remote` — The [`RemoteSysTask`] variant (without the path prefix) to communicate with.
/// - `$service_type` — The service enum type (e.g. `CoreIpcService`).
/// - `$bufsize` — The buffer size in **bytes**; internally rounded to `usize` alignment.
///
/// # Example
/// ```rust
/// static_service!(CORE_REMOTE, CoreApp, CoreIpcService, 4096);
/// ```
#[macro_export]
macro_rules! static_service {
    ($name:ident, $remote:ident, $service_type:ty, $bufsize:expr) => {
        pub static $name: $crate::service::IpcRemote<'static, $service_type> = {
            const BUFFER_SIZE: usize = $bufsize / core::mem::size_of::<usize>();
            static mut BUFFER: [usize; BUFFER_SIZE] = [0usize; BUFFER_SIZE];
            // SAFETY: The BUFFER cannot be accessed outside the macro invocation.
            let inbox = $crate::ipc::IpcInbox::new($crate::ipc::RemoteSysTask::$remote, unsafe {
                &mut *core::ptr::addr_of_mut!(BUFFER)
            });
            $crate::service::IpcRemote::new(inbox)
        };
    };
}
