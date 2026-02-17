use core::marker::PhantomData;
extern crate alloc;
use ufmt::derive::uDebug;

use crate::ipc::{IpcInbox, IpcMessage, RemoteSysTask};
use crate::sysevent::SysEvents;
use crate::util::Timeout;

pub const CORE_SERVICE_REMOTE: RemoteSysTask = RemoteSysTask::CoreApp;

use trezor_structs::ArchivedUtilEnum;

// ============================================================================
// Trait-based Call Abstraction
// ============================================================================
/// Context for handling utility messages, contains info from the original request
pub struct UtilContext {
    pub service: u16,
    pub id: u16,
    pub remote: RemoteSysTask,
}

/// Result of handling a utility message
pub enum UtilHandleResult {
    /// Continue waiting for more messages
    Continue,
    /// Unexpected message received
    Unexpected,
}

/// Trait for handling utility service messages during IPC calls
pub trait UtilHandler {
    /// Returns true if this handler expects utility messages
    fn expects_util_messages(&self) -> bool;

    /// Handle an incoming utility enum message
    /// Returns `UtilHandleResult::Continue` if handled successfully and should keep waiting
    /// Returns `UtilHandleResult::Unexpected` if the message was not expected
    fn handle(&self, ctx: &UtilContext, archived: &ArchivedUtilEnum) -> UtilHandleResult;
}

/// No utility message handling - for regular calls
pub struct NoUtilHandler;

impl UtilHandler for NoUtilHandler {
    fn expects_util_messages(&self) -> bool {
        false
    }

    fn handle(&self, _ctx: &UtilContext, _archived: &ArchivedUtilEnum) -> UtilHandleResult {
        // Should never receive utility messages
        UtilHandleResult::Unexpected
    }
}

#[derive(uDebug, Copy, Clone, PartialEq, Eq, num_enum::IntoPrimitive, num_enum::FromPrimitive)]
#[repr(u16)]
pub enum CoreIpcService {
    Lifecycle = 0,
    Ui = 1,
    WireStart = 2,
    WireContinue = 3,
    WireEnd = 4,
    Crypto = 5,
    Util = 6,
    WireCall = 7,
    #[num_enum(catch_all)]
    Unknown(u16),
}

pub struct IpcRemote<'a, T> {
    inbox: IpcInbox<'a>,
    _service_type: PhantomData<T>,
}

#[derive(ufmt::derive::uDebug)]
pub enum Error<'a> {
    Timeout,
    FailedToSend,
    UnexpectedService(IpcMessage<'a>),
    UnexpectedResponse(IpcMessage<'a>),
}

impl<'a, T: Into<u16> + Copy> IpcRemote<'a, T> {
    pub const fn new(inbox: IpcInbox<'a>) -> Self {
        Self {
            inbox,
            _service_type: PhantomData,
        }
    }

    pub fn start(&self) {
        self.inbox.register();
    }

    pub fn receive(&self, timeout: Timeout) -> Result<IpcMessage<'a>, Error<'a>> {
        let events_ready = SysEvents::new_with_read(&[self.inbox.remote()]).poll(timeout);
        if !events_ready.read_ready(self.inbox.remote()) {
            return Err(Error::Timeout);
        }
        // this should not fail, because the kernel signalled us that a message is ready
        let message = self.inbox.try_receive().expect("Failed to receive message");
        Ok(message)
    }

    pub fn call(
        &self,
        service: T,
        message: &IpcMessage,
        timeout: Timeout,
        util_handler: &dyn UtilHandler,
    ) -> Result<IpcMessage<'a>, Error<'a>> {
        let service_id = service.into();
        message
            .send(self.inbox.remote(), service_id)
            .map_err(|_| Error::FailedToSend)?;
        loop {
            let reply = self.receive(timeout)?;

            if reply.service() == u16::from(CoreIpcService::Util)
                && util_handler.expects_util_messages()
            {
                let util_ctx = UtilContext {
                    service: reply.service(),
                    id: reply.id(),
                    remote: reply.remote(),
                };
                let data = reply.data();
                let archived = unsafe { rkyv::access_unchecked::<ArchivedUtilEnum>(data) };

                match util_handler.handle(&util_ctx, archived) {
                    UtilHandleResult::Continue => continue,
                    UtilHandleResult::Unexpected => return Err(Error::UnexpectedResponse(reply)),
                }
            } else if reply.service() != service_id {
                return Err(Error::UnexpectedService(reply));
            } else {
                return Ok(reply);
            }
        }
    }
}

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

pub(crate) use static_service;
