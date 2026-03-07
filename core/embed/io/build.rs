#[path = "backlight/build.rs"]
mod backlight;

#[path = "button/build.rs"]
mod button;

#[path = "display/build.rs"]
mod display;

#[path = "haptic/build.rs"]
mod haptic;

#[path = "gfx/build.rs"]
mod gfx;

#[path = "notify/build.rs"]
mod notify;

#[path = "power_manager/build.rs"]
mod power_manager;

#[path = "sbu/build.rs"]
mod sbu;

#[path = "sdcard/build.rs"]
mod sdcard;

#[path = "suspend/build.rs"]
mod suspend;

#[path = "translations/build.rs"]
mod translations;

#[path = "tsqueue/build.rs"]
mod tsqueue;

#[path = "touch/build.rs"]
mod touch;

#[path = "usb/build.rs"]
mod usb;

fn main() {
    let mut lib = cbuild::CLibrary::new();

    lib.use_lib("sec");

    if cfg!(feature = "backlight") {
        backlight::def_module(&mut lib);
    }

    if cfg!(feature = "button") {
        button::def_module(&mut lib);
    }

    display::def_module(&mut lib);

    gfx::def_module(&mut lib);

    if cfg!(feature = "haptic") {
        haptic::def_module(&mut lib);
    }

    notify::def_module(&mut lib);

    //TODO!@# consider splitting pmic/power_manager into separate modules
    if cfg!(feature = "power_manager") || cfg!(feature = "pmic") {
        power_manager::def_module(&mut lib);
    }

    if cfg!(feature = "sbu") {
        sbu::def_module(&mut lib);
    }

    if cfg!(feature = "sd_card") {
        sdcard::def_module(&mut lib);
    }

    if cfg!(feature = "suspend") {
        suspend::def_module(&mut lib);
    }

    translations::def_module(&mut lib);

    tsqueue::def_module(&mut lib);

    if cfg!(feature = "touch") {
        touch::def_module(&mut lib);
    }

    if cfg!(feature = "usb") {
        usb::def_module(&mut lib);
    }

    lib.build();
}
