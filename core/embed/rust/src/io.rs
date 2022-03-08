use crate::{
    error::Error,
    time::{Duration, Instant},
    trezorhal::usb::{usb_is_ready_to_read, usb_is_ready_to_write, IfaceTicket},
    util::wait_in_busy_loop,
};

mod ffi {
    extern "C" {
        #[cfg(feature = "model_t1")]
        pub fn button_read() -> u32;
        #[cfg(feature = "model_tt")]
        pub fn touch_read() -> u32;
    }
}

#[cfg(feature = "model_t1")]
pub fn button_read() -> u32 {
    unsafe { ffi::button_read() }
}

#[cfg(feature = "model_tt")]
pub fn touch_read() -> u32 {
    unsafe { ffi::touch_read() }
}

pub enum Resource {
    #[cfg(feature = "model_t1")]
    Button,
    #[cfg(feature = "model_tt")]
    Touch,
    UsbRead(IfaceTicket),
    UsbWrite(IfaceTicket),
}

pub enum Event {
    #[cfg(feature = "model_t1")]
    Button(u32), // TODO: We should somehow use `ButtonEvent` from UI here.
    #[cfg(feature = "model_tt")]
    Touch(u32), // TODO: We should somehow use `TouchEvent` from UI here.
    UsbRead(IfaceTicket),
    UsbWrite(IfaceTicket),
    TimedOut,
}

pub fn poll_io(resources: &[Resource], timeout: Duration) -> Result<Event, Error> {
    let deadline = Instant::now()
        .checked_add(timeout)
        .ok_or(Error::OutOfRange)?;

    loop {
        // Poll all resources, return if ready.
        for resource in resources {
            match resource {
                #[cfg(feature = "model_t1")]
                Resource::Button => {
                    let event = button_read();
                    if event != 0 {
                        return Ok(Event::Button(event));
                    }
                }
                #[cfg(feature = "model_tt")]
                Resource::Touch => {
                    let event = touch_read();
                    if event != 0 {
                        return Ok(Event::Touch(event));
                    }
                }
                Resource::UsbRead(ticket) => {
                    if usb_is_ready_to_read(*ticket) {
                        return Ok(Event::UsbRead(*ticket));
                    }
                }
                Resource::UsbWrite(ticket) => {
                    if usb_is_ready_to_write(*ticket) {
                        return Ok(Event::UsbWrite(*ticket));
                    }
                }
            }
        }

        // No resource is ready yet, wait or exit on timeout.
        if Instant::now() < deadline {
            wait_in_busy_loop();
        } else {
            return Ok(Event::TimedOut);
        }
    }
}
