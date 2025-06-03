use super::ffi;

pub fn send_data(data: &[u8]) {
    unsafe {
        ffi::nrf_send_uart_data(data.as_ptr(), data.len() as _);
    }
}
