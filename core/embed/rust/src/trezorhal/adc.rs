use core::ffi::CStr;
use heapless::String;
use super::ffi;



pub fn get_vrefint() -> String<32> {
    let mut buffer = [0_u8;32];
    unsafe {
        let len = ffi::adc_get_vrefint(buffer.as_mut_ptr() as _, buffer.len() as _);
        let s = unwrap!(CStr::from_bytes_with_nul_unchecked(&buffer[..len+1]).to_str());
        let mut result: String<32> = String::new();
        unwrap!(result.push_str(s));
        result
    }
}

pub fn get_vbat() -> String<32> {

    let mut buffer = [0_u8;32];
    unsafe {
        let len = ffi::adc_get_vbat(buffer.as_mut_ptr() as _, buffer.len() as _);
        let s = unwrap!(CStr::from_bytes_with_nul_unchecked(&buffer[..len+1]).to_str());
        let mut result: String<32> = String::new();
        unwrap!(result.push_str(s));
        result
    }
}

pub fn get_temp() -> String<32> {

    let mut buffer = [0_u8;32];
    unsafe {
        let len = ffi::adc_get_temp(buffer.as_mut_ptr() as _, buffer.len() as _);
        let s = unwrap!(CStr::from_bytes_with_nul_unchecked(&buffer[..len+1]).to_str());
        let mut result: String<32> = String::new();
        unwrap!(result.push_str(s));
        result
    }
}

