use stm32_metapac as pac;

pub fn test() {
    let p = cortex_m::Peripherals::take().unwrap();

    critical_section::with(|_cs| {
        p.MPU.rbar_a1.read();
    });
    
    let rcc = pac::RCC;    

    rcc.ahb1enr().modify(|w| {
        w.set_gpu2den(true);
    });

    
}