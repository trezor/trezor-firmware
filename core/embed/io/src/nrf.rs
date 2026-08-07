use super::ffi;

pub fn send_data(data: &[u8], timeout: u32) -> bool {
    unsafe { ffi::nrf_send_uart_data(data.as_ptr(), data.len() as _, timeout) }
}
