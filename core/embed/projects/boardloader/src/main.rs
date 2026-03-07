#![no_std]
#![no_main]

#[cfg(not(feature = "mcu_emulator"))]
#[panic_handler]
fn panic(_info: &core::panic::PanicInfo) -> ! {
    loop {}
}
