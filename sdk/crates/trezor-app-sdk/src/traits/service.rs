use stabby::boxed::Box;
use stabby::slice::{Slice, SliceMut};

use super::util::FastResult;

/// Identifies the remote system task that sent or will receive an IPC message.
#[derive(
    ufmt::derive::uDebug,
    Copy,
    Clone,
    PartialEq,
    Eq,
    num_enum::FromPrimitive,
    num_enum::IntoPrimitive,
)]
#[stabby::stabby]
#[repr(u8)]
pub enum RemoteSysTask {
    Kernel = 0,
    CoreApp = 1,
    #[num_enum(catch_all)]
    Unknown(u8),
}

/// Identifies the IPC services provided by the Core application.
#[derive(
    ufmt::derive::uDebug,
    Copy,
    Clone,
    PartialEq,
    Eq,
    num_enum::IntoPrimitive,
    num_enum::FromPrimitive,
)]
#[stabby::stabby]
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

#[stabby::stabby(checked)]
pub trait Message {
    extern "C" fn service(&self) -> u16;
    extern "C" fn id(&self) -> u16;
    extern "C" fn data<'a>(&'a self) -> Slice<'a, u8>;
}

pub type MessageVtable = stabby::vtable!(Message);
/// A borrowed reference to a received [`Message`] — never owning, since Core
/// never allocates: the message data is borrowed straight from the app's own
/// IPC inbox buffer (see `IpcRemote::register_inbox`). Valid only until the
/// next `receive`/`call`, which reuses the same buffer slot.
pub type MessageRef<'a> = stabby::DynRef<'a, MessageVtable>;

/// Errors that can occur during IPC communication.
#[stabby::stabby]
#[repr(C, u8)]
pub enum IpcError<'a> {
    /// The operation timed out while waiting for a response.
    Timeout,
    /// The message could not be sent to the remote task.
    FailedToSend,
    /// A response was received from an unexpected service ID.
    UnexpectedService(MessageRef<'a>),
    /// A response with an unexpected format or content was received.
    UnexpectedResponse(MessageRef<'a>),
}

impl IpcError<'_> {
    /// Returns a static human-readable description of the error.
    pub fn message(&self) -> &'static str {
        match self {
            Self::Timeout => "timeout while waiting for response",
            Self::FailedToSend => "failed to send message",
            Self::UnexpectedService { .. } => "received message from unexpected service",
            Self::UnexpectedResponse(..) => "received unexpected response message",
        }
    }
}

#[stabby::stabby(checked)]
pub trait IpcRemote {
    /// Registers `buffer` as this app's own inbox for messages from Core.
    ///
    /// Must be called exactly once, before the first `receive`/`call`. Core
    /// never allocates memory of its own for IPC — `buffer` must be
    /// allocated by the app (out of its own heap) and stay valid for as
    /// long as the app is running; Core only ever holds a reference into
    /// it, never a copy.
    extern "C" fn register_inbox<'remote, 'local>(&'remote self, buffer: SliceMut<'local, usize>);

    /// Waits for and returns the next incoming [`Message`].
    ///
    /// Blocks until a message is available or `timeout` expires.
    /// Returns [`Error::Timeout`] if no message arrives in time.
    extern "C" fn receive<'remote>(
        &'remote self,
        timeout_ms: u32,
    ) -> FastResult<MessageRef<'remote>, IpcError<'remote>>;

    /// Sends a message to the remote service.
    ///
    /// # Arguments
    /// - `message` — The IPC message payload to send.
    ///
    /// # Errors
    /// - [`Error::FailedToSend`] — Message could not be sent.
    extern "C" fn send<'remote, 'local>(
        &'remote self,
        service: u16,
        id: u16,
        message: Slice<'local, u8>,
    ) -> FastResult<(), IpcError<'remote>>;

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
    extern "C" fn call<'remote, 'local>(
        &'remote self,
        service: u16,
        id: u16,
        message: Slice<'local, u8>,
        timeout_ms: u32,
    ) -> FastResult<MessageRef<'remote>, IpcError<'remote>>;
}

pub type BoxedIpcRemote = stabby::dynptr!(Box<dyn IpcRemote + Send + Sync>);
pub type IpcRemoteVtable = stabby::vtable!(IpcRemote + Send + Sync);
pub type IpcRemoteRef<'a> = stabby::DynRef<'a, IpcRemoteVtable>;
