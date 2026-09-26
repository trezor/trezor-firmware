use crate::service::{CoreIpcService, IpcRemote};

static SERVICES: spin::Once<&'static IpcRemote<'static, CoreIpcService>> = spin::Once::new();

pub fn init(services: &'static IpcRemote<'static, CoreIpcService>) {
    SERVICES.call_once(|| services);
}

pub(crate) fn services_or_die() -> &'static IpcRemote<'static, CoreIpcService> {
    SERVICES.get().expect("Services not initialized")
}
