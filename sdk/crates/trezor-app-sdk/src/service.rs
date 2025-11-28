use core::marker::PhantomData;

use ufmt::derive::uDebug;

use crate::ipc::{IpcInbox, IpcMessage, RemoteSysTask};
use crate::sysevent::SysEvents;
use crate::util::Timeout;

pub const CORE_SERVICE_REMOTE: RemoteSysTask = RemoteSysTask::CoreApp;

#[derive(uDebug, Copy, Clone, PartialEq, Eq, num_enum::IntoPrimitive, num_enum::FromPrimitive)]
#[repr(u16)]
pub enum CoreIpcService {
    Lifecycle = 0,
    Ui = 1,
    WireStart = 2,
    WireContinue = 3,
    WireEnd = 4,
    #[num_enum(catch_all)]
    Unknown(u16),
    Ping = 0xffff,
}

pub struct IpcRemote<'a, T> {
    inbox: IpcInbox<'a>,
    _service_type: PhantomData<T>,
}

pub enum Error<'a> {
    Timeout,
    FailedToSend,
    UnexpectedService(IpcMessage<'a>),
    UnexpectedResponse(IpcMessage<'a>),
}

impl<'a, T: Into<u16>> IpcRemote<'a, T> {
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
    ) -> Result<IpcMessage<'a>, Error<'a>> {
        let service_id = service.into();
        message
            .send(self.inbox.remote(), service_id)
            .map_err(|_| Error::FailedToSend)?;
        let reply = self.receive(timeout)?;
        if reply.service() != service_id {
            Err(Error::UnexpectedService(reply))
        } else {
            Ok(reply)
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
            let inbox = $crate::ipc::IpcInbox::new($crate::ipc::RemoteSysTask::$remote, unsafe { &mut *core::ptr::addr_of_mut!(BUFFER) });
            $crate::service::IpcRemote::new(inbox)
        };
    };
}

pub(crate) use static_service;
